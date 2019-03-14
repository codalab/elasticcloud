import os
from datetime import datetime
import time

from ElasticCloudAdapter import ElasticCloudAdapter

class GCEAdapter(ElasticCloudAdapter):

    # Container States
    CONTAINER_RUNNING = 'RUNNING'
    CONTAINER_STOPPING = 'STOPPING'
    CONTAINER_STOPPED = 'STOPPED'


    def __init__(self):
        super().__init__('gce')

        self._configure()
        self.gce = self._load_gce_account()

        # Used to format node names (datetime formatting)
        self.format = '%m-%d-%Y-%H-%M-%S'

        states_directory = '.states'
        self.container_states_filename = states_directory + '/container_states'
        self.node_states_filename = states_directory + '/node_states'

        if not os.path.isdir(states_directory):
            os.mkdir(states_directory)

       
    def _configure(self):
        # From config.yaml
        self.service_account_key_path = self.config['service_account_file']
        self.datacenter               = self.config['datacenter']
        self.image                    = self.config['image_name']
        self.size                     = self.config['vm_size']
        self.max_nodes                = self.config['max']
        self.min_nodes                = self.config['min']
        self.EXPAND_CRITERION         = self.config['expand_sensitivity'] 
        self.SHRINK_CRITERION         = self.config['shrink_sensitivity'] 

    def _load_gce_account(self):
        tmp = __import__('libcloud.compute.types', fromlist=['Provider'])
        Provider = tmp.Provider
        tmp = __import__('libcloud.compute.providers', fromlist=['get_driver'])
        get_driver = tmp.get_driver
        json = __import__('json')
        service_account = None
        
        with open(self.service_account_key_path) as f:
            service_account = json.load(f)

        Driver = get_driver(Provider.GCE)

        return Driver(service_account['client_email'], 
        self.service_account_key_path, 
        datacenter=self.datacenter,
        project=service_account['project_id'])
        

    def _get_oldest_node(self):
        # use strptime to parse node names and compare
        nodes = self.gce.list_nodes()
        oldest_date = datetime.strptime(nodes[0].name[4:], self.format)
        oldest_node = nodes[0]
        for node in nodes:
            date = datetime.strptime(node.name[4:], self.format)
            if date < oldest_date:
               oldest_node = node 
        return oldest_node

    def _load_states(self, option):
        if option == 'container':
            filename = self.container_states_filename
        elif option == 'node':
            filename = self.node_states_filename
        states = []

        # Check that file exists
        if os.path.isfile(filename):
            with open(filename) as f:
                lines = f.readlines()
                for l in lines:
                    line = l.split()
                    states.append(line)
        return states

    def _store_states(self, states, option):
        if option == 'container':
            filename = self.container_states_filename
        elif option == 'node':
            filename = self.node_states_filename
        with open(filename, 'w+') as f:
            for s in states:
                line = " ".join(s)
                f.write('%s\n' % line)

    def set_container_state(self, node_name, state):
        states = self._load_states('container')
        state_exists = False
        for s in states:
            if s[0] == node_name:
                s[1] = state
                state_exists = True
        if not state_exists:
            new_state = [node_name, state]
            states.append(new_state)
        self._store_states(states, 'container')        

    def get_container_state(self, node_name):
        filename = "container_states"
        states = self._load_states('container')
        for s in states:
            if s[0] == node_name:
                return s[1]
        return None

    def _clean_container_states(self):
        states = self._load_states('container')
        new_states = []
        for s in states:
            if s[1] == self.CONTAINER_STOPPED:
                pass
            else:
                new_states.append(s)
        self._store_states(new_states, 'container')

    def _wait_for_node_container_shutdown(self, node_name):
        # get ip from node name
        node = None
        for n in self.gce.list_nodes():
            if n.name == node_name:
                node = n

        ip = node.public_ips[0]
        command = 'docker ps | wc -l'
        container_running = 1
        while container_running:
            (stdin, stdout, stderr) = self._run_ssh_command(ip, command)

            out = stdout.readlines()
            line = out[0]
            container_running = int(line.split()[0]) - 1
            if container_running:
                print('container stopping.')
            else:
                print('container stopped.')
            time.sleep(0.5)

    def _stop_container(self, node_name, container_name):
        node = None
        for n in self.gce.list_nodes():
            if n.name == node_name:
                node = n

        ip = node.public_ips[0]
        command = 'docker stop -t 10 ' + container_name

        (stdin, stdout, stderr) = self._run_ssh_command(ip, command)

    def get_node_quantity(self):
        return len(self.gce.list_nodes())

    def get_node_names(self):
        nodes = self.gce.list_nodes()
        names = []
        for n in nodes:
            names.append(n.name)
        return names

    def get_node_ips(self):
        nodes = self.gce.list_nodes()
        ips = []
        for n in nodes:
            ips.append(n.public_ips)
        return ips

    def expand(self):
        if self.get_node_quantity() < self.max_nodes:
            now = datetime.now()
            node_name = 'gpu-' + now.strftime(self.format)
            print('Creating new VM node...')
            new_node = self.gce.create_node(name=node_name, size=self.size, image=self.image)
            """
            new_node = self.gce.create_node(name=node_name,
                                            size=self.size, 
                                            image=self.image, 
                                            ex_accelerator_count=1,
                                            ex_accelerator_type='nvidia-tesla-p100',
                                            )
            """

            self.gce.wait_until_running([new_node])

            # Mark container state as "RUNNING"
            self.set_container_state(node_name, GCEAdapter.CONTAINER_RUNNING)

            return "New node running at " + new_node.public_ips[0] + " with name " + node_name
        else:
            return "Already " + str(self.get_active_node_quantity()) + " nodes running. (max)"
            
    def shrink(self):
        if self.get_node_quantity() > self.min_nodes:
            node_name = self._get_oldest_node().name

            # Mark state to "STOPPING"
            self.set_container_state(node_name, GCEAdapter.CONTAINER_STOPPING)

            # Send SIGTERM to worker (docker stop)
            self._stop_container(node_name, 'web')
            self._wait_for_node_container_shutdown(node_name)

            # Destroy VM
            node = None
            for n in self.gce.list_nodes():
                if n.name == node_name:
                    node = n
            print('Shutting down VM...')
            self.gce.destroy_node(node)
            print('VM has shut down.')

            # Mark state to "STOPPED"
            self.set_container_state(node_name, GCEAdapter.CONTAINER_STOPPED)
            
            return "Destroyed node: " + node.name + "."
        else:
            return "Only " + str(self.min_nodes) + " nodes running. (min)"

    def dump_state(self):

        node_states = []
        node_names = self.get_node_names()

        # paramiko ssh
        ips = self.get_node_ips()
        for ip in ips:
            host = ip[0]
            self.ssh_client.connect(host, username=self.username, pkey=self.pkey)

            commands = ['ls -la /tmp/codalab | wc -l']

            for command in commands:
                stdin, stdout, stderr = self.ssh_client.exec_command(command)
                s = stdout.readlines()
                if command == 'ls -la /tmp/codalab | wc -l':
                    directory_length = int(s[0])
                    if directory_length > 3:
                        node_states.append('BUSY')
                    else:
                        node_states.append('NOT-BUSY')
                else:
                    for l in s:
                        print(l)
                    print("stderr",stderr.readlines())
        return list(zip(node_names, node_states))
    
    def get_next_action(self):
        """

        If all nodes have been busy for longer than EXPAND_CRITERION, next action is expand.
        If there is a node that has been not-busy for longer than SHRINK_CRITERION, next action is shrink.
        Otherwise, next action is do-nothing.

        """

        next_action = ElasticCloudAdapter.ACTION_DO_NOTHING
        action_count = 0

        def get_count(old_nodes, node):
            for i in range(len(old_nodes)):
                if old_nodes[i][0] == node[0]:
                    if node[1] == old_nodes[i][1]:
                        return int(old_nodes[i][2])
            return 0

        filename = "node_states"
        old_nodes = self._load_states('node')

        stored_nodes = []
        new_nodes = self.dump_state()
        busy_count = 0
        for n in new_nodes:
            count = get_count(old_nodes, n)
            if n[1] == 'NOT-BUSY':
                if count >= self.SHRINK_CRITERION:
                    print('shrink criterion met')
                    next_action = ElasticCloudAdapter.ACTION_SHRINK
                    action_count += 1
            elif n[1] == 'BUSY':
                busy_count += 1
            stored_nodes.append([n[0], n[1], str(count + 1)])

        # all nodes are in busy state
        if busy_count == len(new_nodes):
            TOO_BUSY = True
            for n in old_nodes:
                if int(n[2]) < self.EXPAND_CRITERION:
                    TOO_BUSY = False
            
            if TOO_BUSY:
                print('expand criterion met')
                next_action = ElasticCloudAdapter.ACTION_EXPAND
                action_count = 1

        self._store_states(stored_nodes, 'node')
        self._clean_container_states()
        return (next_action, action_count)
