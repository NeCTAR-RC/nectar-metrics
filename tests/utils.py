class TestSender():
    def __init__(self):
        self.by_az = []
        self.by_az_by_domain = []
        self.by_tenant = []
        self.by_az_by_tenant = []
        self.by_az_by_home = []
        self.by_host_by_home = []
        self.by_idp = []
        self.by_global = []
        self.capacity_by_site = []
        self.usage_by_site = []
        self.availability_by_site = []
        self.metrics = []
        self.flushes = 0

    def send_by_az_by_domain(self, *args):
        self.by_az_by_domain.append(args)

    def send_by_az(self, *args):
        self.by_az.append(args)

    def send_by_tenant(self, *args):
        self.by_tenant.append(args)

    def send_by_az_by_tenant(self, *args):
        self.by_az_by_tenant.append(args)

    def send_by_az_by_home(self, *args):
        self.by_az_by_home.append(args)

    def send_by_host_by_home(self, *args):
        self.by_host_by_home.append(args)

    def send_by_idp(self, *args):
        self.by_idp.append(args)

    def send_capacity_by_site(self, *args):
        self.capacity_by_site.append(args)

    def send_usage_by_site(self, *args):
        self.usage_by_site.append(args)

    def send_availability_by_site(self, *args):
        self.availability_by_site.append(args)

    def send_global(self, *args):
        self.by_global.append(args)

    def send_metric(self, *args):
        self.metrics.append(args)

    def flush(self):
        self.flushes += 1
