import itertools

try:
    # queens
    from ceilometer.polling import plugin_base
except ImportError:
    # < queens
    from ceilometer.agent import plugin_base
from ceilometer import sample
from ceilometer import keystone_client

from magnumclient import client

from oslo_log import log
LOG = log.getLogger(__name__)


class MagnumClusterPollster(plugin_base.PollsterBase):
    """ Collect stats on magnum clusters
    """

    def __init__(self, conf):
        super(MagnumClusterPollster, self).__init__(conf)
        creds = conf.service_credentials
        self.client = client.Client(
            version='1',
            session=keystone_client.get_session(conf),
            region_name=creds.region_name,
            interface=creds.interface,
        )

    @property
    def default_discovery(self):
        return 'container_infra'

    def get_samples(self, manager, cache, resources):
        samples = []

        total = sample.Sample(
            name='global.container_infra.clusters',
            type=sample.TYPE_GAUGE,
            unit=None,
            volume=len(resources),
            user_id=None,
            project_id=None,
            resource_id='global-stats')

        samples.append(total)

        sample_iters = []
        sample_iters.append(samples)
        LOG.debug("Sending samples %s", sample_iters)
        return itertools.chain(*sample_iters)
