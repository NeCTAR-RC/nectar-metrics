import itertools

from ceilometer.polling import plugin_base
from ceilometer import sample
from ceilometer import keystone_client
from oslo_log import log
from warreclient import client


LOG = log.getLogger(__name__)


class ReservationFlavorPollster(plugin_base.PollsterBase):
    """ Collect stats on reservation flavors
    """

    def __init__(self, conf):
        super(ReservationFlavorPollster, self).__init__(conf)
        creds = conf.service_credentials
        self.client = client.Client(
            version='1',
            session=keystone_client.get_session(conf),
            region_name=creds.region_name,
            interface=creds.interface,
        )

    @property
    def default_discovery(self):
        return 'reservation_flavors'

    def get_samples(self, manager, cache, resources):
        samples = []
        for flavor in resources:
            samples.append(
                sample.Sample(
                    name='warre.reservation-flavor.capacity',
                    type=sample.TYPE_GAUGE,
                    unit="Slots",
                    volume=flavor.slots,
                    user_id=None,
                    project_id=None,
                    resource_id=flavor.id,
                    resource_metadata={
                        'name': flavor.name,
                        'availability_zone': flavor.availability_zone,
                        'category': flavor.category})
            )

        sample_iters = []
        sample_iters.append(samples)
        return itertools.chain(*sample_iters)
