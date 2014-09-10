#!/usr/bin/env python
import os
import time
import socket
import logging
import pickle
import struct
from collections import defaultdict

from nectar_metrics import config
from nectar_metrics.config import CONFIG
from nectar_metrics.nova import client as nova_client
from nectar_metrics.keystone import client as keystone_client
from cinderclient.v1 import client as cinder_client

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

    def send_graphite_tenant1(self, cell, tenants, metric, value, time):
        return self.send_metric("cells.%s.tenants.%s.%s" % (cell, tenants, metric),
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


flavor = {}


def all_volumes(c_client):
    volumes = []
    marker = None

    while True:
        opts = {"all_tenants": True}
        if marker:
            opts["marker"] = marker
        res = c_client.volumes.list(search_opts=opts)
        if not res:
            break
        volumes.extend(res)
        marker = volumes[-1].id
    return volumes


def client(username=None, password=None,
                           tenant=None, url=None):
    url = os.environ.get('OS_AUTH_URL', url)
    username = os.environ.get('OS_USERNAME', username)
    password = os.environ.get('OS_PASSWORD', password)
    tenant = os.environ.get('OS_TENANT_NAME', tenant)
    assert url and username and password and tenant
    return cinder_client.Client(username=username,
                                api_key=password,
                                project_id=tenant,
                                auth_url=url)


def volume_metrics(volumes):
    metrics = defaultdict(int)
    for volume in volumes:
        metrics['total_volumes'] += 1
        metrics['used_volume_size'] += volume.size
    return metrics


def by_tenant(volumes, now, sender):
    volumes_by_cell_by_tenant = defaultdict(lambda: defaultdict(list))
    for volume in volumes:
        cell = volume.availability_zone
        tenant_id = getattr(volume, 'os-vol-tenant-attr:tenant_id')
        volumes_by_cell_by_tenant[cell][tenant_id].append(volume)
    for zone, items in volumes_by_cell_by_tenant.items():
        for tenant, volumes in items.items():
            for metric, value in volume_metrics(volumes).items():
                sender.send_graphite_tenant1(zone, tenant, metric, value, now)


def main1(sender):
    username = CONFIG.get('production', 'user')
    key = CONFIG.get('production', 'passwd')
    tenant_name = CONFIG.get('production', 'name')
    url = CONFIG.get('production', 'url')
    c_client = client(username, key, tenant_name, url)
    volumes = all_volumes(c_client)
    now = int(time.time())
    by_tenant(volumes, now, sender)
    sender.flush()


def main():
    from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument('-v', '--verbose', action='count', default=0,
                        help="Increase verbosity (specify multiple times for more)")
    parser.add_argument('--protocol', choices=['debug', 'carbon', 'carbon_pickle'],
                        required=True)
    parser.add_argument('--carbon-host', help='Carbon Host.')
    parser.add_argument('--carbon-port', default=2003, type=int,
                        help='Carbon Port.')
    args = parser.parse_args()

    log_level = logging.WARNING
    if args.verbose == 1:
        log_level = logging.INFO
    elif args.verbose >= 2:
        log_level = logging.DEBUG

    logging.basicConfig(
        level=log_level,
        format='%(asctime)s %(name)s %(levelname)s %(message)s')

    if args.protocol == 'carbon':
        if not args.carbon_host:
            parser.error('argument --carbon-host is required')
        if not args.carbon_port:
            parser.error('argument --carbon-port is required')
        sender = SocketMetricSender(args.carbon_host, args.carbon_port)
    elif args.protocol == 'carbon_pickle':
        if not args.carbon_host:
            parser.error('argument --carbon-host is required')
        if not args.carbon_port:
            parser.error('argument --carbon-port is required')
        sender = PickleSocketMetricSender(args.carbon_host, args.carbon_port)
    elif args.protocol == 'debug':
        sender = DummySender()

    main1(sender)
