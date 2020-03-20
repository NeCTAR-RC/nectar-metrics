import itertools

from oslo_log import log

from ceilometer.polling import plugin_base
from ceilometer import sample


LOG = log.getLogger(__name__)


class LoadBalancerPollster(plugin_base.PollsterBase):
    """Collect stats on load balancers"""

    @property
    def default_discovery(self):
        return 'load_balancer'

    def get_samples(self, manager, cache, resources):
        samples = []
        total = 0
        for lb in resources:
            samples.append(sample.Sample(
                name='loadbalancer',
                type=sample.TYPE_GAUGE,
                unit='Instance',
                volume=1,
                user_id=None,
                project_id=lb.project_id,
                resource_id=lb.id,
                resource_metadata={'availability_zone': lb.availability_zone})
            )
            total += 1

        samples.append(sample.Sample(
            name='global.loadbalancer.loadbalancers',
            type=sample.TYPE_GAUGE,
            unit='Instance',
            volume=total,
            user_id=None,
            project_id=None,
            resource_id='')
        )

        sample_iters = []
        sample_iters.append(samples)
        LOG.debug("Sending samples %s", sample_iters)
        return itertools.chain(*sample_iters)
