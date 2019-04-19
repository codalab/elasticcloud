from cloud import GCEAdapter

from unittest import TestCase


class GCEAdapterTests(TestCase):

    def setUp(self):
        # Here's where you do any setup common to all of the tests
        self.adapter = GCEAdapter()

    # def test_<thing you're testing>_<expected result>()
    def test_spinning_up_worker_recognizes_it_is_in_spinning_up_state(self):
        # start spinning up process
        assert self.adapter.state == "spinning-up"  # Should probably be something like AdapterStates.SPINNING_UP

    def test_config_loads_environment_variables:
        CLOUDCUBE_URL = os.environ['CLOUDCUBE_URL']
        CLOUDCUBE_ACCESS_KEY_ID = os.environ['CLOUDCUBE_ACCESS_KEY_ID']
        CLOUDCUBE_SECRET_ACCESS_KEY = os.environ['CLOUDCUBE_SECRET_ACCESS_KEY']
        

if __name__ == "__main__":
    unittest.main()
