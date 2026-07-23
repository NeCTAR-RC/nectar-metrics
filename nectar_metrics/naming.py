"""Mapping from legacy Graphite dotted metric paths to the
Prometheus-style metric names and labels used by VictoriaMetrics.

Dotted paths are the interchange format between the collectors (the
BaseSender helpers compose dotted paths), the whisper backfill tool
(paths derived from .wsp file names) and the VictoriaMetrics sender.
Keeping a single parser here guarantees that backfilled history and
live writes always map to identical series.

Only the metrics the status page (langstroth) uses are mapped, plus
the cheap active.projects globals; every other path returns None and
is dropped by the VictoriaMetrics sender.
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

_AZ_RE = re.compile(
    r'^az\.(?P<az>[^.]+)\.(?P<metric>%s)$' % '|'.join(AZ_METRICS))
_DOMAIN_RE = re.compile(
    r'^az\.(?P<az>[^.]+)\.domain\.(?P<domain>[^.]+)\.used_vcpus$')
_HOME_RE = re.compile(
    r'^az\.(?P<az>[^.]+)\.allocation_home\.(?P<home>[^.]+)\.used_vcpus$')
_ACTIVE_PROJECTS_RE = re.compile(
    r'^active\.projects\.(?P<service>[^.]+)$')


def from_dotted_path(path):
    """Map a legacy dotted metric path to a (name, labels) tuple.

    Returns None for paths outside the migrated set (per-tenant,
    per-idp, hosts, sites, ...).
    """
    if path == 'users.total':
        return ('nectar_users_total', {})

    match = _AZ_RE.match(path)
    if match:
        return ('nectar_%s' % match.group('metric'),
                {'az': match.group('az')})

    match = _DOMAIN_RE.match(path)
    if match:
        # nova.py flattens email domains with underscores
        # (e.g. unimelb_edu_au); restore the real dots. Safe because
        # hostnames cannot contain underscores.
        domain = match.group('domain').replace('_', '.')
        return ('nectar_domain_used_vcpus',
                {'az': match.group('az'), 'domain': domain})

    match = _HOME_RE.match(path)
    if match:
        return ('nectar_allocation_home_used_vcpus',
                {'az': match.group('az'), 'home': match.group('home')})

    match = _ACTIVE_PROJECTS_RE.match(path)
    if match:
        return ('nectar_active_projects',
                {'service': match.group('service')})

    return None
