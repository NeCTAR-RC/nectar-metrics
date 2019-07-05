import collections
import itertools

from ceilometer.polling import plugin_base
from ceilometer import sample

from oslo_log import log
LOG = log.getLogger(__name__)


class EnvironmentPollster(plugin_base.PollsterBase):
    """Collect stats on murano application environments"""

    @property
    def default_discovery(self):
        return 'application_catalog'

    def get_samples(self, manager, cache, resources):
        samples = []

        total = sample.Sample(
            name='global.application_catalog.environments',
            type=sample.TYPE_GAUGE,
            unit='environments',
            volume=len(resources),
            user_id=None,
            project_id=None,
            resource_id='global-stats')

        samples.append(total)

        env_status = collections.defaultdict(int)
        for env in resources:
            env_status[env.status] += 1

        for status, count in env_status.items():
            s = sample.Sample(
                name="global.application_catalog.environments.{}"
                     .format(status.replace(" ", "_")),
                type=sample.TYPE_GAUGE,
                unit="environments",
                volume=count,
                user_id=None,
                project_id=None,
                resource_id='global-stats'
                )
            samples.append(s)

        sample_iters = []
        sample_iters.append(samples)
        LOG.debug("Sending samples %s", sample_iters)
        return itertools.chain(*sample_iters)
