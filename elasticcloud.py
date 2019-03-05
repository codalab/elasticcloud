import os
import paramiko
import yaml
from datetime import datetime


class GCEMixin():
    def __init__(self, service):
        tmp = __import__('libcloud.compute.types', fromlist=['Provider'])
        Provider = tmp.Provider
        tmp = __import__('libcloud.compute.providers', fromlist=['get_driver'])
        get_driver = tmp.get_driver
        json = __import__('json')

        # From config.yaml
        service_account_key_path = service['service_account_file']
        datacenter               = service['datacenter']
        self.image               = service['image_name']
        self.size                = service['vm_size']
        self.max_nodes           = service['max']
        self.min_nodes           = service['min']
        service_account          = None
        
        with open(service_account_key_path) as f:
            service_account = json.load(f)

        # From service account key
        project_id            = service_account['project_id']
        service_account_email = service_account['client_email']

        Driver = get_driver(Provider.GCE)
        self.gce = Driver(service_account_email, service_account_key_path, datacenter=datacenter, project=project_id)

        # Used to format node names (datetime formatting)
        self.format = '%m-%d-%Y-%H-%M-%S'
        

    def get_oldest_node(self):
        nodes = self.gce.list_nodes()
        for n in nodes:
            print(n.name)

    def get_active_node_quantity(self):
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

    def get_ips(self):
        return self.get_node_ips()

    def expand(self):
        if self.get_active_node_quantity() < self.max_nodes:
            now = datetime.now()
            node_name = 'gpu-' + now.strftime(self.format)
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
            return "New node running at " + new_node.public_ips[0] + " with name " + node_name
        else:
            return "Already " + str(self.get_active_node_quantity()) + " nodes running. (max)"
            
    def shrink(self):
        if self.get_active_node_quantity() > self.min_nodes:
            # Find oldest node, Destroy it
            # use strptime to parse node names and compare
            nodes = self.gce.list_nodes()
            oldest_date = datetime.strptime(nodes[0].name[4:], self.format)
            oldest_node = nodes[0]

            for node in nodes:
                date = datetime.strptime(node.name[4:], self.format)
                if date < oldest_date:
                   oldest_node = node 

            self.gce.destroy_node(oldest_node)
            return "Destroyed node: " + oldest_node.name + "."
        else:
            return "Only " + self.min_nodes + " nodes running. (min)"

    


class ElasticCloud(GCEMixin):
    def __init__(self, provider_name):
        # load yaml config
        service_config = None
        with open('cloudconfig/config.yaml') as f:
            service_config = yaml.load(f)

        if provider_name == "GCE":
            service = service_config['services']['gce']
            self.cloud = GCEMixin(service)
        else:
            print("Provider not yet offered.")
            raise NotImplementedError


        # Paramiko ssh library set up
        ssh_config_filename = os.path.expanduser('~/.ssh/config')

        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.load_system_host_keys()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        config = paramiko.config.SSHConfig()
        
        with open(ssh_config_filename) as f:
            config.parse(f)
        
        elastic_cloud_ssh_config = 'ElasticCloud'
        user_config = config.lookup(elastic_cloud_ssh_config)
        pkey_fn = user_config['identityfile'][0]
        self.username = user_config['user']
        self.pkey = paramiko.RSAKey.from_private_key_file(pkey_fn)#, password="placeholder")


    def expand(self):
        print(self.cloud.expand())

    def shrink(self):
        print(self.cloud.shrink())

    def dump_state(self):

        # paramiko ssh test
        ips = self.cloud.get_ips()
        for ip in ips:
            host = ip[0]
            print('host:',host)
            print('username:',self.username)
            self.ssh_client.connect(host, username=self.username, pkey=self.pkey)

            commands = ['ls -la', 'uname', 'lsb_release -a']

            for command in commands:
                print('\n\n\n\n\nCOMMAND:',command)
                stdin, stdout, stderr = self.ssh_client.exec_command(command)
                for l in stdout.readlines():
                    print(l)
                print("stderr",stderr.readlines())

    def status(self):
        raise NotImplementedError

    def watch(self):
        raise NotImplementedError
