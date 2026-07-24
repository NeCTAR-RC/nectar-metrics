from nectar_metrics.senders import composite

from tests.utils import TestSender


def make_transition_sender():
    sender = composite.GnocchiGraphiteVictoriaSender.__new__(
        composite.GnocchiGraphiteVictoriaSender
    )
    sender.gnocchi = TestSender()
    sender.graphite = TestSender()
    sender.victoria = TestSender()
    return sender


def make_end_state_sender():
    sender = composite.GnocchiVictoriaSender.__new__(
        composite.GnocchiVictoriaSender
    )
    sender.gnocchi = TestSender()
    sender.victoria = TestSender()
    return sender


def test_transition_forwards_migration_set_to_victoria():
    sender = make_transition_sender()
    sender.send_by_az('zone1', 'used_vcpus', 1, 't')
    sender.send_by_az_by_domain(
        'zone1', 'unimelb_edu_au', 'used_vcpus', 2, 't'
    )
    sender.send_by_az_by_home('zone1', 'monash', 'used_vcpus', 3, 't')
    sender.send_global('users.total', 4, 't')

    for leg in (sender.graphite, sender.victoria):
        assert leg.by_az == [('zone1', 'used_vcpus', 1, 't')]
        assert leg.by_az_by_domain == [
            ('zone1', 'unimelb_edu_au', 'used_vcpus', 2, 't')
        ]
        assert leg.by_az_by_home == [('zone1', 'monash', 'used_vcpus', 3, 't')]
        assert leg.by_global == [('users.total', 4, 't')]
    # send_global also goes to gnocchi (unchanged behaviour)
    assert sender.gnocchi.by_global == [('users.total', 4, 't')]


def test_transition_keeps_tenant_and_idp_off_victoria():
    sender = make_transition_sender()
    sender.send_by_tenant('8ffff', 'used_vcpus', 1, 't')
    sender.send_by_az_by_tenant('zone1', '8ffff', 'used_vcpus', 2, 't')
    sender.send_by_idp('idp_unimelb_edu_au', 'total', 3, 't')

    assert sender.graphite.by_tenant == [('8ffff', 'used_vcpus', 1, 't')]
    assert sender.graphite.by_az_by_tenant == [
        ('zone1', '8ffff', 'used_vcpus', 2, 't')
    ]
    assert sender.graphite.by_idp == [('idp_unimelb_edu_au', 'total', 3, 't')]
    assert sender.victoria.by_tenant == []
    assert sender.victoria.by_az_by_tenant == []
    assert sender.victoria.by_idp == []


def test_transition_site_metrics_stay_on_gnocchi():
    sender = make_transition_sender()
    sender.send_capacity_by_site('monash', 'national', 'vcpu', 1, 't')
    sender.send_by_host_by_home('qh2-rcc-1', 'national', 'used_vcpus', 2, 't')
    assert sender.gnocchi.capacity_by_site == [
        ('monash', 'national', 'vcpu', 1, 't')
    ]
    assert sender.victoria.capacity_by_site == []
    assert sender.victoria.by_host_by_home == []


def test_transition_flush_reaches_both_legs():
    sender = make_transition_sender()
    sender.flush()
    assert sender.graphite.flushes == 1
    assert sender.victoria.flushes == 1


def test_end_state_routing():
    sender = make_end_state_sender()
    sender.send_by_az('zone1', 'used_vcpus', 1, 't')
    sender.send_by_az_by_domain(
        'zone1', 'unimelb_edu_au', 'used_vcpus', 2, 't'
    )
    sender.send_by_az_by_home('zone1', 'monash', 'used_vcpus', 3, 't')
    sender.send_global('users.total', 4, 't')
    sender.send_capacity_by_site('monash', 'national', 'vcpu', 5, 't')
    sender.send_usage_by_site('monash', 'national', 'vcpu', 6, 't')
    sender.send_availability_by_site('monash', 'national', 'vcpu', 7, 't')
    sender.send_by_host_by_home('qh2-rcc-1', 'national', 'used_vcpus', 8, 't')

    assert sender.victoria.by_az == [('zone1', 'used_vcpus', 1, 't')]
    assert sender.victoria.by_az_by_domain == [
        ('zone1', 'unimelb_edu_au', 'used_vcpus', 2, 't')
    ]
    assert sender.victoria.by_az_by_home == [
        ('zone1', 'monash', 'used_vcpus', 3, 't')
    ]
    assert sender.victoria.by_global == [('users.total', 4, 't')]
    assert sender.gnocchi.by_global == [('users.total', 4, 't')]
    assert sender.gnocchi.capacity_by_site == [
        ('monash', 'national', 'vcpu', 5, 't')
    ]
    assert sender.gnocchi.usage_by_site == [
        ('monash', 'national', 'vcpu', 6, 't')
    ]
    assert sender.gnocchi.availability_by_site == [
        ('monash', 'national', 'vcpu', 7, 't')
    ]
    assert sender.gnocchi.by_host_by_home == [
        ('qh2-rcc-1', 'national', 'used_vcpus', 8, 't')
    ]
    # gnocchi never sees az/domain/home; victoria never sees sites/hosts
    assert sender.gnocchi.by_az == []
    assert sender.victoria.capacity_by_site == []


def test_end_state_retired_series_are_noops():
    sender = make_end_state_sender()
    sender.send_by_tenant('8ffff', 'used_vcpus', 1, 't')
    sender.send_by_az_by_tenant('zone1', '8ffff', 'used_vcpus', 2, 't')
    sender.send_by_idp('idp_unimelb_edu_au', 'total', 3, 't')
    for leg in (sender.gnocchi, sender.victoria):
        assert leg.by_tenant == []
        assert leg.by_az_by_tenant == []
        assert leg.by_idp == []
