from oslo_log import log

from nectarallocationclient import client
from nectarallocationclient import exceptions
from nectarallocationclient import states

from ceilometer import keystone_client
from ceilometer.polling import plugin_base


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
        active_allocations = []
        all_allocations = self.client.allocations.list(
            parent_request__isnull=True)
        for allocation in all_allocations:
            if allocation.status in [states.DELETED,
                                     states.SUBMITTED,
                                     states.APPROVED]:
                active_allocations.append(allocation)
            else:
                try:
                    allocation = self.client.allocations.get_last_approved(
                        parent_request=allocation.id)
                    active_allocations.append(allocation)
                except exceptions.AllocationDoesNotExist:
                    continue

        return active_allocations
