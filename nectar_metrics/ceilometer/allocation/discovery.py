from oslo_log import log

from ceilometer.agent import plugin_base
from nectarallocationclient import client

from ceilometer import keystone_client

LOG = log.getLogger(__name__)


class AllocationDiscovery(plugin_base.DiscoveryBase):

    def __init__(self, conf):
        super(AllocationDiscovery, self).__init__(conf)
        creds = conf.service_credentials
        self.client = client.Client(
            version='1',
            session=keystone_client.get_session(conf),
            region_name=creds.region_name,
            interface=creds.interface,
        )

    def discover(self, manager, param=None):
        """Discover object server disks."""
        return self.client.allocations.list(parent_request__isnull=True)
