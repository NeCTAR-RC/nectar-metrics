from oslo_log import log

from ceilometer.agent import plugin_base
from nectar_metrics.ceilometer.allocation import api


LOG = log.getLogger(__name__)


class AllocationDiscovery(plugin_base.DiscoveryBase):

    def __init__(self, conf):
        super(AllocationDiscovery, self).__init__(conf)
        self.api = api.AllocationAPI(conf)

    def discover(self, manager, param=None):
        """Discover object server disks."""
        return self.api.get_all_parentless()
