from openstack import connection

from ceilometer import keystone_client
from ceilometer.polling import plugin_base


class LoadBalancerDiscovery(plugin_base.DiscoveryBase):

    def __init__(self, conf):
        super(LoadBalancerDiscovery, self).__init__(conf)
        self.client = connection.Connection(
            session=keystone_client.get_session(conf))

    def discover(self, manager, param=None):
        return self.client.load_balancer.load_balancers()
