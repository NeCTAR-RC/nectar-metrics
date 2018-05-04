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

    def _make_sample(self, metric, value, resource_id, unit='B'):

        return sample.Sample(
            name='quota.%s' % metric,
            type=sample.TYPE_GAUGE,
            unit=unit,
            volume=value,
            user_id=None,
            project_id=None,
            resource_id=resource_id)

    def get_samples(self, manager, cache, resources):
        samples = []
        swift_total = 0
        for allocation in resources:
            swift_allocated = 0
            if allocation['status'] == 'D':
                continue
            if allocation['status'] != 'A':
                allocation = self.api.get_last_approved(allocation['id'])
                if not allocation:
                    continue

            LOG.debug("Processing %s" % allocation['id'])
            if not allocation['project_id']:
                continue

            for quota in allocation['quotas']:
                if quota['resource'] == 'object.object':
                    swift_allocated = int(quota['quota']) * 1024 * 1024 * 1024

            swift_total += swift_allocated
            samples.append(
                self._make_sample('swift', swift_allocated,
                                  allocation['project_id']))
            samples.append(
                self._make_sample('swift.raw', swift_allocated * 3,
                                  allocation['project_id']))

        samples.append(sample.Sample(
            name='global.allocations.quota.swift',
            type=sample.TYPE_GAUGE,
            unit='B',
            volume=swift_total,
            user_id=None,
            project_id=None,
            resource_id='global-stats')
        )
        samples.append(sample.Sample(
            name='global.allocations.quota.swift.raw',
            type=sample.TYPE_GAUGE,
            unit='B',
            volume=swift_total * 3,
            user_id=None,
            project_id=None,
            resource_id='global-stats')
        )

        sample_iters = []
        sample_iters.append(samples)
        return itertools.chain(*sample_iters)
