from ceilometer.polling import plugin_base

from nectar_metrics.ceilometer.application_catalog.common import murano_client


class _BaseDiscovery(plugin_base.DiscoveryBase):
    def __init__(self, conf):
        super(_BaseDiscovery, self).__init__(conf)
        self.client = murano_client(conf)


class EnvironmentDiscovery(_BaseDiscovery):
    def discover(self, manager, param=None):
        """Discover environments to monitor"""
        return self.client.environments.list(all_tenants=True)


class PackageDiscovery(_BaseDiscovery):
    def discover(self, manager, param=None):
        """Discover packages to monitor"""
        package_list = self.client.packages.list(include_disabled=True,
                                                 limit=1000)
        packages = list(set([p.fully_qualified_name for p in package_list]))
        return packages
