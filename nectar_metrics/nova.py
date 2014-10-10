import os
from os import path
import time
import logging
import pickle
from collections import defaultdict

from novaclient.v1_1 import client as nova_client

from nectar_metrics import log
from nectar_metrics import config
from nectar_metrics.config import CONFIG
from nectar_metrics.graphite import (PickleSocketMetricSender,
                                     DummySender, SocketMetricSender)
from nectar_metrics.keystone import client as keystone_client

logger = logging.getLogger(__name__)
flavor = {}


def client(username=None, password=None, tenant=None, url=None):
    url = os.environ.get('OS_AUTH_URL', url)
    username = os.environ.get('OS_USERNAME', username)
    password = os.environ.get('OS_PASSWORD', password)
    tenant = os.environ.get('OS_TENANT_NAME', tenant)
    conn = nova_client.Client(username=username, api_key=password,
                              project_id=tenant, auth_url=url)
    return conn


def all_servers(client, limit=None):
    servers = []
    marker = None
    opts = {"all_tenants": True}
    if limit:
        opts['limit'] = limit

    while True:
        if marker:
            opts["marker"] = marker
        result = client.servers.list(search_opts=opts)

        if not result:
            break

        servers.extend(result)

        # Quit if we have got enough servers.
        if limit and len(servers) >= int(limit):
            break

        marker = servers[-1].id
    return servers


def all_flavors(client, servers):
    flavor_ids = set()
    for server in servers:
        flavor_ids.add(server['flavor']['id'])
    flavors = {}
    for flavor_id in flavor_ids:
        flavor = client.flavors.get(flavor_id)
        flavors[flavor.id] = {'disk': flavor.disk,
                              'ram': flavor.ram,
                              'vcpus': flavor.vcpus}
    return flavors


def server_metrics(servers, flavors):
    """Generate a dict containing the total counts of vcpus, ram, disk as
    well as the total number of servers."""
    metrics = defaultdict(int)
    metrics['total_instances'] = len(servers)
    for server in servers:
        metrics['used_vcpus'] += flavors[server['flavor']['id']]['vcpus']
        metrics['used_memory'] += flavors[server['flavor']['id']]['ram']
        metrics['used_disk'] += flavors[server['flavor']['id']]['disk']
    return metrics


def server_metrics1(servers, flavors):
    metrics = defaultdict(lambda: defaultdict(int))
    for server in servers:
        name = server['flavor']['id']
        metrics[name]['total_instances'] += 1
        metrics[name]['used_vcpus'] += flavors[server['flavor']['id']]['vcpus']
        metrics[name]['used_memory'] += flavors[server['flavor']['id']]['ram']
        metrics[name]['used_disk'] += flavors[server['flavor']['id']]['disk']
    return metrics


def by_az(servers_by_az, flavors, now, sender):
    """Group the data by az."""
    for zone, servers in servers_by_az.items():
        for metric, value in server_metrics(servers, flavors).items():
            sender.send_by_az(zone, metric, value, now)


def by_az_by_domain(servers, flavors, users, now, sender):
    servers_by_az_by_domain = defaultdict(lambda: defaultdict(list))
    for server in servers:
        az = server.get('OS-EXT-AZ:availability_zone')

        if server['user_id'] in users and users[server['user_id']] is None:
            logger.info("skipping unknown user %s" % server['user_id'])
            continue

        if server['user_id'] not in users:
            logger.error(
                "user %s doesn't exist but is currently owner of server %s"
                % (server['user_id'], server['id']))
            continue

        domain = users[server['user_id']]
        servers_by_az_by_domain[az][domain].append(server)

    for zone, items in servers_by_az_by_domain.items():
        for domain, servers in items.items():
            for metric, value in server_metrics(servers, flavors).items():
                if metric not in ['used_vcpus']:
                    continue
                sender.send_by_az_by_domain(zone, domain, metric, value, now)


def by_tenant(servers, flavors, now, sender):
    servers_by_tenant = defaultdict(list)
    for server in servers:
        servers_by_tenant[server['tenant_id']].append(server)
    for tenant, servers in servers_by_tenant.items():
        for metric, value in server_metrics(servers, flavors).items():
            if metric not in ['used_vcpus', 'total_instances',
                              'used_memory']:
                continue
            sender.send_by_tenant(tenant, metric, value, now)


def by_az_by_tenant(servers, flavors, now, sender):
    servers_by_cell_by_tenant = defaultdict(lambda: defaultdict(list))
    for server in servers:
        cell = server.get('OS-EXT-AZ:availability_zone')
        servers_by_cell_by_tenant[cell][server['tenant_id']].append(server)
    for zone, items in servers_by_cell_by_tenant.items():
        for tenant, servers in items.items():
            for metric, value in server_metrics(servers, flavors).items():
                if metric not in ['used_vcpus', 'total_instances',
                                  'used_memory']:
                    continue
                sender.send_by_az_by_tenant(zone, tenant, metric, value, now)


def change_over_time(servers_by_az, now, sender):
    current_servers = dict([(az, set([server['id'] for server in servers]))
                            for az, servers in servers_by_az.items()])
    working_dir = CONFIG.get('metrics', 'working_dir')
    previous_servers_file = path.join(working_dir, "previous_servers.pickle")

    if not os.path.exists(previous_servers_file):
        pickle.dump(current_servers, open(previous_servers_file, 'w'))

    previous_servers = pickle.load(open(previous_servers_file))
    # Override the pickle each time no matter what.  this will
    # prevent massive launch rates if the script fails fro a
    # while.
    pickle.dump(current_servers, open(previous_servers_file, 'w'))
    for zone, servers in current_servers.items():
        if zone not in previous_servers:
            # If the zone isn't in the list of previous servers
            # then skip it.
            continue
        previous_zone_servers = previous_servers.get(zone)
        intersection = servers.intersection(previous_zone_servers)

        instances_deleted = len(previous_zone_servers) - len(intersection)
        sender.send_by_az(zone, 'instances_deleted', instances_deleted, now)

        instances_created = len(servers) - len(intersection)
        sender.send_by_az(zone, 'instances_created', instances_created, now)


def do_report(sender, limit):
    username = CONFIG.get('openstack', 'user')
    key = CONFIG.get('openstack', 'passwd')
    tenant_name = CONFIG.get('openstack', 'name')
    url = CONFIG.get('openstack', 'url')
    nclient = client(username, key, tenant_name, url)
    kclient = keystone_client(username, key, tenant_name, url)
    users = {}
    for user in kclient.users.list():
        if not getattr(user, 'email', None):
            users[user.id] = None
            continue
        email = user.email.split('@')[-1]
        if email.endswith('.edu.au'):
            email = '_'.join(email.split('.')[-3:])
        else:
            email = email.replace('.', '_')
        users[user.id] = email

    servers = [server.to_dict() for server in all_servers(nclient, limit)]
    flavors = all_flavors(nclient, servers)
    servers_by_az = defaultdict(list)

    for server in servers:
        az = server.get('OS-EXT-AZ:availability_zone')
        servers_by_az[az].append(server)

    now = int(time.time())
    by_tenant(servers, flavors, now, sender)
    by_az(servers_by_az, flavors, now, sender)
    by_az_by_tenant(servers, flavors, now, sender)
    by_az_by_domain(servers, flavors, users, now, sender)
    change_over_time(servers_by_az, now, sender)
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
    parser.add_argument('--config', default=config.CONFIG_FILE, type=str,
                        help='Config file path.')
    parser.add_argument(
        '--limit', default=None,
        help='Limit the response to some servers only.')
    args = parser.parse_args()
    config.read(args.config)

    log_level = 'WARNING'
    if args.verbose == 1:
        log_level = 'INFO'
    elif args.verbose >= 2:
        log_level = 'DEBUG'
    log.setup('nova.log', 'INFO', log_level)

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
