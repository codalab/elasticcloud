import os
import paramiko
from paramiko import ssh_exception
import yaml


# TODO: When paramiko is updated > 2.4.2 remove this warning squelch
# Last checked March 14, 2019
import warnings
warnings.filterwarnings(action='ignore', module='.*paramiko.*')


class ElasticCloudAdapter:

    ACTION_SHRINK = 'shrink'
    ACTION_EXPAND = 'expand'
    ACTION_DO_NOTHING = 'do_nothing'

    def __init__(self, provider_name):
        self._load_configuration(provider_name)
        self._load_ssh_configuration()

    def _load_configuration(self, service_name):
        service_config = None
        config_filename = 'cloud_config/config.yaml'

        with open(config_filename) as f:
            service_config = yaml.load(f, Loader=yaml.FullLoader)

        self.config = service_config['services'][service_name]
    
    def _load_ssh_configuration(self):
        # Paramiko ssh library set up
        ssh_config_filename = os.path.expanduser('~/.ssh/config')

        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.load_system_host_keys()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        config = paramiko.config.SSHConfig()
        
        with open(ssh_config_filename) as f:
            config.parse(f)

        try:
            elastic_cloud_ssh_config = 'ElasticCloud'
            user_config = config.lookup(elastic_cloud_ssh_config)
            pkey_fn = user_config['identityfile'][0]
            self.username = user_config['user']
            self.pkey = paramiko.RSAKey.from_private_key_file(pkey_fn)#, password="placeholder")
        except KeyError:
            # We don't have a specific entry for this, use defaults
            self.username = "ubuntu"
            self.pkey = paramiko.RSAKey.from_private_key_file(os.path.expanduser("~/.ssh/id_rsa"))

    def _connect(self, host):
        # Delete old known hosts entry for GCE VM ip address
        known_hosts_filename = os.path.expanduser('~/.ssh/known_hosts')
        if os.path.exists(known_hosts_filename):
            kh = None
            with open(known_hosts_filename, 'r') as f:
                kh = f.readlines()
            with open(known_hosts_filename, 'w') as f:
                for line in kh:
                    line_ip = line.split()[0]
                    if not line_ip == host:
                        f.write(line)
        try:
            self.ssh_client.connect(host, username=self.username, pkey=self.pkey)
        except (ssh_exception.NoValidConnectionsError, ssh_exception.AuthenticationException):
            print("ERROR :: Could not connect to host, maybe it is spinning down?")

    def _run_ssh_command(self, host, command):
        self._connect(host)
        stdin, stdout, stderr = self.ssh_client.exec_command(command)
        return (stdin, stdout, stderr)

    def expand(self):
        raise NotImplementedError

    def shrink(self):
        raise NotImplementedError

    def dump_state(self):
        raise NotImplementedError

