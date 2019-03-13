import itertools

from ceilometer.polling import plugin_base
from ceilometer import sample


class ComputePollster(plugin_base.PollsterBase):

    @property
    def default_discovery(self):
        return 'all_instances'

    def get_samples(self, manager, cache, resources):
        samples = []

        for instance in resources:
            az = getattr(instance, 'OS-EXT-AZ:availability_zone', None)
            host = getattr(instance, 'OS-EXT-SRV-ATTR:host', None)
            if az and host:
                s = sample.Sample(
                    name='instance',
                    type=sample.TYPE_GAUGE,
                    unit='',
                    volume=1,
                    user_id=instance.user_id,
                    project_id=instance.tenant_id,
                    resource_id=instance.id,
                    resource_metadata={'availability_zone': az,
                                       'display_name': instance.name,
                                       'host': host,
                                       'flavor_id': instance.flavor['id']},
                )
                samples.append(s)
        
        sample_iters = []
        sample_iters.append(samples)
        return itertools.chain(*sample_iters)
