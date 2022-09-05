
from ceilometer.polling import plugin_base
from ceilometer import keystone_client
from oslo_log import log
from warreclient import client


LOG = log.getLogger(__name__)


class ReservationFlavorDiscovery(plugin_base.DiscoveryBase):

    def __init__(self, conf):
        super(ReservationFlavorDiscovery, self).__init__(conf)
        creds = conf.service_credentials
        self.client = client.Client(
            version='1',
            session=keystone_client.get_session(conf),
            region_name=creds.region_name,
            interface=creds.interface,
        )

    def discover(self, manager, param=None):
        """Discover reservation flavors."""
        return self.client.flavors.list(all_projects=True)
