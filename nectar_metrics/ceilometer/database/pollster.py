import itertools

from oslo_log import log

from ceilometer.polling import plugin_base
from ceilometer import sample


LOG = log.getLogger(__name__)


class DatabasePollster(plugin_base.PollsterBase):
    """Collect stats on databases"""

    @property
    def default_discovery(self):
        return 'all_databases'

    def get_samples(self, manager, cache, resources):
        samples = []
        total = 0
        projects = set()
        for db in resources:
            samples.append(sample.Sample(
                name='database',
                type=sample.TYPE_GAUGE,
                unit='Instance',
                volume=1,
                user_id=None,
                project_id=db.tenant_id,
                resource_id=db.id)
            )
            total += 1
            projects.add(db.tenant_id)

        samples.append(sample.Sample(
            name='global.database.databases',
            type=sample.TYPE_GAUGE,
            unit='Instance',
            volume=total,
            user_id=None,
            project_id=None,
            resource_id='global-stats')
        )

        samples.append(sample.Sample(
            name='active.projects.database',
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
