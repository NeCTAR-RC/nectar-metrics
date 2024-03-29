from ceilometer import keystone_client
from ceilometer.polling import plugin_base

from heatclient import client


class HeatStackDiscovery(plugin_base.DiscoveryBase):

    def __init__(self, conf):
        super(HeatStackDiscovery, self).__init__(conf)
        creds = conf.service_credentials
        self.client = client.Client(
            version='1',
            session=keystone_client.get_session(conf),
            region_name=creds.region_name,
            interface=creds.interface,
        )

    def discover(self, manager, param=None):
        return self.client.stacks.list()
