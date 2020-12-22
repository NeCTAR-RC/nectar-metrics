import uuid

from nectar_metrics import config
from nectar_metrics import gnocchi
from nectar_metrics.senders import base


CONF = config.CONFIG


class GnocchiSender(base.BaseSender):

    def __init__(self):
        super(GnocchiSender, self).__init__()
        self.client = gnocchi.get_client()
        self.archive_policy = CONF.get('gnocchi', 'archive_policy')

    def send_metric(self, resource_type, resource_name, metric, value, time,
                    by_name=False, create_resource=True):
        if by_name:
            terms = [{'=': {'name': resource_name}},
                     {'=': {'ended_at': None}}]
        else:
            terms = [{'=': {'id': resource_name}}]

        resources = self.client.resource.search(
            resource_type=resource_type,
            query={'and': terms})
        num_resources = len(resources)
        if num_resources == 1:
            resource = resources[0]
        elif num_resources == 0:
            if not create_resource:
                self.log.error("Could not find resource %s", resource_name)
                return

            if by_name:
                args = {'id': str(uuid.uuid4()), 'name': resource_name}
            else:
                args = {'id': resource_name}
            resource = self.client.resource.create(
                resource_type=resource_type,
                resource=args)
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
        # Don't create missing resources, since they should be created by
        # the resource_provider ceilometer poller.
        self.send_metric(_type, host, metric, value, time,
                         by_name=True, create_resource=False)

    def send_capacity_by_site(self, site, scope, metric, value, time):
        metric = "capacity.%s.%s" % (scope, metric)
        self.send_metric('site', site, metric, value, time,
                         by_name=True)

    def send_usage_by_site(self, site, scope, metric, value, time):
        metric = "usage.%s.%s" % (scope, metric)
        self.send_metric('site', site, metric, value, time,
                         by_name=True)

    def send_availability_by_site(self, site, scope, metric, value, time):
        metric = "availability.%s.%s" % (scope, metric)
        self.send_metric('site', site, metric, value, time,
                         by_name=True)

    def send_by_idp(self, idp, metric, value, time):
        return self.send_metric('idp', idp, metric, value, time)

    def send_global(self, metric, value, time):
        return self.send_metric('generic', 'global-stats', metric, value, time)
