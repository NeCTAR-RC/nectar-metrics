import requests

from oslo_config import cfg
from oslo_log import log


LOG = log.getLogger(__name__)

opt_group = cfg.OptGroup(name='allocations',
                         title='Options for allocations')

OPTS = [
    cfg.StrOpt('api_url',
               help='Allocations API URL'),
    cfg.StrOpt('api_username',
               help='Allocations API username'),
    cfg.StrOpt('api_password',
               help='Allocations API password'),
]


class AllocationAPI(object):

    def __init__(self, conf):
        self.conf = conf
        conf.register_group(opt_group)
        conf.register_opts(OPTS, group=opt_group)

        session = requests.Session()
        session.auth = (self.conf.allocations.api_username,
                        self.conf.allocations.api_password)
        self.session = session

    def json_get(self, url, params):
        response = self.session.get('%s%s' % (self.conf.allocations.api_url,
                                              url),
                                    params=params)
        return response.json()

    def get_all_parentless(self):
        return self.json_get('/allocations/',
                             {'parent_request__isnull': True})

    def get_last_approved(self, id):
        allocations = self.json_get('/allocations/',
                                    {'parent_request': id, 'status': 'A'})
        if allocations:
            return allocations[0]
