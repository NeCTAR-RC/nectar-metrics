class TestSender():
    def __init__(self):
        self.graphite_domain = []
        self.graphite_az = []
        self.graphite_tenant = []

    def send_graphite_domain(self, *args):
        self.graphite_domain.append(args)

    def send_graphite_az(self, *args):
        self.graphite_az.append(args)

    def send_graphite_tenant(self, *args):
        self.graphite_tenant.append(args)
