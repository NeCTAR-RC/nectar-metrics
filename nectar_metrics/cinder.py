import os
import time
import logging
from collections import defaultdict

from cinderclient.v1 import client as cinder_client

from nectar_metrics import log
from nectar_metrics import config
from nectar_metrics.config import CONFIG
from nectar_metrics.graphite import (PickleSocketMetricSender,
                                     DummySender, SocketMetricSender)


logger = logging.getLogger(__name__)


def client(username=None, password=None, tenant=None, url=None):
    url = os.environ.get('OS_AUTH_URL', url)
    username = os.environ.get('OS_USERNAME', username)
    password = os.environ.get('OS_PASSWORD', password)
    tenant = os.environ.get('OS_TENANT_NAME', tenant)
    assert url and username and password and tenant
    return cinder_client.Client(username=username,
                                api_key=password,
                                project_id=tenant,
                                auth_url=url)


def all_volumes(c_client, limit=None):
    volumes = []
    marker = None
    opts = {"all_tenants": True}
    if limit:
        opts['limit'] = limit

    while True:
        if marker:
            opts["marker"] = marker
        res = c_client.volumes.list(search_opts=opts)
        if not res:
            break
        volumes.extend(res)

        # Quit if we have got enough servers.
        if limit and len(volumes) >= int(limit):
            break

        marker = volumes[-1].id
    return volumes


def volume_metrics(volumes):
    metrics = defaultdict(int)
    for volume in volumes:
        metrics['total_volumes'] += 1
        metrics['used_volume_size'] += volume['size']
    return metrics


def by_tenant(volumes, now, sender):
    volumes_by_tenant = defaultdict(list)
    for volume in volumes:
        tenant_id = volume['os-vol-tenant-attr:tenant_id']
        volumes_by_tenant[tenant_id].append(volume)
    for tenant, volumes in volumes_by_tenant.items():
        for metric, value in volume_metrics(volumes).items():
            sender.send_by_tenant(tenant, metric, value, now)


def by_az_by_tenant(volumes, now, sender):
    volumes_by_az_by_tenant = defaultdict(lambda: defaultdict(list))
    for volume in volumes:
        az = volume['availability_zone']
        tenant_id = volume['os-vol-tenant-attr:tenant_id']
        volumes_by_az_by_tenant[az][tenant_id].append(volume)
    for zone, items in volumes_by_az_by_tenant.items():
        for tenant, volumes in items.items():
            for metric, value in volume_metrics(volumes).items():
                sender.send_by_az_by_tenant(zone, tenant, metric, value, now)


def do_report(sender, limit):
    username = CONFIG.get('openstack', 'user')
    key = CONFIG.get('openstack', 'passwd')
    tenant_name = CONFIG.get('openstack', 'name')
    url = CONFIG.get('openstack', 'url')
    c_client = client(username, key, tenant_name, url)
    volumes = [volume._info for volume in all_volumes(c_client, limit)]
    now = int(time.time())
    by_tenant(volumes, now, sender)
    by_az_by_tenant(volumes, now, sender)
    sender.flush()


def main():
    from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-v', '--verbose', action='count', default=0,
        help="Increase verbosity (specify multiple times for more)")
    parser.add_argument(
        '--protocol', choices=['debug', 'carbon', 'carbon_pickle'],
        required=True)
    parser.add_argument(
        '--carbon-host', help='Carbon Host.')
    parser.add_argument(
        '--carbon-port', default=2003, type=int,
        help='Carbon Port.')
    parser.add_argument(
        '--config', default=config.CONFIG_FILE, type=str,
        help='Config file path.')
    parser.add_argument(
        '--limit', default=None,
        help='Limit the response to some volumes only.')
    args = parser.parse_args()
    config.read(args.config)

    log_level = 'WARNING'
    if args.verbose == 1:
        log_level = 'INFO'
    elif args.verbose >= 2:
        log_level = 'DEBUG'
    log.setup('cinder.log', 'INFO', log_level)

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

    logger.info("Running Report")
    do_report(sender, args.limit)
