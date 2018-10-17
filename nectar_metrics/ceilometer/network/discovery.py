from oslo_config import cfg

from ceilometer import neutron_client
from ceilometer.polling import plugin_base


opt_group = cfg.OptGroup(name='network',
                         title='Options for network')

OPTS = [
    cfg.StrOpt('ipavailability_project_filter',
               default=None,
               help="Only list networks owned by a certain project"
    )
]


class NetworkIPAvailabilityDiscovery(plugin_base.DiscoveryBase):

    def __init__(self, conf):
        super(NetworkIPAvailabilityDiscovery, self).__init__(conf)
        conf.register_group(opt_group)
        conf.register_opts(OPTS, group=opt_group)
        self.neutron_cli = neutron_client.Client(conf)

    def discover(self, manager, param=None):
        url = '/network-ip-availabilities?ip_version=4'
        if self.conf.network.ipavailability_project_filter:
            project = self.conf.network.ipavailability_project_filter
            url = url + '&tenant_id=%s' % project
        return self.neutron_cli.get(url)['network_ip_availabilities']
