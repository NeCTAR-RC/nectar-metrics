import time
import logging
from collections import defaultdict

from novaclient.v1_1 import client as nova_client

from nectar_metrics import config
from nectar_metrics.config import CONFIG
from nectar_metrics.graphite import (PickleSocketMetricSender,
                                     DummySender, SocketMetricSender)
from nectar_metrics.keystone import client as keystone_client

if __name__ == '__main__':
    LOG_NAME = __file__
else:
    LOG_NAME = __name__

logger = logging.getLogger(LOG_NAME)


flavor = {}


def client(username=None, password=None, tenant=None, url=None):
    url = os.environ.get('OS_AUTH_URL', url)
    username = os.environ.get('OS_USERNAME', username)
    password = os.environ.get('OS_PASSWORD', password)
    tenant = os.environ.get('OS_TENANT_NAME', tenant)
    conn = nova_client.Client(username=username, api_key=password,
                              project_id=tenant, auth_url=url)
    return conn


def all_servers(client):
    servers = []
    marker = None

    while True:
        opts = {"all_tenants": True}
        if marker:
            opts["marker"] = marker
        res = client.servers.list(search_opts=opts)
        if not res:
            break
        servers.extend(res)
        marker = servers[-1].id
    return servers


def all_flavors(client, servers):
    flavor_ids = set()
    for server in servers:
        flavor_ids.add(server.flavor['id'])
    flavors = {}
    for flavor_id in flavor_ids:
        flavor = client.flavors.get(flavor_id)
        flavors[flavor.id] = {'disk': flavor.disk,
                              'ram': flavor.ram,
                              'vcpus': flavor.vcpus}
    return flavors


def server_metrics(servers, flavors):
    metrics = defaultdict(int)
    metrics['total_instances'] = len(servers)
    for server in servers:
        metrics['used_vcpus'] += flavors[server.flavor['id']]['vcpus']
        metrics['used_memory'] += flavors[server.flavor['id']]['ram']
        metrics['used_disk'] += flavors[server.flavor['id']]['disk']
    return metrics


def server_metrics1(servers, flavors):
    metrics = defaultdict(lambda: defaultdict(int))
    for server in servers:
        name = server.flavor['id']
        metrics[name]['total_instances'] += 1
        metrics[name]['used_vcpus'] += flavors[server.flavor['id']]['vcpus']
        metrics[name]['used_memory'] += flavors[server.flavor['id']]['ram']
        metrics[name]['used_disk'] += flavors[server.flavor['id']]['disk']
    return metrics


def by_cell(servers_by_cell, flavors, now, sender):
    "Depreciated, since it's now done by the graphite aggregator."
    for zone, servers in servers_by_cell.items():
        for metric, value in server_metrics(servers, flavors).items():
            sender.send_graphite_cell(zone, metric, value, now)


def by_domain(servers, flavors, users, now, sender):
    servers_by_cell_by_domain = defaultdict(lambda: defaultdict(list))
    for server in servers:
        cell = getattr(server, 'OS-EXT-AZ:availability_zone')
        if server.user_id in users and users[server.user_id] is None:
            logger.info("skipping unknown user %s" % server.user_id)
            return True
        if server.user_id not in users:
            logger.error(
                "user %s doesn't exist but is currently owner of server %s"
                % (server.user_id, server.id))
            return True
        servers_by_cell_by_domain[cell][users[server.user_id]].append(server)
    for zone, items in servers_by_cell_by_domain.items():
        for domain, servers in items.items():
            for metric, value in server_metrics(servers, flavors).items():
                if metric not in ['used_vcpus']:
                    continue
                sender.send_graphite_domain(zone, domain, metric, value, now)


def by_tenant(servers, flavors, now, sender):
    servers_by_cell_by_tenant = defaultdict(lambda: defaultdict(list))
    for server in servers:
        cell = getattr(server, 'OS-EXT-AZ:availability_zone')
        servers_by_cell_by_tenant[cell][server.tenant_id].append(server)
    for zone, items in servers_by_cell_by_tenant.items():
        for tenant, servers in items.items():
            for flavor, metrics in server_metrics1(servers, flavors).items():
                for metric, value in metrics.items():
                    sender.send_graphite_tenant(zone, tenant, flavor,
                                                metric, value, now)


def main1(sender):
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

    servers = all_servers(nclient)
    flavors = all_flavors(nclient, servers)
    servers_by_cell = defaultdict(list)

    for server in servers:
        cell = getattr(server, 'OS-EXT-AZ:availability_zone')
        servers_by_cell[cell].append(server)

    now = int(time.time())
    by_domain(servers, flavors, users, now, sender)
    by_tenant(servers, flavors, now, sender)
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
    args = parser.parse_args()
    config.read(args.config)

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
