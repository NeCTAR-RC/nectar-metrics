from nectar_metrics.senders import base
from nectar_metrics.senders import gnocchi
from nectar_metrics.senders import victoria


class GnocchiVictoriaSender(base.BaseSender):
    """Composite production sender: every metric goes to
    VictoriaMetrics, while site and host metrics (and globals) also
    flow to Gnocchi.
    """

    def __init__(self, victoria_url=None):
        super().__init__()
        self.gnocchi = gnocchi.GnocchiSender()
        self.victoria = victoria.VictoriaMetricsSender(victoria_url)

    def flush(self):
        self.victoria.flush()

    def send_by_az(self, az, metric, value, time):
        self.victoria.send_by_az(az, metric, value, time)

    def send_by_az_by_domain(self, az, domain, metric, value, time):
        self.victoria.send_by_az_by_domain(az, domain, metric, value, time)

    def send_by_az_by_home(self, az, home, metric, value, time):
        self.victoria.send_by_az_by_home(az, home, metric, value, time)

    def send_by_tenant(self, tenant, metric, value, time):
        self.victoria.send_by_tenant(tenant, metric, value, time)

    def send_by_az_by_tenant(self, az, tenant, metric, value, time):
        self.victoria.send_by_az_by_tenant(az, tenant, metric, value, time)

    def send_by_idp(self, idp, metric, value, time):
        # Also duplicated in Gnocchi by the ceilometer account
        # pollster.
        self.victoria.send_by_idp(idp, metric, value, time)

    def send_by_host_by_home(self, host, home, metric, value, time):
        self.gnocchi.send_by_host_by_home(host, home, metric, value, time)
        self.victoria.send_by_host_by_home(host, home, metric, value, time)

    def send_capacity_by_site(self, site, scope, metric, value, time):
        self.gnocchi.send_capacity_by_site(site, scope, metric, value, time)
        self.victoria.send_capacity_by_site(site, scope, metric, value, time)

    def send_usage_by_site(self, site, scope, metric, value, time):
        self.gnocchi.send_usage_by_site(site, scope, metric, value, time)
        self.victoria.send_usage_by_site(site, scope, metric, value, time)

    def send_availability_by_site(self, site, scope, metric, value, time):
        self.gnocchi.send_availability_by_site(
            site, scope, metric, value, time
        )
        self.victoria.send_availability_by_site(
            site, scope, metric, value, time
        )

    def send_global(self, metric, value, time):
        self.gnocchi.send_global(metric, value, time)
        self.victoria.send_global(metric, value, time)
