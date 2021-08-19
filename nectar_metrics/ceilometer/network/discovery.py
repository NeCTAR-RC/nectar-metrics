from ceilometer import neutron_client
from ceilometer.polling import plugin_base


class NetworkIPAvailabilityDiscovery(plugin_base.DiscoveryBase):

    def __init__(self, conf):
        super(NetworkIPAvailabilityDiscovery, self).__init__(conf)
        self.neutron_cli = neutron_client.Client(conf).client

    def discover(self, manager, param=None):
        url = '/network-ip-availabilities?ip_version=4'
        return self.neutron_cli.get(url)['network_ip_availabilities']
