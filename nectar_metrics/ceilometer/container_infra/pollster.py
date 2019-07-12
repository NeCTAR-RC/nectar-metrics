import itertools

from ceilometer.polling import plugin_base
from ceilometer import sample

from oslo_log import log
LOG = log.getLogger(__name__)


class MagnumClusterPollster(plugin_base.PollsterBase):
    """Collect stats on magnum clusters"""

    @property
    def default_discovery(self):
        return 'container_infra'

    def get_samples(self, manager, cache, resources):
        samples = []

        total = sample.Sample(
            name='global.container_infra.clusters',
            type=sample.TYPE_GAUGE,
            unit='clusters',
            volume=len(resources),
            user_id=None,
            project_id=None,
            resource_id='global-stats')

        samples.append(total)

        sample_iters = []
        sample_iters.append(samples)
        LOG.debug("Sending samples %s", sample_iters)
        return itertools.chain(*sample_iters)
