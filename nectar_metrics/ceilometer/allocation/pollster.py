from collections import defaultdict
import itertools

from nectarallocationclient import client
from nectarallocationclient import states
from oslo_log import log

from ceilometer.agent import plugin_base
from ceilometer import sample
from ceilometer import keystone_client

LOG = log.getLogger(__name__)


class AllocationPollster(plugin_base.PollsterBase):
    """ Collect stats on allocations
    """

    def __init__(self, conf):
        super(AllocationPollster, self).__init__(conf)
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

    def get_samples(self, manager, cache, resources):
        samples = []
        swift_total = 0
        cinder_totals = defaultdict(int)
        counts = {'deleted': 0, 'active': 0, 'pending': 0}
        for allocation in resources:
            LOG.debug(str(allocation.id) + ": " + allocation.status)
            if allocation.status == states.DELETED:
                counts['deleted'] += 1
                continue
            if allocation.status == states.SUBMITTED:
                counts['pending'] += 1
            if allocation.status != states.APPROVED:
                try:
                    allocation = self.client.allocations.get_last_approved(parent_request=allocation.id)
                except:
                    continue

            LOG.debug("Processing %s" % allocation.id)
            if not allocation.project_id:
                continue

            swift_allocated = allocation.get_allocated_swift_quota()
            if swift_allocated['object']:
                swift_allocated = int(swift_allocated['object'])
                samples.append(
                    self._make_sample('swift', swift_allocated,
                                      allocation.project_id))
                swift_total += swift_allocated
            cinder_allocated = allocation.get_allocated_cinder_quota()
            if cinder_allocated:
                for k,v in allocation.get_allocated_cinder_quota().items():
                    if k.startswith('gigabytes_'):
                        zone = k.split('_')[1]
                        q = int(v)
                        samples.append(
                            self._make_sample('cinder.%s' % zone,
                                              q,
                                              allocation.project_id))
                        cinder_totals[zone] += q


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
