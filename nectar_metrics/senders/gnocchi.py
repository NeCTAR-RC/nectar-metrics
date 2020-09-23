from gnocchiclient import client

from nectar_metrics.config import CONFIG
from nectar_metrics.senders import base
from nectar_metrics import keystone


GNOCCHI_API_VERSION = '1'


class GnocchiSender(base.BaseSender):

    def __init__(self):
        super(GnocchiSender, self).__init__()
        self.client = self._get_client()
        self.archive_policy = CONFIG.get('gnocchi', 'archive_policy')

    @staticmethod
    def _get_client():
        auth = keystone.get_auth_session()
        return client.Client(GNOCCHI_API_VERSION, auth)

    def send_metric(self, resource_type, resource_name, metric, value, time,
                    find_by_name=False):

        search_field = 'name' if find_by_name else 'id'
        resources = self.client.resource.search(
            resource_type=resource_type,
            query={'=': {search_field: resource_name}})
        num_resources = len(resources)
        if num_resources == 1:
            resource = resources[0]
        elif num_resources < 1:
            resource = self.client.resource.create(
                resource_type=resource_type,
                resource={'id': resource_name})
        else:
            self.log.error("More than 1 resource exists for type: %s and "
                           "name: %s" % (resource_type, resource_name))
            return

        metric_id = resource.get('metrics', {}).get(metric)
        if not metric_id:
            gmetric = self.client.metric.create(
                metric={'name': metric, 'resource_id': resource.get('id'),
                        'archive_policy_name': self.archive_policy})
            metric_id = gmetric.get('id')

        self.log.debug("Resource: %s:%s metric: %s" % (resource_type,
                                                       resource,
                                                       metric))
        self.client.metric.add_measures(metric=metric_id,
                                        measures=[dict(timestamp=time,
                                                       value=float(value))])

    def send_by_az(self, az, metric, value, time):
        self.send_metric('availability-zone', az, metric, value, time)

    def send_by_az_by_domain(self, az, domain, metric, value, time):
        metric = "%s-%s" % (metric, az)
        self.send_metric('domain', domain, metric,  value, time)

    def send_by_tenant(self, tenant, metric, value, time):
        self.send_metric('project', tenant, metric, value, time)

    def send_by_az_by_tenant(self, az, tenant, metric, value, time):
        metric = "%s-%s" % (metric, az)
        self.send_metric('project', tenant, metric, value, time)

    def send_by_az_by_home(self, az, home, metric, value, time):
        metric = "%s-%s" % (metric, az)
        self.send_metric('allocation_home', home, metric, value, time)

    def send_by_host_by_home(self, host, home, metric, value, time):
        _type = 'resource_provider'
        metric = "%s.usage.%s.%s" % (_type, home,
                                     metric.replace('used_', '').rstrip('s'))
        self.send_metric(_type, host, metric, value, time, find_by_name=True)

    def send_by_idp(self, idp, metric, value, time):
        return self.send_metric('idp', idp, metric, value, time)

    def send_global(self, resource, metric, value, time):
        return self.send_metric('generic', 'global-stats',
                                "%s-%s" % (resource, metric), value, time)
