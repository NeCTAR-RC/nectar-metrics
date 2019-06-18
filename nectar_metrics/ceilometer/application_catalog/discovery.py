from ceilometer import keystone_client
from ceilometer.polling import plugin_base

from muranoclient import client


class MuranoEnvironmentDiscovery(plugin_base.DiscoveryBase):

    def __init__(self, conf):
        super(MuranoEnvironmentDiscovery, self).__init__(conf)
        creds = conf.service_credentials
        session = keystone_client.get_session(conf)
        endpoint = session.get_endpoint(service_type='application-catalog')
        self.client = client.Client(
            version='1',
            session=session,
            region_name=creds.region_name,
            endpoint_override=endpoint)

    def discover(self, manager, param=None):
        return self.client.environments.list(all_tenants=True)
