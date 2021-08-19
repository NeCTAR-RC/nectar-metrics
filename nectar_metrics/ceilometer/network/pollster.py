import itertools

from ceilometer.polling import plugin_base
from ceilometer import sample

from oslo_config import cfg
from oslo_log import log

LOG = log.getLogger(__name__)

opt_group = cfg.OptGroup(name='network',
                         title='Options for network')

OPTS = [
    cfg.StrOpt('ipavailability_project_filter',
               default=None,
               help="Only list networks owned by a certain project")
]

class NetworkIPAvailabilityPollster(plugin_base.PollsterBase):
    """Collect stats on network IP availability"""
    def __init__(self, conf):
        super(NetworkIPAvailabilityPollster, self).__init__(conf)
        conf.register_group(opt_group)
        conf.register_opts(OPTS, group=opt_group)

    @property
    def default_discovery(self):
        return 'network_ip_availability'

    def get_samples(self, manager, cache, resources):
        samples = []

        if self.conf.network.ipavailability_project_filter:
            resources = [r for r in resources if r['tenant_id'] == self.conf.network.ipavailability_project_filter]

        for network in resources:
            samples.append(sample.Sample(
                name='ip.availability.used',
                type=sample.TYPE_GAUGE,
                unit='IP',
                volume=network['used_ips'],
                user_id=None,
                project_id=network['tenant_id'],
                resource_id=network['network_id'],
                resource_metadata={'name': network['network_name']})
            )
            samples.append(sample.Sample(
                name='ip.availability.total',
                type=sample.TYPE_GAUGE,
                unit='IP',
                volume=network['total_ips'],
                user_id=None,
                project_id=network['tenant_id'],
                resource_id=network['network_id'],
                resource_metadata={'name': network['network_name']})
            )

        sample_iters = []
        sample_iters.append(samples)
        LOG.debug("Sending samples %s", sample_iters)
        return itertools.chain(*sample_iters)
