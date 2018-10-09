try:
    # queens
    from ceilometer.polling import plugin_base
except ImportError:
    # < queens
    from ceilometer.agent import plugin_base
from ceilometer import keystone_client

from magnumclient import client

class MagnumClusterDiscovery(plugin_base.DiscoveryBase):

    def __init__(self, conf):
        super(MagnumClusterDiscovery, self).__init__(conf)
        creds = conf.service_credentials
        self.client = client.Client(
            version='1',
            session=keystone_client.get_session(conf),
            region_name=creds.region_name,
            interface=creds.interface,
        )

    def discover(self, manager, param=None):
        return self.client.clusters.list()
