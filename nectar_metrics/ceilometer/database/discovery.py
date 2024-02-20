from troveclient import client

from ceilometer import keystone_client
from ceilometer.polling import plugin_base


class DatabaseDiscovery(plugin_base.DiscoveryBase):

    def __init__(self, conf):
        super().__init__(conf)
        self.client = client.Client('1.0',
                                    session=keystone_client.get_session(conf))

    def discover(self, manager, param=None):
        return self.client.mgmt_instances.list()
