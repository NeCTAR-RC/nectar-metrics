from collections import defaultdict
import itertools

from nectarallocationclient import client
from nectarallocationclient import states
from oslo_log import log

from ceilometer import keystone_client
from ceilometer.polling import plugin_base
from ceilometer import sample


LOG = log.getLogger(__name__)


class AllocationPollsterBase(plugin_base.PollsterBase):
    """Collect stats on allocations"""

    def __init__(self, conf):
        super(AllocationPollsterBase, self).__init__(conf)
        creds = conf.service_credentials
        self.client = client.Client(
            version='1',
            session=keystone_client.get_session(conf),
            region_name=creds.region_name,
            interface=creds.interface,
        )

    @property
    def default_discovery(self):
        return 'all_allocations'

    def _make_sample(self, metric, value, resource_id, unit='GB'):

        return sample.Sample(
            name='quota.%s' % metric,
            type=sample.TYPE_GAUGE,
            unit=unit,
            volume=value,
            user_id=None,
            project_id=resource_id,
            resource_id=resource_id)


class AllocationStatusPollster(AllocationPollsterBase):

    def get_samples(self, manager, cache, resources):
        samples = []
        counts = {'deleted': 0, 'active': 0, 'pending': 0}
        home_totals = defaultdict(int)
        bundle_totals = defaultdict(int)

        for allocation in resources:
            if allocation.status == states.DELETED:
                counts['deleted'] += 1
                continue
            elif allocation.status == states.SUBMITTED:
                counts['pending'] += 1
                continue

            if not allocation.project_id:
                continue
            counts['active'] += 1
            home_totals[allocation.allocation_home] += 1
            bundle_totals[allocation.bundle] += 1

        for status, count in counts.items():
            samples.append(sample.Sample(
                name='global.allocations.%s' % status,
                type=sample.TYPE_GAUGE,
                unit='Allocation',
                volume=count,
                user_id=None,
                project_id=None,
                resource_id='global-stats')
            )

        for home, count in home_totals.items():
            samples.append(sample.Sample(
                name='allocations.active',
                type=sample.TYPE_GAUGE,
                unit='Allocation',
                volume=count,
                user_id=None,
                project_id=None,
                resource_id=home)
            )

        for bundle, count in bundle_totals.items():
            if bundle is None:
                bundle = 'Custom'
            samples.append(sample.Sample(
                name='allocations.bundle',
                type=sample.TYPE_GAUGE,
                unit='Allocation',
                volume=count,
                user_id=None,
                project_id=None,
                resource_id=bundle)
            )

        sample_iters = []
        sample_iters.append(samples)
        return itertools.chain(*sample_iters)


class NovaQuotaAllocationPollster(AllocationPollsterBase):

    def get_samples(self, manager, cache, resources):
        samples = []
        cores_total = 0
        ram_total = 0
        instances_total = 0
        cores_home_totals = defaultdict(int)
        ram_home_totals = defaultdict(int)
        instances_home_totals = defaultdict(int)

        for allocation in resources:
            if allocation.status == states.DELETED:
                continue
            elif allocation.status == states.SUBMITTED:
                continue

            if not allocation.project_id:
                continue

            home = allocation.allocation_home
            nova_allocated = allocation.get_allocated_nova_quota()
            if nova_allocated:
                cores = nova_allocated.get('cores')
                ram = nova_allocated.get('ram')
                instances = nova_allocated.get('instances')
                if cores is not None:
                    samples.append(self._make_sample('nova.cores', cores,
                                                     allocation.project_id,
                                                     unit='VCPU')),
                    cores_total += cores
                    cores_home_totals[home] += cores
                if ram:
                    samples.append(self._make_sample('nova.ram', ram,
                                                     allocation.project_id,
                                                     unit='MB'))
                    ram_total += ram
                    ram_home_totals[home] += ram
                if instances:
                    samples.append(self._make_sample('nova.instances',
                                                     instances,
                                                     allocation.project_id))
                    instances_total += instances
                    instances_home_totals[home] += instances

        samples.append(sample.Sample(
            name='global.allocations.quota.nova.cores',
            type=sample.TYPE_GAUGE,
            unit='VCPU',
            volume=cores_total,
            user_id=None,
            project_id=None,
            resource_id='global-stats')
        )
        samples.append(sample.Sample(
            name='global.allocations.quota.nova.ram',
            type=sample.TYPE_GAUGE,
            unit='GB',
            volume=ram_total,
            user_id=None,
            project_id=None,
            resource_id='global-stats')
        )
        samples.append(sample.Sample(
            name='global.allocations.quota.nova.instances',
            type=sample.TYPE_GAUGE,
            unit='Instances',
            volume=instances_total,
            user_id=None,
            project_id=None,
            resource_id='global-stats')
        )
        for home, count in cores_home_totals.items():
            samples.append(sample.Sample(
                name='allocations.quota.nova.cores',
                type=sample.TYPE_GAUGE,
                unit='VCPU',
                volume=count,
                user_id=None,
                project_id=None,
                resource_id=home)
            )
        for home, count in ram_home_totals.items():
            samples.append(sample.Sample(
                name='allocations.quota.nova.ram',
                type=sample.TYPE_GAUGE,
                unit='GB',
                volume=count,
                user_id=None,
                project_id=None,
                resource_id=home)
            )
        for home, count in instances_home_totals.items():
            samples.append(sample.Sample(
                name='allocations.quota.nova.instances',
                type=sample.TYPE_GAUGE,
                unit='Instances',
                volume=count,
                user_id=None,
                project_id=None,
                resource_id=home)
            )

        sample_iters = []
        sample_iters.append(samples)
        return itertools.chain(*sample_iters)


class CinderQuotaAllocationPollster(AllocationPollsterBase):

    def get_samples(self, manager, cache, resources):
        samples = []
        cinder_totals = defaultdict(int)
        for allocation in resources:
            if allocation.status == states.DELETED:
                continue
            elif allocation.status == states.SUBMITTED:
                continue

            if not allocation.project_id:
                continue

            cinder_allocated = allocation.get_allocated_cinder_quota()
            if cinder_allocated:
                for k, v in allocation.get_allocated_cinder_quota().items():
                    if k.startswith('gigabytes_'):
                        zone = k.split('_')[1]
                        q = int(v)
                        samples.append(
                            self._make_sample('cinder.%s' % zone,
                                              q,
                                              allocation.project_id))
                        cinder_totals[zone] += q

        for zone, total in cinder_totals.items():
            samples.append(sample.Sample(
                name='global.allocations.quota.cinder.%s' % zone,
                type=sample.TYPE_GAUGE,
                unit='GB',
                volume=total,
                user_id=None,
                project_id=None,
                resource_id='global-stats')
            )
        sample_iters = []
        sample_iters.append(samples)
        return itertools.chain(*sample_iters)


class SwiftQuotaAllocationPollster(AllocationPollsterBase):

    def get_samples(self, manager, cache, resources):
        samples = []
        swift_total = 0
        home_totals = defaultdict(int)

        for allocation in resources:
            if allocation.status == states.DELETED:
                continue
            elif allocation.status == states.SUBMITTED:
                continue

            if not allocation.project_id:
                continue

            swift_allocated = allocation.get_allocated_swift_quota()
            if swift_allocated['object']:
                swift_allocated = int(swift_allocated['object'])
                samples.append(
                    self._make_sample('swift', swift_allocated,
                                      allocation.project_id))
                swift_total += swift_allocated
                home_totals[allocation.allocation_home] += swift_allocated

        samples.append(sample.Sample(
            name='global.allocations.quota.swift',
            type=sample.TYPE_GAUGE,
            unit='GB',
            volume=swift_total,
            user_id=None,
            project_id=None,
            resource_id='global-stats')
        )
        for home, count in home_totals.items():
            samples.append(sample.Sample(
                name='allocations.quota.swift',
                type=sample.TYPE_GAUGE,
                unit='GB',
                volume=count,
                user_id=None,
                project_id=None,
                resource_id=home)
            )

        sample_iters = []
        sample_iters.append(samples)
        return itertools.chain(*sample_iters)


class CloudkittyQuotaAllocationPollster(AllocationPollsterBase):

    def get_samples(self, manager, cache, resources):
        samples = []
        cloudkitty_total = 0
        home_totals = defaultdict(int)

        for allocation in resources:
            if allocation.status == states.DELETED:
                continue
            elif allocation.status == states.SUBMITTED:
                continue

            if not allocation.project_id:
                continue

            cloudkitty_allocated = allocation.get_allocated_cloudkitty_quota()
            budget = cloudkitty_allocated.get('budget', 0)
            if budget:
                budget = int(budget)
                samples.append(
                    self._make_sample('budget', budget,
                                      allocation.project_id))
                cloudkitty_total += budget
                home_totals[allocation.allocation_home] += budget

        samples.append(sample.Sample(
            name='global.allocations.quota.budget',
            type=sample.TYPE_GAUGE,
            unit='SU',
            volume=cloudkitty_total,
            user_id=None,
            project_id=None,
            resource_id='global-stats')
        )
        for home, count in home_totals.items():
            samples.append(sample.Sample(
                name='allocations.quota.budget',
                type=sample.TYPE_GAUGE,
                unit='SU',
                volume=count,
                user_id=None,
                project_id=None,
                resource_id=home)
            )

        sample_iters = []
        sample_iters.append(samples)
        return itertools.chain(*sample_iters)
