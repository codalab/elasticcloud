from cloud import GCEAdapter
import os

import unittest
from unittest import TestCase
from unittest import mock


class GCEAdapterTests(TestCase):
    def setUp(self):
        self.CLOUDCUBE_URL = 'https://cloud-cube.s3.amazonaws.com/abcd'
        self.CLOUDCUBE_ACCESS_KEY_ID = 'LKKASDP9F8AAA3HQ2P9S'
        self.CLOUDCUBE_SECRET_ACCESS_KEY = 'KLlkjhsduf98hdsf98+hwjknw9ddjkh9h8kjhsdf'
        self.BROKER_URL = 'pyamqp://guest:guest@127.0.0.1:9001/abcd'
        self.max = 5
        self.min = 10
        self.shrink_sensitivity = 3
        self.expand_sensitivity = 4
        self.image_name = "ubuntu-testy-test"
        self.use_gpus = str(False)
        self.vm_size = "n1-standard-1"
        self.datacenter = "us-west1-a"
        self.service_account_key = '{test_key: {empty: 5} }'
        self.service_account_file = 'service_accounts/testy.json'
        os.environ['CLOUDCUBE_URL'] = self.CLOUDCUBE_URL              
        os.environ['CLOUDCUBE_ACCESS_KEY_ID'] = self.CLOUDCUBE_ACCESS_KEY_ID
        os.environ['CLOUDCUBE_SECRET_ACCESS_KEY'] = self.CLOUDCUBE_SECRET_ACCESS_KEY
        os.environ['BROKER_URL'] = self.BROKER_URL
        os.environ['GCE_MAX'] = str(self.max)
        os.environ['GCE_MIN'] = str(self.min)
        os.environ['GCE_SHRINK_SENSITIVITY'] = str(self.shrink_sensitivity)
        os.environ['GCE_EXPAND_SENSITIVITY'] = str(self.expand_sensitivity)
        os.environ['GCE_IMAGE_NAME'] = self.image_name
        os.environ['GCE_USE_GPUS'] = self.use_gpus
        os.environ['GCE_VM_SIZE'] = self.vm_size
        os.environ['GCE_DATACENTER'] = self.datacenter
        os.environ['GCE_SERVICE_ACCOUNT_FILE'] = self.service_account_file
        

    # def test_<thing you're testing>_<expected result>()
#    def test_spinning_up_worker_recognizes_it_is_in_spinning_up_state(self):
#        # start spinning up process
#        assert self.adapter.state == "spinning-up"  # Should probably be something like AdapterStates.SPINNING_UP

    def test_config_loads_environment_variables(self):
        with mock.patch('cloud.GCEAdapter._load_boto_client') as load_boto_patch:
            load_boto_patch.return_value = True
            with mock.patch('cloud.GCEAdapter._load_gce_account') as load_gce_patch:
                load_gce_patch.return_value = True
                self.adapter = GCEAdapter()

        assert self.adapter.CLOUDCUBE_URL == self.CLOUDCUBE_URL              
        assert self.adapter.CLOUDCUBE_ACCESS_KEY_ID == self.CLOUDCUBE_ACCESS_KEY_ID
        assert self.adapter.CLOUDCUBE_SECRET_ACCESS_KEY == self.CLOUDCUBE_SECRET_ACCESS_KEY
        assert self.adapter.config['BROKER_URL'] == self.BROKER_URL
        assert self.adapter.max_nodes == self.max
        assert self.adapter.min_nodes == self.min
        assert self.adapter.SHRINK_CRITERION == self.shrink_sensitivity
        assert self.adapter.EXPAND_CRITERION == self.expand_sensitivity
        assert self.adapter.image == self.image_name
        assert self.adapter.use_gpus == self.use_gpus
        assert self.adapter.size == self.vm_size
        assert self.adapter.datacenter == self.datacenter
        assert self.adapter.service_account_key_path == self.service_account_file

        


if __name__ == "__main__":
    unittest.main()
