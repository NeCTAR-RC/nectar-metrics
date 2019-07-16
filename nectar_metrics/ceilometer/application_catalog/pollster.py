import collections
import itertools

from ceilometer import keystone_client
from ceilometer.polling import plugin_base
from ceilometer import sample

from muranoclient import client

from oslo_log import log
LOG = log.getLogger(__name__)


class EnvironmentPollster(plugin_base.PollsterBase):
    """Collect stats on murano application environments"""

    @property
    def default_discovery(self):
        return 'application_catalog_environments'

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
        LOG.debug("Sending environment samples %s", sample_iters)
        return itertools.chain(*sample_iters)


class PackagePollster(plugin_base.PollsterBase):

    def __init__(self, conf):
        super(PackagePollster, self).__init__(conf)
        creds = conf.service_credentials
        self.client = client.Client(
            version='1',
            session=keystone_client.get_session(conf),
            region_name=creds.region_name,
            service_type='application-catalog',
        )


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
            environment = self.client.environments.get(env.id)
            for services in environment.services:
                for val in services.values():
                    if type(val) == dict:
                        t = val.get('type')
                        if t and t.find('/') > 0:
                            package = t.split('/')[0]
                            package_totals[package] += 1

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
