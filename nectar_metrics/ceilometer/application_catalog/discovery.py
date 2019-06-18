from ceilometer import keystone_client
from ceilometer.polling import plugin_base

from muranoclient import client


class EnvironmentDiscovery(plugin_base.DiscoveryBase):

    def __init__(self, conf):
        super(EnvironmentDiscovery, self).__init__(conf)
        creds = conf.service_credentials
        self.client = client.Client(
            version='1',
            session=keystone_client.get_session(conf),
            region_name=creds.region_name,
            service_type='application-catalog',
        )

    def discover(self, manager, param=None):
        return self.client.environments.list(all_tenants=True)
