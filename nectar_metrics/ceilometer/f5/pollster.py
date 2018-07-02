from ceilometer.hardware.pollsters.generic import \
    GenericHardwareDeclarativePollster
from ceilometer.hardware.pollsters import util


class F5VirtualServerPollster(GenericHardwareDeclarativePollster):
    CACHE_KEY = 'f5'
    mapping = None

    def __init__(self, conf):
        super(F5VirtualServerPollster, self).__init__(conf)

    @property
    def default_discovery(self):
        return 'f5_loadbalancers'

    def generate_samples(self, host_url, data):
        """Generate a list of Sample from the data returned by inspector

        :param host_url: host url of the endpoint
        :param data: list of data returned by the corresponding inspector
        """
        samples = []
        definition = self.meter_definition
        for (value, metadata, extra) in data:
            name = metadata.get('name')
            if 'NECTAR_RC' not in name:
                continue

            resource_id = name.split('/')[-1]
            s = util.make_sample_from_host(host_url,
                                           name=definition.name,
                                           sample_type=definition.type,
                                           unit=definition.unit,
                                           volume=value,
                                           resource_id=resource_id,
                                           res_metadata=metadata,
                                           name_prefix=None)
            samples.append(s)
        return samples
