from nectar_metrics.senders import base, gnocchi, graphite


class GnocchiGraphiteSender(base.BaseSender):

    def __init__(self, host, port):
        super(GnocchiGraphiteSender, self).__init__()
        self.gnocchi = gnocchi.GnocchiSender()
        self.graphite = graphite.PickleSocketMetricSender(host, port)

    def send_by_az(self, az, metric, value, time):
        self.gnocchi.send_by_az(az, metric, value, time)
        self.graphite.send_by_az(az, metric, value, time)

    def send_by_az_by_domain(self, az, domain, metric, value, time):
        self.gnocchi.send_by_az_by_domain(az, domain, metric, value, time)
        self.graphite.send_by_az_by_domain(az, domain, metric, value, time)

    def send_by_tenant(self, tenant, metric, value, time):
        self.gnocchi.send_by_tenant(tenant, metric, value, time)
        self.graphite.send_by_tenant(tenant, metric, value, time)

    def send_by_az_by_tenant(self, az, tenant, metric, value, time):
        self.gnocchi.send_by_az_by_tenant(az, tenant, metric, value, time)
        self.graphite.send_by_az_by_tenant(az, tenant, metric, value, time)

    def send_by_idp(self, idp, metric, value, time):
        self.gnocchi.send_by_idp(idp, metric, value, time)
        self.graphite.send_by_idp(idp, metric, value, time)

    def send_by_cell(self, cell, metric, value, time):
        self.gnocchi.send_by_cell(cell, metric, value, time)

    def send_global(self, resource, metric, value, time):
        self.gnocchi.send_global(resource, metric, value, time)