from nectar_metrics.senders import base, gnocchi, graphite


class GnocchiGraphiteSender(base.BaseSender):

    def __init__(self, host, port):
        super(GnocchiGraphiteSender, self).__init__()
        self.gnocchi = gnocchi.GnocchiSender()
        self.graphite = graphite.PickleSocketMetricSender(host, port)

    def send_by_az(self, az, metric, value, time):
        # self.gnocchi.send_by_az(az, metric, value, time)
        self.graphite.send_by_az(az, metric, value, time)

    def send_by_az_by_domain(self, az, domain, metric, value, time):
        # self.gnocchi.send_by_az_by_domain(az, domain, metric, value, time)
        self.graphite.send_by_az_by_domain(az, domain, metric, value, time)

    def send_by_tenant(self, tenant, metric, value, time):
        # self.gnocchi.send_by_tenant(tenant, metric, value, time)
        self.graphite.send_by_tenant(tenant, metric, value, time)

    def send_by_az_by_tenant(self, az, tenant, metric, value, time):
        # self.gnocchi.send_by_az_by_tenant(az, tenant, metric, value, time)
        self.graphite.send_by_az_by_tenant(az, tenant, metric, value, time)

    def send_by_az_by_home(self, az, home, metric, value, time):
        # self.gnocchi.send_by_az_by_home(az, home, metric, value, time)
        self.graphite.send_by_az_by_home(az, home, metric, value, time)

    def send_by_host_by_home(self, host, home, metric, value, time):
        self.gnocchi.send_by_host_by_home(host, home, metric, value, time)

    def send_capacity_by_site(self, site, scope, metric, value, time):
        self.gnocchi.send_capacity_by_site(site, scope, metric, value, time)

    def send_usage_by_site(self, site, scope, metric, value, time):
        self.gnocchi.send_usage_by_site(site, scope, metric, value, time)

    def send_availability_by_site(self, site, scope, metric, value, time):
        self.gnocchi.send_availability_by_site(site, scope, metric, value,
                                               time)

    def send_by_idp(self, idp, metric, value, time):
        self.graphite.send_by_idp(idp, metric, value, time)

    def send_global(self, resource, metric, value, time):
        self.graphite.send_global(resource, metric, value, time)
