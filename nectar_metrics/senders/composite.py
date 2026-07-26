from nectar_metrics.senders import base
from nectar_metrics.senders import gnocchi
from nectar_metrics.senders import graphite
from nectar_metrics.senders import victoria


class GnocchiGraphiteSender(base.BaseSender):
    def __init__(self, host, port):
        super().__init__()
        self.gnocchi = gnocchi.GnocchiSender()
        self.graphite = graphite.PickleSocketMetricSender(host, port)

    def flush(self):
        self.graphite.flush()

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
        self.gnocchi.send_availability_by_site(
            site, scope, metric, value, time
        )

    def send_by_idp(self, idp, metric, value, time):
        self.graphite.send_by_idp(idp, metric, value, time)

    def send_global(self, metric, value, time):
        self.graphite.send_global(metric, value, time)
        self.gnocchi.send_global(metric, value, time)


class GnocchiGraphiteVictoriaSender(GnocchiGraphiteSender):
    """Transition composite for the Graphite to VictoriaMetrics
    migration: everything continues to flow to Graphite and Gnocchi
    exactly as with GnocchiGraphiteSender, while every metric is
    additionally written to VictoriaMetrics.
    """

    def __init__(self, host, port, victoria_url=None):
        super().__init__(host, port)
        self.victoria = victoria.VictoriaMetricsSender(victoria_url)

    def flush(self):
        super().flush()
        self.victoria.flush()

    def send_by_az(self, az, metric, value, time):
        super().send_by_az(az, metric, value, time)
        self.victoria.send_by_az(az, metric, value, time)

    def send_by_az_by_domain(self, az, domain, metric, value, time):
        super().send_by_az_by_domain(az, domain, metric, value, time)
        self.victoria.send_by_az_by_domain(az, domain, metric, value, time)

    def send_by_tenant(self, tenant, metric, value, time):
        super().send_by_tenant(tenant, metric, value, time)
        self.victoria.send_by_tenant(tenant, metric, value, time)

    def send_by_az_by_tenant(self, az, tenant, metric, value, time):
        super().send_by_az_by_tenant(az, tenant, metric, value, time)
        self.victoria.send_by_az_by_tenant(az, tenant, metric, value, time)

    def send_by_az_by_home(self, az, home, metric, value, time):
        super().send_by_az_by_home(az, home, metric, value, time)
        self.victoria.send_by_az_by_home(az, home, metric, value, time)

    def send_by_host_by_home(self, host, home, metric, value, time):
        super().send_by_host_by_home(host, home, metric, value, time)
        self.victoria.send_by_host_by_home(host, home, metric, value, time)

    def send_capacity_by_site(self, site, scope, metric, value, time):
        super().send_capacity_by_site(site, scope, metric, value, time)
        self.victoria.send_capacity_by_site(site, scope, metric, value, time)

    def send_usage_by_site(self, site, scope, metric, value, time):
        super().send_usage_by_site(site, scope, metric, value, time)
        self.victoria.send_usage_by_site(site, scope, metric, value, time)

    def send_availability_by_site(self, site, scope, metric, value, time):
        super().send_availability_by_site(site, scope, metric, value, time)
        self.victoria.send_availability_by_site(
            site, scope, metric, value, time
        )

    def send_by_idp(self, idp, metric, value, time):
        super().send_by_idp(idp, metric, value, time)
        self.victoria.send_by_idp(idp, metric, value, time)

    def send_global(self, metric, value, time):
        super().send_global(metric, value, time)
        self.victoria.send_global(metric, value, time)


class GnocchiVictoriaSender(base.BaseSender):
    """End-state composite once Graphite is decommissioned: every
    metric goes to VictoriaMetrics, while site and host metrics (and
    globals) keep flowing to Gnocchi as before.
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
