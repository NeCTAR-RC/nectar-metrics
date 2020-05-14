from oslo_log import log

from manukaclient import client

from ceilometer import keystone_client
from ceilometer.polling import plugin_base


LOG = log.getLogger(__name__)


class AccountDiscovery(plugin_base.DiscoveryBase):

    def __init__(self, conf):
        super(AccountDiscovery, self).__init__(conf)
        creds = conf.service_credentials
        self.client = client.Client(
            version='1',
            session=keystone_client.get_session(conf),
            region_name=creds.region_name,
            interface=creds.interface,
        )

    def discover(self, manager, param=None):
        """Discover user records from Manuka."""
        return self.client.users.list(state='created')
