class TestSender():
    def __init__(self):
        self.by_az = []
        self.by_az_by_domain = []
        self.by_tenant = []
        self.by_az_by_tenant = []
        self.by_global = []

    def send_by_az_by_domain(self, *args):
        self.by_az_by_domain.append(args)

    def send_by_az(self, *args):
        self.by_az.append(args)

    def send_by_tenant(self, *args):
        self.by_tenant.append(args)

    def send_by_az_by_tenant(self, *args):
        self.by_az_by_tenant.append(args)

    def send_global(self, *args):
        self.by_global.append(args)
