import itertools

from ceilometer.polling import plugin_base
from ceilometer import sample

from oslo_log import log
LOG = log.getLogger(__name__)


class NetworkIPAvailabilityPollster(plugin_base.PollsterBase):
    """Collect stats on network IP availability"""

    @property
    def default_discovery(self):
        return 'network_ip_availability'

    def get_samples(self, manager, cache, resources):

        samples = []

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

        sample_iters = []
        sample_iters.append(samples)

        LOG.debug("Sending samples %s", sample_iters)
        return itertools.chain(*sample_iters)
