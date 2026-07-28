from datetime import datetime, timezone

from nectar_metrics import gnocchi_backfill
from nectar_metrics import naming

from tests.utils import TestSender


def ts(epoch):
    return datetime.fromtimestamp(epoch, tz=timezone.utc)


def test_finest_points_prefers_finest_granularity():
    measures = [
        (ts(3600), 86400.0, 10.0),
        (ts(3600), 3600.0, 11.0),
        (ts(3600), 300.0, 12.0),
        (ts(7200), 3600.0, 13.0),
    ]
    assert gnocchi_backfill.finest_points(measures) == {
        3600: 12.0,
        7200: 13.0,
    }


def test_finest_points_accepts_iso_strings():
    measures = [('1970-01-02T00:00:00+00:00', 3600.0, 5.0)]
    assert gnocchi_backfill.finest_points(measures) == {86400: 5.0}


def test_site_paths():
    resource = {
        'name': 'monash',
        'metrics': {
            'capacity.local.vcpu': 'id-1',
            'usage.PT.disk': 'id-2',
            'availability.national.memory': 'id-3',
            # legacy plural resource from an old writer
            'usage.other.vcpus': 'id-4',
            'unrelated': 'id-5',
        },
    }
    assert sorted(gnocchi_backfill.site_paths(resource)) == [
        ('sites.monash.availability.national.memory', 'id-3'),
        ('sites.monash.capacity.local.vcpu', 'id-1'),
        ('sites.monash.usage.PT.disk', 'id-2'),
    ]


def test_host_paths():
    resource = {
        'name': 'qh2-rcc01.maas.cloud.unimelb.edu.au',
        'metrics': {
            'resource_provider.usage.PT.vcpu': 'id-1',
            'resource_provider.usage.national.uom.memory': 'id-2',
            # ceilometer placement pollster metrics are skipped
            'resource_provider.capacity.vcpu': 'id-3',
            'resource_provider.capacity.cores': 'id-4',
            'resource_provider.usage.disk': 'id-5',
        },
    }
    host = 'qh2_rcc01_maas_cloud_unimelb_edu_au'
    assert sorted(gnocchi_backfill.host_paths(resource)) == [
        (f'hosts.{host}.PT.used_vcpus', 'id-1'),
        (f'hosts.{host}.national.uom.used_memory', 'id-2'),
    ]


def test_generated_paths_map_in_naming():
    site = {
        'name': 'monash',
        'metrics': {
            f'{kind}.{scope}.{res}': 'id'
            for kind in gnocchi_backfill.SITE_KINDS
            for scope in ('local', 'national', 'PT', 'other', 'unknown')
            for res in gnocchi_backfill.SITE_RESOURCES
        },
    }
    rp = {
        'name': 'qh2-rcc01.maas.cloud.unimelb.edu.au',
        'metrics': {
            f'resource_provider.usage.{home}.{res}': 'id'
            for home in (
                'PT',
                'admin',
                'unknown',
                'preemptible',
                'national.monash',
                'local.uom',
            )
            for res in gnocchi_backfill.RES_TO_USED
        },
    }
    for path, _ in list(gnocchi_backfill.site_paths(site)) + list(
        gnocchi_backfill.host_paths(rp)
    ):
        assert naming.from_dotted_path(path) is not None, path


class FakeMetricManager:
    def __init__(self, measures_by_id):
        self.measures_by_id = measures_by_id

    def get_measures(self, metric, aggregation):
        assert aggregation == 'mean'
        return self.measures_by_id[metric]


class FakeResourceManager:
    def __init__(self, resources_by_type):
        self.resources_by_type = resources_by_type

    def list(self, resource_type):
        return self.resources_by_type.get(resource_type, [])


class FakeGnocchiClient:
    def __init__(self, resources_by_type, measures_by_id):
        self.resource = FakeResourceManager(resources_by_type)
        self.metric = FakeMetricManager(measures_by_id)


def make_client():
    resources = {
        'site': [
            {'name': 'monash', 'metrics': {'capacity.local.vcpu': 'm-1'}},
        ],
        'resource_provider': [
            {
                'name': 'cc1.test.rc.nectar.org.au',
                'metrics': {'resource_provider.usage.PT.vcpu': 'm-2'},
            },
        ],
    }
    measures = {
        'm-1': [(ts(3600), 3600.0, 100.0), (ts(7200), 3600.0, 101.0)],
        'm-2': [(ts(3600), 3600.0, 8.0)],
    }
    return FakeGnocchiClient(resources, measures)


def test_do_report_replays_sites_and_hosts():
    sender = TestSender()
    metrics, points = gnocchi_backfill.do_report(sender, make_client())
    assert metrics == 2
    assert points == 3
    assert sender.metrics == [
        ('sites.monash.capacity.local.vcpu', 100.0, 3600),
        ('sites.monash.capacity.local.vcpu', 101.0, 7200),
        ('hosts.cc1_test_rc_nectar_org_au.PT.used_vcpus', 8.0, 3600),
    ]
    assert sender.flushes == 1


def test_do_report_dry_run_sends_nothing():
    sender = TestSender()
    metrics, points = gnocchi_backfill.do_report(
        sender, make_client(), dry_run=True
    )
    assert metrics == 2
    assert points == 3
    assert sender.metrics == []
    assert sender.flushes == 0


def test_do_report_respects_limit():
    sender = TestSender()
    metrics, points = gnocchi_backfill.do_report(
        sender, make_client(), limit=1
    )
    assert metrics == 2
    assert points == 2
    assert [m[0] for m in sender.metrics] == [
        'sites.monash.capacity.local.vcpu',
        'hosts.cc1_test_rc_nectar_org_au.PT.used_vcpus',
    ]
