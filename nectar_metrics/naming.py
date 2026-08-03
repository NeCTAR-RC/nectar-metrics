"""Mapping from legacy dotted metric paths to the Prometheus-style
metric names and labels used by VictoriaMetrics.

Dotted paths are the interchange format between the collectors (the
BaseSender helpers compose dotted paths), the backfill tools and the
VictoriaMetrics sender. Keeping a single parser here guarantees that
backfilled history and live writes always map to identical series.

Every path family the collectors emit (nova, cinder, rcshibboleth)
is mapped. Paths outside the known families (retired trees, unknown
metric names) return None and are dropped by the VictoriaMetrics
sender.
"""

import re


AZ_METRICS = (
    'total_instances',
    'used_vcpus',
    'used_memory',
    'used_disk',
    'instances_created',
    'instances_deleted',
)

# nova sends total_instances/used_vcpus/used_memory, cinder sends
# total_volumes/used_volume_size, through the same per-tenant helpers.
TENANT_METRICS = (
    'total_instances',
    'used_vcpus',
    'used_memory',
    'total_volumes',
    'used_volume_size',
)

HOST_METRICS = (
    'used_vcpus',
    'used_memory',
    'used_disk',
)

_AZ_RE = re.compile(
    r'^az\.(?P<az>[^.]+)\.(?P<metric>{})$'.format('|'.join(AZ_METRICS))
)
_DOMAIN_RE = re.compile(
    r'^az\.(?P<az>[^.]+)\.domain\.(?P<domain>[^.]+)\.used_vcpus$'
)
_HOME_RE = re.compile(
    r'^az\.(?P<az>[^.]+)\.allocation_home\.(?P<home>[^.]+)\.used_vcpus$'
)
_TENANT_RE = re.compile(
    r'^tenant\.(?P<tenant>[^.]+)\.(?P<metric>{})$'.format(
        '|'.join(TENANT_METRICS)
    )
)
_AZ_TENANT_RE = re.compile(
    r'^az\.(?P<az>[^.]+)\.tenant\.(?P<tenant>[^.]+)\.(?P<metric>{})$'.format(
        '|'.join(TENANT_METRICS)
    )
)
# home is one or two segments: 'PT', 'preemptible', 'admin',
# 'unknown' or '{national|local}.{site}'.
_HOST_RE = re.compile(
    r'^hosts\.(?P<host>[^.]+)\.(?P<home>[^.]+(?:\.[^.]+)?)'
    r'\.(?P<metric>{})$'.format('|'.join(HOST_METRICS))
)
_SITE_RE = re.compile(
    r'^sites\.(?P<site>[^.]+)\.(?P<kind>capacity|usage|availability)'
    r'\.(?P<scope>[^.]+)\.(?P<resource>vcpu|memory|disk)$'
)
_IDP_RE = re.compile(r'^users\.(?P<idp>[^.]+)\.total$')
_ACTIVE_PROJECTS_RE = re.compile(r'^active\.projects\.(?P<service>[^.]+)$')


def from_dotted_path(path):
    """Map a legacy dotted metric path to a (name, labels) tuple.

    Returns None for paths outside the known families (retired
    trees, unknown metric names).
    """
    if path == 'users.total':
        return ('nectar_users_total', {})

    match = _AZ_RE.match(path)
    if match:
        return (
            'nectar_{}'.format(match.group('metric')),
            {'az': match.group('az')},
        )

    match = _DOMAIN_RE.match(path)
    if match:
        # nova.py flattens email domains with underscores
        # (e.g. unimelb_edu_au); restore the real dots. Safe because
        # hostnames cannot contain underscores.
        domain = match.group('domain').replace('_', '.')
        return (
            'nectar_domain_used_vcpus',
            {'az': match.group('az'), 'domain': domain},
        )

    match = _HOME_RE.match(path)
    if match:
        return (
            'nectar_allocation_home_used_vcpus',
            {'az': match.group('az'), 'home': match.group('home')},
        )

    # Tenant series exist both all-az (tenant.*) and per-az
    # (az.*.tenant.*); they get distinct metric names so each name
    # keeps a uniform label set and sum() never double counts.
    # Domain/home breakdowns above only exist per-az, so their names
    # predate and skip the az_ prefix.
    match = _TENANT_RE.match(path)
    if match:
        return (
            'nectar_tenant_{}'.format(match.group('metric')),
            {'tenant': match.group('tenant')},
        )

    match = _AZ_TENANT_RE.match(path)
    if match:
        return (
            'nectar_az_tenant_{}'.format(match.group('metric')),
            {
                'az': match.group('az'),
                'tenant': match.group('tenant'),
            },
        )

    match = _HOST_RE.match(path)
    if match:
        # The BaseSender flattens both dots and dashes in hostnames
        # to underscores, so the original hostname cannot be
        # restored; the label keeps the flattened form.
        return (
            'nectar_host_{}'.format(match.group('metric')),
            {'host': match.group('host'), 'home': match.group('home')},
        )

    match = _SITE_RE.match(path)
    if match:
        return (
            'nectar_site_{}_{}'.format(
                match.group('kind'), match.group('resource')
            ),
            {'site': match.group('site'), 'scope': match.group('scope')},
        )

    match = _IDP_RE.match(path)
    if match:
        # rcshibboleth.py flattens IdP hostnames with underscores
        # (e.g. idp_unimelb_edu_au); restore the real dots. Safe
        # because hostnames cannot contain underscores.
        idp = match.group('idp').replace('_', '.')
        return ('nectar_idp_users_total', {'idp': idp})

    match = _ACTIVE_PROJECTS_RE.match(path)
    if match:
        return ('nectar_active_projects', {'service': match.group('service')})

    return None
