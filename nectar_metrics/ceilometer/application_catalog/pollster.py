import collections
import itertools

from ceilometer.polling import plugin_base
from ceilometer import sample

from nectar_metrics.ceilometer.application_catalog.common import murano_client

from oslo_log import log
LOG = log.getLogger(__name__)


class EnvironmentPollster(plugin_base.PollsterBase):
    """Collect stats on murano application environments"""

    @property
    def default_discovery(self):
        return 'application_catalog_environments'

    def get_samples(self, manager, cache, resources):
        samples = []
        projects = set()

        samples.append(sample.Sample(
            name='global.application_catalog.environments',
            type=sample.TYPE_GAUGE,
            unit='environments',
            volume=len(resources),
            user_id=None,
            project_id=None,
            resource_id='global-stats')
        )

        env_status = collections.defaultdict(int)
        for env in resources:
            projects.add(env.tenant_id)
            env_status[env.status] += 1

        samples.append(sample.Sample(
            name='active.projects.application_catalog',
            type=sample.TYPE_GAUGE,
            unit='Projects',
            volume=len(projects),
            user_id=None,
            project_id=None,
            resource_id='global-stats')
        )

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
        LOG.debug("Sending environment samples %s", sample_iters)
        return itertools.chain(*sample_iters)


class PackagePollster(plugin_base.PollsterBase):

    def __init__(self, conf):
        super(PackagePollster, self).__init__(conf)
        self.client = murano_client(conf)

    @property
    def default_discovery(self):
        return 'application_catalog_packages'

    def get_samples(self, manager, cache, resources):
        samples = []
        package_totals = dict.fromkeys(resources, 0)

        environment_list = self.client.environments.list(all_tenants=True)
        for env in environment_list:
            # NOTE(andybotting): The environment list doesn't provide all the
            # details we require, so must get each environment individually
            try:
                environment = self.client.environments.get(env.id)
                if environment.services:
                    for services in environment.services:
                        for val in services.values():
                            if type(val) == dict:
                                t = val.get('type')
                                if t and t.find('/') > 0:
                                    package = t.split('/')[0]
                                    package_totals[package] += 1
            except Exception as e:
                LOG.warning('Failed to add stats for package %s: %s',
                            package, e)

            for package, count in package_totals.items():
                s = sample.Sample(
                    name='application_catalog_package.environments',
                    type=sample.TYPE_GAUGE,
                    unit='packages',
                    volume=count,
                    user_id=None,
                    project_id=None,
                    resource_id=package,
                )
                samples.append(s)

        sample_iters = []
        sample_iters.append(samples)
        LOG.debug("Sending package samples %s", sample_iters)
        return itertools.chain(*sample_iters)
