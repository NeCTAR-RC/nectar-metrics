import itertools

from ceilometer.polling import plugin_base
from ceilometer import sample

from oslo_log import log
LOG = log.getLogger(__name__)


class HeatPollster(plugin_base.PollsterBase):
    """Collect stats on heat stack"""

    @property
    def default_discovery(self):
        return 'orchestration'

    def get_samples(self, manager, cache, resources):
        samples = []
        projects = set()

        for stack in resources:
            projects.add(stack.project)

        samples.append(sample.Sample(
            name='global.orchestration.stacks',
            type=sample.TYPE_GAUGE,
            unit='stacks',
            volume=len(resources),
            user_id=None,
            project_id=None,
            resource_id='global-stats')
        )
        samples.append(sample.Sample(
            name='active.projects.orchestration',
            type=sample.TYPE_GAUGE,
            unit='Projects',
            volume=len(projects),
            user_id=None,
            project_id=None,
            resource_id='global-stats')
        )

        sample_iters = []
        sample_iters.append(samples)
        LOG.debug("Sending samples %s", sample_iters)
        return itertools.chain(*sample_iters)
