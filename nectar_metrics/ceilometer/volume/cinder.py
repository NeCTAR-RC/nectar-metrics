from collections import defaultdict
import itertools
from oslo_log import log

import ceilometer
from ceilometer.agent import plugin_base
from ceilometer import sample


LOG = log.getLogger(__name__)


class CinderPollster(plugin_base.PollsterBase):
    """ Collects stats on total and size of volumes
    Gathers them on a:
      - per project
      - per project and availability-zone

    Metrics are:
      - nectar.project.volumes.count
      - nectar.project.volumes.size
      - nectar.project.volumes.count.<az>
      - nectar.project.volumes.size.<az>
    """

    @property
    def default_discovery(self):
        return 'volumes'

    def _volume_metrics(self, volumes):
        metrics = defaultdict(int)
        for volume in volumes:
            metrics['nectar.project.volumes.count'] += 1
            metrics['nectar.project.volumes.size'] += volume.size
        return metrics

    def _make_sample(self, metric, value, project):
        if 'size' in metric:
            unit = 'GB'
        else:
            unit = 'volumes'
        return sample.Sample(
            name=metric,
            type=sample.TYPE_GAUGE,
            unit=unit,
            volume=value,
            user_id=None,
            project_id=None,
            resource_id=project)
        
    def get_samples(self, manager, cache, resources):
        volumes_by_project = defaultdict(list)
        volumes_by_az_by_project = defaultdict(lambda: defaultdict(list))
        samples = []
        for volume in resources:
            project_id = getattr(volume, 'os-vol-tenant-attr:tenant_id')
            az = volume.availability_zone
            volumes_by_az_by_project[az][project_id].append(volume)
            volumes_by_project[project_id].append(volume)

        for project, volumes in volumes_by_project.items():
            for metric, value in self._volume_metrics(volumes).items():
                samples.append(self._make_sample(metric, value, project))
        for zone, items in volumes_by_az_by_project.items():
            for project, volumes in items.items():
                for metric, value in self._volume_metrics(volumes).items():
                    metric = "%s.%s" % (metric, zone)
                    samples.append(self._make_sample(metric, value, project))

        sample_iters = []
        sample_iters.append(samples)
        return itertools.chain(*sample_iters)
