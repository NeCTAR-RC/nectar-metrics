import logging
import sys


logger = logging.getLogger(__name__)


class BaseSender(object):
    message_fmt = '%s %0.2f %d\n'

    def __init__(self):
        self.log = logging.getLogger(self.__class__.__name__)

    def flush(self):
        pass

    def format_metric(self, metric, value, now):
        return self.message_fmt % (metric, value, now)

    def send_metric(self, metric, value, now):
        raise NotImplemented()

    def send_by_az(self, az, metric, value, time):
        return self.send_metric("az.%s.%s" % (az, metric), value, time)

    def send_by_az_by_domain(self, az, domain, metric, value, time):
        return self.send_metric("az.%s.domain.%s.%s"
                                % (az, domain, metric),
                                value, time)

    def send_by_tenant(self, tenant, metric, value, time):
        return self.send_metric("tenant.%s.%s"
                                % (tenant, metric),
                                value, time)

    def send_by_az_by_tenant(self, az, tenant, metric, value, time):
        return self.send_metric("az.%s.tenant.%s.%s"
                                % (az, tenant, metric),
                                value, time)

    def send_by_az_by_home(self, az, home, metric, value, time):
        return self.send_metric("az.%s.allocation_home.%s.%s"
                                % (az, home, metric),
                                value, time)

    def send_by_idp(self, idp, metric, value, time):
        return self.send_metric("users.%s.%s" % (idp, metric), value, time)

    def send_by_cell(self, cell, metric, value, time):
        return self.send_metric("cell.%s.%s" % (cell, metric), value, time)

    def send_global(self, resource, metric, value, time):
        return self.send_metric("%s.%s" % (resource, metric), value, time)


class DummySender(BaseSender):

    def send_metric(self, metric, value, now):
        message = self.format_metric(metric, value, now)
        sys.stdout.write(message)
        return message
