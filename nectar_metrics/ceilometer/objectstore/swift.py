from collections import defaultdict
import itertools
from oslo_log import log
from oslo_config import cfg

import uuid
import hashlib

from ceilometer.agent import plugin_base
from ceilometer import sample


LOG = log.getLogger(__name__)


opt_group = cfg.OptGroup(name='swift',
                         title='Options for Swift')

OPTS = [
    cfg.StrOpt('region_name',
               help='Swift Region'),
]


class SwiftDiskPollster(plugin_base.PollsterBase):
    """ Collects stats on swift disks
    """

    def __init__(self, conf):
        conf.register_group(opt_group)
        conf.register_opts(OPTS, group=opt_group)
        super(SwiftDiskPollster, self).__init__(conf)

    @property
    def default_discovery(self):
        return 'swift_disks'

    def _make_sample(self, metric, value, disk):
        host = self.conf.host
        region = self.conf.swift.region_name
        LOG.debug('REGION %s' % region)
        resource = region + host + disk
        resource_id = str(uuid.UUID(hashlib.sha1(resource).hexdigest()[:32]))

        return sample.Sample(
            name='swift.disk.%s' % metric,
            type=sample.TYPE_GAUGE,
            unit='B',
            volume=value,
            user_id=None,
            project_id=None,
            resource_id=resource_id,
            resource_metadata={'host': host, 'region': region, 'device_name': disk})

    def get_samples(self, manager, cache, resources):
        samples = []
        for disk in resources:
            mounted = disk['mounted']
            if not mounted:
                continue

            device_name = disk['device']
            available = disk['avail']
            used = disk['used']
            size = disk['size']

            samples.append(self._make_sample('available', available, device_name))
            samples.append(self._make_sample('used', used, device_name))
            samples.append(self._make_sample('size', size, device_name))

        sample_iters = []
        sample_iters.append(samples)
        return itertools.chain(*sample_iters)
