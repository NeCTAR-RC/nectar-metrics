from collections import defaultdict
import itertools
from oslo_log import log

from ceilometer.agent import plugin_base
from ceilometer import sample


LOG = log.getLogger(__name__)


class SwiftDiskPollster(plugin_base.PollsterBase):
    """ Collects stats on swift disks
    """

    @property
    def default_discovery(self):
        return 'swift_disks'

    def _make_sample(self, metric, value, disk):
        host = self.conf.host
        region = self.conf.swift.region_name
        resource = region + host + disk
        resource_uuid = str(uuid.UUID(hashlib.sha1(metric).hexdigest()[:32]))
        
        return sample.Sample(
            name='swift.disk.%s' % metric,
            type=sample.TYPE_GAUGE,
            unit='B',
            volume=value,
            user_id=None,
            project_id=None,
            resource_id=resource_id,
            resource_metadata={'host': host, 'resgion': region})

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
            region = CONF.swift.region_name
            samples.append(self._make_sample('available', available, device_name)
            samples.append(self._make_sample('used', available, device_name)
            samples.append(self._make_sample('size', available, device_name)

        sample_iters = []
        sample_iters.append(samples)
        return itertools.chain(*sample_iters)
