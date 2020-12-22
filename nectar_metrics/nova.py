from collections import defaultdict
import datetime
import logging
import os
from os import path
import pickle
import shutil
import sys
import time

from nectarallocationclient import client as allocation_client
from nectarallocationclient import exceptions
from nectarallocationclient import states
from novaclient import client as nova_client

from nectar_metrics import cli
from nectar_metrics import config
from nectar_metrics import gnocchi
from nectar_metrics.keystone import client as keystone_client
from nectar_metrics.keystone import get_auth_session


CONF = config.CONFIG
LOG = logging.getLogger(__name__)
flavor = {}
NOVA_VERSION = '2.60'


def client():
    auth_session = get_auth_session()
    return nova_client.Client(NOVA_VERSION,
                              session=auth_session)


def all_servers(client, limit=None):
    servers = []
    marker = None
    opts = {"all_tenants": True}
    if limit:
        opts['limit'] = limit

    while True:
        if marker:
            opts["marker"] = marker

        try:
            result = client.servers.list(search_opts=opts)
        except Exception as exception:
            LOG.exception(exception)
            sys.exit(1)

        if not result:
            break

        servers.extend(result)

        # Quit if we have got enough servers.
        if limit and len(servers) >= int(limit):
            break

        marker = servers[-1].id
    return servers


def server_metrics(servers):
    """Generate a dict containing the total counts of vcpus, ram, disk as
    well as the total number of servers."""
    metrics = defaultdict(int)
    metrics['total_instances'] = len(servers)
    for server in servers:
        if 'flavor' in server:
            metrics['used_vcpus'] += server['flavor']['vcpus']
            metrics['used_memory'] += server['flavor']['ram']
            metrics['used_disk'] += server['flavor']['disk']
    return metrics


def by_az(servers_by_az, now, sender):
    """Group the data by az."""
    for zone, servers in servers_by_az.items():
        for metric, value in server_metrics(servers).items():
            sender.send_by_az(zone, metric, value, now)


def by_az_by_domain(servers, users, now, sender):
    servers_by_az_by_domain = defaultdict(lambda: defaultdict(list))
    for server in servers:
        az = server.get('OS-EXT-AZ:availability_zone')

        if server['user_id'] in users and users[server['user_id']] is None:
            LOG.info("skipping unknown user %s" % server['user_id'])
            continue

        if server['user_id'] not in users:
            LOG.error(
                "user %s doesn't exist but is currently owner of server %s"
                % (server['user_id'], server['id']))
            continue

        domain = users[server['user_id']]
        servers_by_az_by_domain[az][domain].append(server)

    for zone, items in servers_by_az_by_domain.items():
        for domain, servers in items.items():
            for metric, value in server_metrics(servers).items():
                if metric not in ['used_vcpus']:
                    continue
                sender.send_by_az_by_domain(zone, domain, metric, value, now)


def by_tenant(servers, now, sender):
    servers_by_tenant = defaultdict(list)
    for server in servers:
        servers_by_tenant[server['tenant_id']].append(server)
    for tenant, servers in servers_by_tenant.items():
        for metric, value in server_metrics(servers).items():
            if metric not in ['used_vcpus', 'total_instances',
                              'used_memory']:
                continue
            sender.send_by_tenant(tenant, metric, value, now)


def by_az_by_tenant(servers, now, sender):
    servers_by_az_by_tenant = defaultdict(lambda: defaultdict(list))
    for server in servers:
        az = server.get('OS-EXT-AZ:availability_zone')
        servers_by_az_by_tenant[az][server['tenant_id']].append(server)
    for zone, items in servers_by_az_by_tenant.items():
        for tenant, servers in items.items():
            for metric, value in server_metrics(servers).items():
                if metric not in ['used_vcpus', 'total_instances',
                                  'used_memory']:
                    continue
                sender.send_by_az_by_tenant(zone, tenant, metric, value, now)


def by_az_by_home(servers, allocations, project_cache, now, sender):
    servers_by_az_by_home = defaultdict(lambda: defaultdict(list))
    for server in servers:
        az = server.get('OS-EXT-AZ:availability_zone')

        home = 'none'  # default if not an allocation or PT
        if server['tenant_id'] in allocations:
            home = allocations[server['tenant_id']].allocation_home
        elif project_cache[server['tenant_id']].name.startswith('pt-'):
            home = 'PT'

        servers_by_az_by_home[az][home].append(server)

    for zone, items in servers_by_az_by_home.items():
        for home, servers in items.items():
            for metric, value in server_metrics(servers).items():
                if metric not in ['used_vcpus']:
                    continue
                sender.send_by_az_by_home(zone, home, metric, value, now)


def by_host_by_home(servers, allocations, project_cache, now, sender):
    servers_by_host_by_home = defaultdict(lambda: defaultdict(list))
    for server in servers:
        host = server.get('OS-EXT-SRV-ATTR:hypervisor_hostname')

        if host is None:
            # This usually means the instance failed to schedule and is in
            # ERROR state, but it could also mean the instance is shelved.
            # For now, we don't count any resource usage in these cases.
            LOG.debug("Server %s is not on any host, skipping.",
                      server["id"])
            continue

        home = 'unknown'  # default if not an allocation or PT
        allocation = allocations.get(server['tenant_id'])
        if allocation:
            home = '{}.{}'.format(
                'national' if allocation.national else 'local',
                allocation.associated_site
            )
        else:
            project = project_cache[server['tenant_id']]
            if project.name.startswith('pt-'):
                home = 'PT'
            elif 'preemptible' in project.tags:
                home = 'preemptible'
            elif getattr(project, 'expiry_status', '') == 'admin':
                home = 'admin'

        servers_by_host_by_home[host][home].append(server)

    for host, items in servers_by_host_by_home.items():
        for home, servers in items.items():
            for metric, value in server_metrics(servers).items():
                if metric.startswith('used_'):
                    sender.send_by_host_by_home(host, home, metric, value, now)


def change_over_time(servers_by_az, now, sender):
    current_servers = dict([(az, set([server['id'] for server in servers]))
                            for az, servers in servers_by_az.items()])
    working_dir = CONF.get('metrics', 'working_dir')
    previous_servers_file = path.join(working_dir, "previous_servers.pickle")

    if not os.path.exists(previous_servers_file):
        with open(previous_servers_file, 'wb') as pickle_file:
            pickle.dump(current_servers, pickle_file)

    try:
        with open(previous_servers_file, 'rb') as pickle_file:
            previous_servers = pickle.load(pickle_file)
    except EOFError:
        LOG.warning("Invalid data in pickle %s" % previous_servers_file)
        previous_servers = current_servers

    # Override the pickle each time no matter what.  this will
    # prevent massive launch rates if the script fails fro a
    # while.
    with open(previous_servers_file + '.tmp', 'wb') as pickle_file:
        pickle.dump(current_servers, pickle_file)
    shutil.move(previous_servers_file + '.tmp', previous_servers_file)
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


def get_active_allocations():
    auth_session = get_auth_session()
    aclient = allocation_client.Client('1', session=auth_session)

    active_allocations = {}

    # All approved allocations
    allocations = aclient.allocations.list(parent_request__isnull=True)

    for allocation in allocations:
        if (allocation.status == states.DELETED
                or allocation.status == states.SUBMITTED):
            continue
        elif allocation.status != states.APPROVED:
            try:
                allocation = aclient.allocations.get_last_approved(
                    parent_request=allocation.id)
            except exceptions.AllocationDoesNotExist:
                continue

        if not allocation.project_id:
            continue

        active_allocations[allocation.project_id] = allocation

    return active_allocations


def get_capacities_by_site():
    client = gnocchi.get_client()
    caps = {}
    for resource in ['vcpu', 'memory', 'disk']:
        fill_capacities_for_resource(client, caps, resource)
    LOG.info("Site capacities: %s", caps)
    return caps


def get_usages_by_site():
    client = gnocchi.get_client()
    usages = {}
    for scope in ['national', 'local', 'PT', 'other', 'preemptible']:
        for resource in ['vcpu', 'memory', 'disk']:
            fill_usages_for_resource(client, usages, scope, resource)
    LOG.info("Site usages: %s", usages)
    return usages


def get_availability_by_site(capacities, usages):
    """Calculate national and local availability by site.

    This function iterates over the aggregated capacity and usage
    metrics for each resource (vcpu, memory, disk) and calculates
    a per-site "availability" metric:

       local availability = local capacity - local usage

       national availability = national capacity...
                                minus national usage
                                minus any overflow of local usage
                                    (where usage > capacity)
                                minus PT usage
                                minus other usage (anything not accounted for)
    """
    availability = {}
    for site, cap in capacities.items():
        usage = usages.get(site, {})
        available = availability.get(site, defaultdict(dict))
        for resource in ['vcpu', 'memory', 'disk']:
            local_cap = cap.get('local', {}).get(resource, .0)
            local_usage = usage.get('local', {}).get(resource, .0)
            local_availability = local_cap - local_usage
            available['local'][resource] = local_availability
            LOG.debug(
                'Local availability %s %s: %s',
                site, resource, local_availability)

            if 'national' in cap and resource in cap['national']:
                national_availability = (
                    cap['national'][resource]
                    - usage.get('national', {}).get(resource, .0)
                    - usage.get('PT', {}).get(resource, .0)
                    - usage.get('other', {}).get(resource, .0)
                    + min(0, local_availability)
                )
                available['national'][resource] = national_availability
                LOG.debug(
                    'National availability %s %s: %s',
                    site, resource, national_availability)
        availability[site] = available
    return availability


def fill_capacities_for_resource(client, caps, resource):
    two_hours_ago = datetime.datetime.utcnow() - datetime.timedelta(hours=2)
    query = '(aggregate sum (metric resource_provider.capacity.{} mean))'
    query = query.format(resource)

    try:
        capacities = client.aggregates.fetch(
            operations=query,
            groupby=['site', 'scope'],
            resource_type='resource_provider',
            granularity=3600,
            start=two_hours_ago,
            fill=0.0,
            search={}
        )
    except gnocchi.exceptions.ClientException as e:
        LOG.warning("Gnocchi query failed: %s, query was: %s",
                    str(e), query)
        return

    errors = False
    for cap in capacities:
        group = cap['group']
        scope = group['scope']
        site = group['site']

        if site is None:
            site = 'unknown'
        if site not in caps:
            caps[site] = {}
        if scope is None:
            scope = 'unknown'
        if scope not in caps[site]:
            caps[site][scope] = {}
        # Get the most recent metric value.
        measures = cap['measures']['measures']['aggregated']
        try:
            caps[site][scope][resource] = measures[-1][2]
        except IndexError:
            errors = True

    if errors:
        LOG.warning("One or more resource providers "
                    "had no capacity metrics.")


usage_metrics = {
    'other': [
        'resource_provider.usage.admin.{resource}',
        'resource_provider.usage.unknown.{resource}',
    ],
    'preemptible': [
        'resource_provider.usage.preemptible.{resource}',
    ],
    'PT': [
        'resource_provider.usage.PT.{resource}',
    ],
    'local': [
        'resource_provider.usage.local.*.{resource}',
    ],
    'national': [
        'resource_provider.usage.national.*.{resource}',
    ],
}


def fill_usages_for_resource(client, usages, scope, resource):
    two_hours_ago = datetime.datetime.utcnow() - datetime.timedelta(hours=2)
    metrics = usage_metrics[scope]
    metrics_query = " ".join(["({metric} mean)".format(metric=metric)
                             for metric in metrics])
    query = "(aggregate sum (metric {metrics} ))"
    query = query.format(metrics=metrics_query)
    query = query.format(resource=resource)

    try:
        gnocchi_usages = client.aggregates.fetch(
            operations=query,
            groupby=['site'],
            resource_type='resource_provider',
            granularity=3600,
            start=two_hours_ago,
            fill=0.0,
            search={}
        )
    except gnocchi.exceptions.ClientException as e:
        LOG.warning("Gnocchi query failed: %s, query was: %s",
                    str(e), query)
        return

    for usage in gnocchi_usages:
        group = usage['group']
        site = group['site']

        if site is None:
            site = 'unknown'
        if site not in usages:
            usages[site] = {}
        if scope not in usages[site]:
            usages[site][scope] = {}
        # Get the most recent metric value.
        measures = usage['measures']['measures']
        if measures:
            aggregate = measures.get('aggregated')
            if aggregate:
                usages[site][scope][resource] = aggregate[-1][2]


def capacity_by_site(capacities, now, sender):
    for site, caps in capacities.items():
        for cap, resources in caps.items():
            for res, value in resources.items():
                sender.send_capacity_by_site(site, cap, res, value, now)


def usage_by_site(usages, now, sender):
    for site, usages in usages.items():
        for scope, resources in usages.items():
            for resource, value in resources.items():
                sender.send_usage_by_site(site, scope, resource, value, now)


def availability_by_site(availability, now, sender):
    for site, availabilities in availability.items():
        for scope, resources in availabilities.items():
            for resource, value in resources.items():
                sender.send_availability_by_site(site, scope, resource,
                                                 value, now)


def do_report(sender, limit):
    nclient = client()
    kclient = keystone_client()
    users = {}
    project_cache = {}

    LOG.info("Getting site capacity information...")
    capacities = get_capacities_by_site()
    usages = get_usages_by_site()
    availability = get_availability_by_site(capacities, usages)

    LOG.info('Fetching user list...')
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

    LOG.info('Fethcing projects...')
    for project in kclient.projects.list():
        project_cache[project.id] = project

    LOG.info('Fetching server list...')
    servers = [server._info for server in all_servers(nclient, limit)
               if getattr(server, 'OS-EXT-AZ:availability_zone')]

    LOG.info('Fetching allocations list...')
    allocations = get_active_allocations()

    servers_by_az = defaultdict(list)
    for server in servers:
        az = server.get('OS-EXT-AZ:availability_zone')
        servers_by_az[az].append(server)

    now = int(time.time())
    by_tenant(servers, now, sender)
    now = int(time.time())
    by_az(servers_by_az, now, sender)
    now = int(time.time())
    by_az_by_tenant(servers, now, sender)
    now = int(time.time())
    by_az_by_domain(servers, users, now, sender)
    now = int(time.time())
    by_az_by_home(servers, allocations, project_cache, now, sender)
    now = int(time.time())
    by_host_by_home(servers, allocations, project_cache, now, sender)
    now = int(time.time())
    capacity_by_site(capacities, now, sender)
    now = int(time.time())
    usage_by_site(usages, now, sender)
    now = int(time.time())
    availability_by_site(availability, now, sender)
    now = int(time.time())
    change_over_time(servers_by_az, now, sender)
    sender.flush()


def main():
    parser = cli.Main('nova')
    parser.add_argument(
        '--limit', default=None,
        help='Limit the response to some servers only.')
    args = parser.parse_args()
    LOG.info("Running Report")
    do_report(parser.sender(), args.limit)
