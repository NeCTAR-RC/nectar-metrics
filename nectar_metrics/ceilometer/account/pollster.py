from collections import defaultdict
import itertools
try:
    from urlparse import urlsplit
except ImportError:
    from urllib.parse import urlsplit

from manukaclient import client
from oslo_log import log

from ceilometer.polling import plugin_base
from ceilometer import sample
from ceilometer import keystone_client

LOG = log.getLogger(__name__)

ODD_IDPS = {
    'urn:mace:federation.org.au:testfed:uq.edu.au':
    'idp.uq.edu.au',

    'urn:mace:federation.org.au:testfed:au-idp.adelaide.edu.au':
    'idp.adelaide.edu.au',

    'urn:mace:federation.org.au:testfed:mq.edu.au':
    'idp.mq.edu.au',

    'urn:mace:aaf.edu.au:idp:468d3d0153e23dda76af9397bddf20ca':
    'idp.des.qld.gov.au',
}


class UserPollster(plugin_base.PollsterBase):
    """ Collect stats on Nectar user acccounts
    """

    def __init__(self, conf):
        super(UserPollster, self).__init__(conf)
        creds = conf.service_credentials
        self.client = client.Client(
            version='1',
            session=keystone_client.get_session(conf),
            region_name=creds.region_name,
            interface=creds.interface,
        )

    @property
    def default_discovery(self):
        return 'all_accounts'

    def get_samples(self, manager, cache, resources):
        user_count = 0
        user_with_orcid_count = 0
        users_by_idp = defaultdict(list)

        for user in resources:
            user_count += 1
            if user.orcid:
                user_with_orcid_count += 1
            for eid in user.external_ids:
                idp = eid.idp
                url = urlsplit(idp)
                if url.netloc:
                    users_by_idp[url.netloc.replace('.', '_')].append(user)
                elif idp in ODD_IDPS:
                    users_by_idp[ODD_IDPS[idp].replace('.', '_')].append(user)
                elif idp == 'idp.fake.nectar.org.au':
                    LOG.debug("Unknown IDP %s" % idp)
                    continue
                else:
                    LOG.warning("Unknown IDP %s" % idp)

        samples = []
        samples.append(sample.Sample(
            name='global.users.total',
            type=sample.TYPE_GAUGE,
            unit='User',
            volume=user_count,
            user_id=None,
            project_id=None,
            resource_id='global-stats')
        )
        samples.append(sample.Sample(
            name='global.users.with_orcid',
            type=sample.TYPE_GAUGE,
            unit='User',
            volume=user_with_orcid_count,
            user_id=None,
            project_id=None,
            resource_id='global-stats')
        )

        for idp, users in users_by_idp.items():
            samples.append(sample.Sample(
                name='users.total',
                type=sample.TYPE_GAUGE,
                unit='User',
                volume=len(users),
                user_id=None,
                project_id=None,
                resource_id=idp)
            )

        sample_iters = []
        sample_iters.append(samples)
        return itertools.chain(*sample_iters)
