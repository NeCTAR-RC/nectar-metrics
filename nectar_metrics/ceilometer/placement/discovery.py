from ceilometer import keystone_client
from ceilometer.polling import plugin_base
from oslo_log import log
from placementclient import client


LOG = log.getLogger(__name__)


class ResourceProviderDiscovery(plugin_base.DiscoveryBase):
    def __init__(self, conf):
        super().__init__(conf)
        creds = conf.service_credentials
        self.client = client.Client(
            version='1',
            session=keystone_client.get_session(conf),
            region_name=creds.region_name,
            interface=creds.interface,
        )

    def discover(self, manager, param=None):
        """Discover resource providers."""
        return self.client.resource_providers.list()
