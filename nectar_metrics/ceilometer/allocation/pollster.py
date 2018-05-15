from collections import defaultdict
import itertools

from oslo_log import log

from ceilometer.agent import plugin_base
from ceilometer import sample

from nectar_metrics.ceilometer.allocation import api


LOG = log.getLogger(__name__)


class AllocationPollster(plugin_base.PollsterBase):
    """ Collect stats on allocations
    """

    def __init__(self, conf):
        super(AllocationPollster, self).__init__(conf)
        self.api = api.AllocationAPI(conf)

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

    def get_samples(self, manager, cache, resources):
        samples = []
        swift_total = 0
        cinder_totals = defaultdict(int)
        counts = {'deleted': 0, 'active': 0, 'pending': 0}
        for allocation in resources:
            if allocation['status'] == 'D':
                counts['deleted'] += 1
                continue
            if allocation['status'] == 'E':
                counts['pending'] += 1
            if allocation['status'] != 'A':
                allocation = self.api.get_last_approved(allocation['id'])
                if not allocation:
                    continue

            LOG.debug("Processing %s" % allocation['id'])
            if not allocation['project_id']:
                continue

            counts['active'] += 1

            for quota in allocation['quotas']:
                if quota['resource'] == 'object.object':
                    swift_allocated = int(quota['quota'])
                    samples.append(
                        self._make_sample('swift', swift_allocated,
                                          allocation['project_id']))
                    swift_total += swift_allocated
                elif quota['resource'] == 'volume.gigabytes':
                    zone = quota['zone']
                    cinder_allocated = int(quota['quota'])
                    samples.append(
                        self._make_sample('cinder.%s' % zone,
                                          cinder_allocated,
                                          allocation['project_id']))
                    cinder_totals[zone] += cinder_allocated


        samples.append(sample.Sample(
            name='global.allocations.quota.swift',
            type=sample.TYPE_GAUGE,
            unit='GB',
            volume=swift_total,
            user_id=None,
            project_id=None,
            resource_id='global-stats')
        )
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

        sample_iters = []
        sample_iters.append(samples)
        return itertools.chain(*sample_iters)
