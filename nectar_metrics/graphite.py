#!/usr/bin/env python
import socket
import logging
import pickle
import struct


if __name__ == '__main__':
    LOG_NAME = __file__
else:
    LOG_NAME = __name__

logger = logging.getLogger(LOG_NAME)


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

    def send_graphite_nectar(self, metric, value, time):
        raise NotImplemented()

    def send_graphite_cell(self, cell, metric, value, time):
        raise NotImplemented()

    def send_graphite_domain(self, cell, domain, metric, value, time):
        raise NotImplemented()


class DummySender(BaseSender):

    def send_metric(self, metric, value, now):
        message = self.format_metric(metric, value, now)
        print message
        return message

    def send_graphite_nectar(self, metric, value, time):
        return self.send_metric("cells.%s" % metric,  value, time)

    def send_graphite_cell(self, cell, metric, value, time):
        return self.send_metric("cells.%s.%s" % (cell, metric), value, time)

    def send_graphite_domain(self, cell, domain, metric, value, time):
        return self.send_metric("cells.%s.domains.%s.%s" % (cell, domain, metric),
                                value, time)

    def send_graphite_tenant(self, cell, tenants, flavor, metric, value, time):
        return self.send_metric("cells.%s.tenants.%s.%s.%s" % (cell, tenants, flavor, metric),
                                value, time)


class SocketMetricSender(BaseSender):
    sock = None
    reconnect_at = 100

    def __init__(self, host, port):
        super(SocketMetricSender, self).__init__()
        self.host = host
        self.port = port
        self.connect()
        self.count = 1

    def connect(self):
        if self.sock:
            self.sock.close()
            self.log.info("Reconnecting")
        else:
            self.log.info("Connecting")
        self.sock = socket.socket()
        self.sock.connect((self.host, self.port))
        self.log.info("Connected")

    def reconnect(self):
        self.count = 1
        self.connect()

    def send_metric(self, metric, value, now):
        message = self.format_metric(metric, value, now)
        if self.count > self.reconnect_at:
            self.reconnect()
        self.sock.sendall(message)
        return message

    def send_graphite_nectar(self, metric, value, time):
        return self.send_metric("cells.%s" % metric,  value, time)

    def send_graphite_cell(self, cell, metric, value, time):
        return self.send_metric("cells.%s.%s" % (cell, metric), value, time)

    def send_graphite_domain(self, cell, domain, metric, value, time):
        return self.send_metric("cells.%s.domains.%s.%s" % (cell, domain, metric),
                                value, time)

    def send_graphite_tenant(self, cell, tenants, flavor, metric, value, time):
        return self.send_metric("cells.%s.tenants.%s.%s.%s" % (cell, tenants, flavor, metric),
                                value, time)


class PickleSocketMetricSender(SocketMetricSender):
    sock = None
    reconnect_at = 500

    def __init__(self, host, port):
        super(SocketMetricSender, self).__init__()
        self.host = host
        self.port = port
        self.connect()
        self.count = 1
        self.buffered_metrics = []

    def send_metric(self, metric, value, now):
        self.count = self.count + 1
        self.buffered_metrics.append((metric, (now, float(value))))
        if self.count > self.reconnect_at:
            self.flush()
            self.reconnect()
        return (metric, (now, float(value)))

    def flush(self):
        payload = pickle.dumps(self.buffered_metrics)
        header = struct.pack("!L", len(payload))
        message = header + payload
        self.sock.sendall(message)
        print len(self.buffered_metrics)
        self.buffered_metrics = []
