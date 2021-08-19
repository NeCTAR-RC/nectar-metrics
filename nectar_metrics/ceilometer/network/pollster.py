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


    def _get_ip_availability_samples(self, resources):
        samples = []

        if self.conf.network.ipavailability_project_filter:
            resources = [r for r in resources if r.project_id == self.conf.network.ipavailability_project_filter]

        for network in resources:
            samples.append(sample.Sample(
                name='ip.availability.used',
                type=sample.TYPE_GAUGE,
                unit='IP',
                volume=network.used_ips,
                user_id=None,
                project_id=network.project_id,
                resource_id=network.network_id,
                resource_metadata={'name': network.network_name})
            )
            samples.append(sample.Sample(
                name='ip.availability.total',
                type=sample.TYPE_GAUGE,
                unit='IP',
                volume=network.total_ips,
                user_id=None,
                project_id=network.project_id,
                resource_id=network.network_id,
                resource_metadata={'name': network.network_name})
            )

        return samples

    def _get_ports_used_samples(self, resources):
        samples = []

        samples.append(sample.Sample(
            name='global.network.ports_used',
            type=sample.TYPE_GAUGE,
            unit='ports',
            volume=sum([r.used_ips for r in resources]),
            user_id=None,
            project_id=None,
            resource_id='global-stats')
        )

        return samples

    def get_samples(self, manager, cache, resources):

        sample_iters = []

        sample_iters.append(self._get_ip_availability_samples(resources))
        sample_iters.append(self._get_ports_used_samples(resources))

        LOG.debug("Sending samples %s", sample_iters)
        return itertools.chain(*sample_iters)