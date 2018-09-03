import itertools

try:
    # queens
    from ceilometer.polling import plugin_base
except ImportError:
    # < queens
    from ceilometer.agent import plugin_base
from ceilometer import sample
from ceilometer import keystone_client

from placementclient import client


class ResourceProviderPollster(plugin_base.PollsterBase):
    """ Collect stats on resource providers
    """

    def __init__(self, conf):
        super(ResourceProviderPollster, self).__init__(conf)
        creds = conf.service_credentials
        self.client = client.Client(
            version='1',
            session=keystone_client.get_session(conf),
            region_name=creds.region_name,
            interface=creds.interface,
        )

    @property
    def default_discovery(self):
        return 'resource_providers'

    def _make_sample(self, metric, value, resource_provider, unit):
        return sample.Sample(
            name='resource_provider.%s' % metric,
            type=sample.TYPE_GAUGE,
            unit=unit,
            volume=value,
            user_id=None,
            project_id=None,
            resource_id=resource_provider.id,
            resource_metadata={'name': resource_provider.name})

    def _make_total_sample(self, metric, value, unit):
        return sample.Sample(
            name='global.resource_provider.%s' % metric,
            type=sample.TYPE_GAUGE,
            unit=unit,
            volume=value,
            user_id=None,
            project_id=None,
            resource_id='global-stats')

    @staticmethod
    def _get_capacity(resource):
        return (int(resource['total']) *
                int(resource['allocation_ratio'])) - int(resource['reserved'])

    def get_samples(self, manager, cache, resources):
        samples = []
        vcpu_usage = 0
        memory_usage = 0
        disk_usage = 0
        vcpu_capacity = 0
        memory_capacity = 0
        disk_capacity = 0

        for resource_provider in resources:
            usages = resource_provider.usages()
            capacity = resource_provider.inventories()
            if hasattr(usages, 'VCPU'):
                samples.append(
                    self._make_sample('usage.vcpu',
                                      usages.VCPU,
                                      resource_provider, 'VCPU'))
                vcpu_usage += usages.VCPU
            if hasattr(usages, 'MEMORY_MB'):
                samples.append(
                    self._make_sample('usage.memory',
                                      usages.MEMORY_MB,
                                      resource_provider, 'MB'))
                memory_usage += usages.MEMORY_MB
            if hasattr(usages, 'DISK_GB'):
                samples.append(
                    self._make_sample('usage.disk',
                                      usages.DISK_GB,
                                      resource_provider, 'GB'))
                disk_usage += usages.DISK_GB
            if hasattr(capacity, 'VCPU'):
                total = self._get_capacity(capacity.VCPU)
                samples.append(
                    self._make_sample('capacity.vcpu',
                                      total,
                                      resource_provider, 'VCPU'))
                vcpu_capacity += total
            if hasattr(capacity, 'MEMORY_MB'):
                total = self._get_capacity(capacity.MEMORY_MB)
                samples.append(
                    self._make_sample('capacity.memory',
                                      total,
                                      resource_provider, 'MB'))
                memory_capacity += total
            if hasattr(capacity, 'DISK_GB'):
                total = self._get_capacity(capacity.DISK_GB)
                samples.append(
                    self._make_sample('capacity.disk',
                                      total,
                                      resource_provider, 'GB'))
                disk_capacity += total

        samples.append(
            self._make_total_sample('usage.vcpu', vcpu_usage, 'VCPU'))
        samples.append(
            self._make_total_sample('usage.memory', memory_usage, 'MB'))
        samples.append(
            self._make_total_sample('usage.disk', disk_usage, 'GB'))
        samples.append(
            self._make_total_sample('capacity.vcpu', vcpu_capacity, 'VCPU'))
        samples.append(
            self._make_total_sample('capacity.memory', memory_capacity, 'MB'))
        samples.append(
            self._make_total_sample('capacity.disk', disk_capacity, 'GB'))

        sample_iters = []
        sample_iters.append(samples)
        return itertools.chain(*sample_iters)
