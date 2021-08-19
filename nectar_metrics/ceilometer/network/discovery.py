from ceilometer import keystone_client
from ceilometer.polling import plugin_base
from openstack import connection


class NetworkIPAvailabilityDiscovery(plugin_base.DiscoveryBase):

    def __init__(self, conf):
        super(NetworkIPAvailabilityDiscovery, self).__init__(conf)
        self.osc = connection.Connection(
                    session=keystone_client.get_session(conf))

    def discover(self, manager, param=None):

        ip_availabilities = list(self.osc.network.network_ip_availabilities(ip_version=4))
        return ip_availabilities