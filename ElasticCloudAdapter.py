import io

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

        # Load config from yaml OR from environment
        if os.path.exists(config_filename):
            with open(config_filename) as f:
                service_config = yaml.load(f, Loader=yaml.FullLoader)
        else:
            service_config = {
                'BROKER_URL': os.environ.get("BROKER_URL"),
                'services': {
                    'gce': {
                        'max': int(os.environ.get('GCE_MAX', 3)),
                        'min': int(os.environ.get('GCE_MIN', 1)),
                        'shrink_sensitivity': int(os.environ.get('GCE_SHRINK_SENSITIVITY', 3)),
                        'expand_sensitivity': int(os.environ.get('GCE_EXPAND_SENSITIVITY', 1)),
                        'image_name': os.environ.get('GCE_IMAGE_NAME'),
                        'use_gpus': os.environ.get('GCE_USE_GPUS'),
                        'vm_size': os.environ.get('GCE_VM_SIZE', "n1-standard-1"),
                        'datacenter': os.environ.get('GCE_DATACENTER', "us-west1-a"),
                        'service_account_key': os.environ.get('GCE_SERVICE_ACCOUNT_KEY'),
                        'service_account_file': os.environ.get('GCE_SERVICE_ACCOUNT_FILE'),
                    }
                }
            }

        self.config = service_config['services'][service_name]
        self.config['BROKER_URL'] = service_config['BROKER_URL']
    
    def _load_ssh_configuration(self):
        # Paramiko ssh library set up
        ssh_config_filename = os.path.expanduser('~/.ssh/config')

        self.ssh_client = paramiko.SSHClient()
        self.ssh_client.load_system_host_keys()
        self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        
        config = paramiko.config.SSHConfig()

        try:
            with open(ssh_config_filename) as f:
                config.parse(f)

            elastic_cloud_ssh_config = 'ElasticCloud'
            user_config = config.lookup(elastic_cloud_ssh_config)
            pkey_fn = user_config['identityfile'][0]
            self.username = user_config['user']
            self.pkey = paramiko.RSAKey.from_private_key_file(pkey_fn)#, password="placeholder")
        except (FileNotFoundError, KeyError):
            # We don't have a specific entry for this, use defaults
            self.username = "ubuntu"

            ssh_key = os.environ.get("GCE_SSH_PRIV")
            print(f"Unable to find ElasticCloud SSHConfig, attempting to use GCE_SSH_PRIV env var = \n{ssh_key}")
            if ssh_key:
                self.pkey = paramiko.RSAKey.from_private_key(io.StringIO(ssh_key))
            else:
                # try to use default local one
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
            print(f"Attempting to connect to {self.username}@{host} with key: \n{self.pkey}")
            self.ssh_client.connect(host, username=self.username, pkey=os.environ.get("GCE_SSH_PRIV"))
        except (ssh_exception.NoValidConnectionsError, ssh_exception.AuthenticationException):
            print("ERROR :: Could not connect to host, maybe it is spinning up/down?")

    def _run_ssh_command(self, host, command):
        self._connect(host)
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command)
        except (ssh_exception.NoValidConnectionsError, ssh_exception.AuthenticationException):
            print("ERROR :: Could not exec command on host, maybe it is spinning up/down?")
        return (stdin, stdout, stderr)

    def expand(self):
        raise NotImplementedError

    def shrink(self):
        raise NotImplementedError

    def dump_state(self):
        raise NotImplementedError

