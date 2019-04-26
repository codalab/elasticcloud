import os
import json
import copy
import time
from datetime import datetime

from paramiko import ssh_exception
import boto3
from botocore.exceptions import ClientError
from libcloud.common.google import GoogleBaseError

from ElasticCloudAdapter import ElasticCloudAdapter


class GCEAdapter(ElasticCloudAdapter):
    # Container States
    CONTAINER_STARTING = 'STARTING'
    CONTAINER_RUNNING = 'RUNNING'
    CONTAINER_STOPPING = 'STOPPING'
    CONTAINER_STOPPED = 'STOPPED'
    INITIALIZING = True

    def __init__(self):
        super().__init__('gce')

        self._configure()
        self.gce = self._load_gce_account()

        # Used to format node names (datetime formatting)
        self.format = '%m-%d-%Y-%H-%M-%S'
        
        self._load_boto_client()

        GCEAdapter.INITIALIZING = False


    def _configure(self):
        # From config.yaml
        self.service_account_key = self.config['service_account_key']
        # If above key is given, this path points to a temp storage version of the above key -- it
        # will be overwritten!
        self.service_account_key_path = self.config['service_account_file']
        self.datacenter = self.config['datacenter']
        self.image = self.config['image_name']
        self.size = self.config['vm_size']
        self.max_nodes = self.config['max']
        self.min_nodes = self.config['min']
        self.EXPAND_CRITERION = self.config['expand_sensitivity']
        self.SHRINK_CRITERION = self.config['shrink_sensitivity']
        self.use_gpus = self.config.get("use_gpus", False)
        self.CLOUDCUBE_URL = os.environ['CLOUDCUBE_URL']
        self.CLOUDCUBE_ACCESS_KEY_ID = os.environ['CLOUDCUBE_ACCESS_KEY_ID']
        self.CLOUDCUBE_SECRET_ACCESS_KEY = os.environ['CLOUDCUBE_SECRET_ACCESS_KEY']

    def _load_gce_account(self):
        tmp = __import__('libcloud.compute.types', fromlist=['Provider'])
        Provider = tmp.Provider
        tmp = __import__('libcloud.compute.providers', fromlist=['get_driver'])
        get_driver = tmp.get_driver
        json = __import__('json')
        service_account = None

        if self.service_account_key:
            print("Loading service account key directly, not reading from file path")
            service_account = json.loads(self.service_account_key)
            self.service_account_key_path = "gce_service_key_temp_store.json"
            with open(self.service_account_key_path, "w") as f:
                f.write(self.service_account_key)

        else:
            print(f"Reading from service account key path: {self.service_account_key_path}")
            with open(self.service_account_key_path) as f:
                service_account = json.load(f)

        Driver = get_driver(Provider.GCE)
        self.service_account_email = service_account['client_email']


        return Driver(service_account['client_email'],
                      self.service_account_key_path,
                      datacenter=self.datacenter,
                      project=service_account['project_id'])

    def _load_boto_client(self):
        self.s3_client = boto3.client('s3', aws_access_key_id=self.CLOUDCUBE_ACCESS_KEY_ID, aws_secret_access_key=self.CLOUDCUBE_SECRET_ACCESS_KEY)
        self.s3_bucket_name = 'cloud-cube'
        fs_prefix = self.CLOUDCUBE_URL[-12:]
        remote_location = '/gce_states'
        self.s3_state_file_location = fs_prefix + remote_location
        self.local_state_file_location = '.gce_states'
        
        try:
            self.s3_client.download_file(self.s3_bucket_name, self.s3_state_file_location, self.local_state_file_location)
        except ClientError:
            print('ClientError')
            if os.path.exists(self.local_state_file_location) and os.path.getsize(self.local_state_file_location) > 0:
                self.s3_client.upload_file(self.local_state_file_location, self.s3_bucket_name, self.s3_state_file_location)
            else:
                print('local states did not exist')
                new_states = {}
                with open(self.local_state_file_location,'w+') as state_file:
                    node_states = self.dump_state()
                    print(node_states)
                    new_states['node'] = node_states

                    container_states = {}
                    for name in node_states:
                        container_states[name] = {}
                        container_states[name]['status'] = self.CONTAINER_RUNNING

                    new_states['container'] = container_states
                    json.dump(new_states, state_file)
                    
                print(new_states)
                self.s3_client.upload_file(self.local_state_file_location, self.s3_bucket_name, self.s3_state_file_location)
                
            
        


    def list_nodes(self):
        nodes = self.gce.list_nodes()
        # Filter nodes that don't fit the datetime format. These nodes were probably created by the user and not by elastic cloud.

        unfit_nodes = []

        for n in nodes:
            try:
                datetime.strptime(n.name[4:-4], self.format)
            except ValueError:
                unfit_nodes.append(n)

        for n in unfit_nodes:
            nodes.remove(n)

        return nodes
        

    def _get_oldest_nodes(self,n):
        # use strptime to parse node names and compare
        def calculate_key(node):
            date = datetime.strptime(node.name[4:-4], self.format)
            return date

        nodes = self.list_nodes()
        if n > len(nodes):
            n = len(nodes)

        nodes.sort(key=calculate_key)
        
        return nodes[0:n]

    def _load_states(self):
        states = {}

        self.s3_client.download_file(self.s3_bucket_name, self.s3_state_file_location, self.local_state_file_location)
        with open(self.local_state_file_location, 'r+') as state_file:
            states = json.load(state_file)

        return states

    def _store_states(self, new_states, option):
        states = self._load_states()
        states[option] = new_states 

        with open(self.local_state_file_location, 'w+') as state_file:
            json.dump(states, state_file)        

        self.s3_client.upload_file(self.local_state_file_location, self.s3_bucket_name, self.s3_state_file_location)

    def _set_container_state(self, node_name, state):
        states = self._load_states()['container']
        if states.get(node_name):
            states[node_name]['status'] = state
        else:
            states[node_name] = {}
            states[node_name]['status'] = state
        self._store_states(states, 'container')

    def _get_container_state(self, node_name):
        states = self._load_states()['container']
        state = states.get(node_name)
        if state:
            return state['status']
        else:
            return None

    def _clean_container_states(self):
        states = self._load_states()['container']

        stored_states = copy.deepcopy(states)
        for node_name in states:
            if states[node_name]['status'] == self.CONTAINER_STOPPED:
                stored_states.pop(node_name, None)

        self._store_states(stored_states, 'container')

    def _update_container_state(self, node_name):
        # get ip from node name
        node = None
        for n in self.list_nodes():
            if n.name == node_name:
                node = n

        ip = node.public_ips[0]
        command = 'sudo docker ps'
        container_running = 1
        (stdin, stdout, stderr) = self._run_ssh_command(ip, command)

        out = stdout.readlines()
        container_running = len(out) - 1

        if container_running:
            self._set_container_state(node_name, GCEAdapter.CONTAINER_RUNNING)
        else:
            print(node_name + ' container not currently running.')
    
    def update_all_states(self):
        node_names = self.get_node_names()

        old_node_states = self._load_states()['node']
        new_node_states = self.dump_state()

        node_states = {}
        for name in new_node_states:
            node = old_node_states.get(name)
            if node:
                node_states[name] = node
            else:
                node_states[name] = {}
                node_states[name]['status'] = new_node_states[name]['status']
                node_states[name]['count'] = 1
        self._store_states(node_states, 'node')

        for name in node_names:
            self._update_container_state(name)


    def _wait_for_node_container_shutdown(self, node_name):
        print("node_name:", node_name) # DEBUG

        # get ip from node name
        node = None
        for n in self.list_nodes():
            if n.name == node_name:
                node = n

        ip = node.public_ips[0]
        command = 'sudo docker ps'
        container_running = 1
        while container_running:
            (stdin, stdout, stderr) = self._run_ssh_command(ip, command)

            out = stdout.readlines()
            container_running = len(out) - 1
            #print("container_running:", container_running) # DEBUG
            if container_running:
                print('container stopping.')
            else:
                print('container stopped.')
            time.sleep(0.5)

    def _stop_container(self, node_name, container_name):
        node = None
        for n in self.list_nodes():
            if n.name == node_name:
                node = n

        ip = node.public_ips[0]
        command = 'sudo docker stop -t 10 ' + container_name

        (stdin, stdout, stderr) = self._run_ssh_command(ip, command)
        #print(stdout.readlines()) # DEBUG
        #print(stderr.readlines()) # DEBUG

    def get_node_quantity(self):
        return len(self.list_nodes())

    def get_node_names(self):
        nodes = self.list_nodes()
        names = []
        for n in nodes:
            names.append(n.name)
        return names

    def get_node_ips(self):
        nodes = self.list_nodes()
        ips = []
        for n in nodes:
            ips.append(n.public_ips)
        return ips

    def expand(self, quantity):
        current_quantity = self.get_node_quantity()
        if current_quantity + quantity > self.max_nodes:
            if current_quantity >= self.max_node:
                print("Already " + str(self.get_node_quantity()) + " nodes running. (max)")
            else: 
                quantity = self.max_nodes - current_quantity
                print("Already " + str(current_quantity) + " nodes running. (max)")
                print("Only " + str(quantity) + " nodes will start up.")

        now = datetime.now()
        base_name = 'gpu-' + now.strftime(self.format)# + "-{:02d}".format(index)
        print('Creating new VM node...')

        new_node_arguments = {
            "base_name": base_name,
            "size": self.size,
            "image": self.image,
            "number": quantity,
            "ignore_errors": False,
            "ex_service_accounts": [{'email': self.service_account_email, 'scopes': ['compute']}]
        }

        new_nodes = None
        if self.use_gpus:
            new_node_arguments = {
                "name": base_name,
                "size": self.size,
                "image": self.image,
                "location": self.datacenter,
                "ex_service_accounts": [{'email': self.service_account_email, 'scopes': ['compute']}]
            }

            print("(note, we doing GPU stuff hoss)")
            new_node_arguments["ex_on_host_maintenance"] = "TERMINATE"
            new_node_arguments["ex_accelerator_count"] = 1
            new_node_arguments["ex_accelerator_type"] = "nvidia-tesla-p100"

            for i in range(quantity):
                base_name = 'gpu-' + now.strftime(self.format) + "-{:03d}".format(index)
                print("New GPU node named {}".format(base_name))
                new_node_arguments['name'] = base_name
                try:
                    new_nodes = self.gce.create_node(**new_node_arguments)
                except GoogleBaseError as e:
                    print('GCE Error:', e)

        else:
            try:
                new_nodes = self.gce.ex_create_multiple_nodes(**new_node_arguments)
        
            except GoogleBaseError as e:
                print('GCE Error:', e)

        if new_nodes:
            for node in new_nodes:
                print("New node running at " + node.public_ips[0] + " with name " + node.name)
                # Mark container state as "STARTING"
                self._set_container_state(node.name, GCEAdapter.CONTAINER_STARTING)


    def shrink(self, quantity):
        current_quantity = self.get_node_quantity()
        if current_quantity > self.min_nodes:
            if current_quantity - quantity < self.min_nodes:
                quantity = current_quantity - self.min_nodes
                print('Spinning down {} nodes.'.format(quantity))
        else:
            return "Only " + str(self.min_nodes) + " nodes running. (min)"
            
            # get n oldest nodes
        nodes = self._get_oldest_nodes(quantity)

        for node in nodes:
            # Mark state to "STOPPING"
            self._set_container_state(node.name, GCEAdapter.CONTAINER_STOPPING)

            # Send SIGTERM to worker (docker stop)
            self._stop_container(node.name, 'compute_worker')


        print('Shutting down {} VMs...'.format(quantity))
        self.gce.ex_destroy_multiple_nodes(nodes)
        print('VMs have shut down.')

        for node in nodes:
            # Mark state to "STOPPED"
            self._set_container_state(node.name, GCEAdapter.CONTAINER_STOPPED)


    def dump_state(self):
        node_states = {}
        nodes = self.list_nodes()

        # paramiko ssh
        for node in nodes:
            host = node.public_ips[0]
            try:
                self._connect(host)
            except (ssh_exception.NoValidConnectionsError, ssh_exception.AuthenticationException):
                print("ERROR :: Could not connect to host, maybe it is spinning down?")
                continue

            commands = ['ls -la /tmp/codalab | wc -l']

            for command in commands:
                stdin, stdout, stderr = self.ssh_client.exec_command(command)
                s = stdout.readlines()
                if command == 'ls -la /tmp/codalab | wc -l':
                    directory_length = int(s[0])
                    node_states[node.name] = { 'status': 'NOT-BUSY',
                                               'count': 1,
                                             }
                    if GCEAdapter.INITIALIZING:
                        if directory_length > 4:
                            node_states[node.name]['status'] = 'BUSY'
                        else:
                            node_states[node.name]['status'] = 'NOT-BUSY'
                    else:
                        if directory_length > 4:
                            node_states[node.name]['status'] = 'BUSY'
                        elif self._get_container_state(node.name) == GCEAdapter.CONTAINER_STARTING:
                            node_states[node.name]['status'] = 'MANAGED'
                        else:
                            node_states[node.name]['status'] = 'NOT-BUSY'
                else:
                    for l in s:
                        print(l)
                    print("stderr", stderr.readlines())
        return node_states

    def get_next_action(self):
        """

        If all nodes have been busy for longer than EXPAND_CRITERION, next action is expand.
        If there is a node that has been not-busy for longer than SHRINK_CRITERION, next action is shrink.
        Otherwise, next action is do-nothing.

        """

        next_action = ElasticCloudAdapter.ACTION_DO_NOTHING
        action_count = 0

        

        new_nodes = self.dump_state()
        old_nodes = self._load_states()['node']
        busy_count = 0
        managed_count = 0

        print('get_next_action:')
        print('new_nodes:',new_nodes)
        print('old_nodes:',old_nodes)

        for name in new_nodes:
            old_count = old_nodes[name]['count']
            old_state = old_nodes[name]['status']
            new_state = new_nodes[name]['status']

            if old_state == new_state:
                if new_nodes[name]['status'] == 'NOT-BUSY':
                    if old_count >= self.SHRINK_CRITERION:
                        next_action = ElasticCloudAdapter.ACTION_SHRINK
                        action_count += 1
                elif new_nodes[name]['status'] == 'BUSY':
                    busy_count += 1
                elif new_nodes[name]['status'] == 'MANAGED':
                    managed_count += 1
                old_nodes[name]['count'] += 1
            else:
                old_nodes[name]['count'] = 1
                old_nodes[name]['status'] = new_state

        # all nodes are in busy state
        if busy_count == len(new_nodes):
            TOO_BUSY = True
            for name in old_nodes:
                if old_nodes[name]['count'] < self.EXPAND_CRITERION:
                    TOO_BUSY = False

            if TOO_BUSY:
                print('expand criterion met')
                next_action = ElasticCloudAdapter.ACTION_EXPAND
                action_count = 1

        self._store_states(old_nodes, 'node')
        self._clean_container_states()
        return (next_action, action_count)
