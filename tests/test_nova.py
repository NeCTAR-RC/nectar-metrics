from nectar_metrics import nova

from .utils import TestSender

users = {1: 'user1', 2: 'user2', 3: 'user3'}

servers = [{'flavor': {'vcpus': i,
                       'ram': i,
                       'disk': i, },
            'OS-EXT-AZ:availability_zone': 'zone1',
            'user_id': i,
            'tenant_id': i * 10}
           for i in [1, 1, 1, 1, 1, 2, 2, 2, 3]]


def test_server_metrics():
    """A simple flavor metric count test"""
    assert nova.server_metrics(servers) == \
        {'total_instances': 9,
         'used_disk': 14,
         'used_memory': 14,
         'used_vcpus': 14}


azs = {'zone1': servers}


def test_by_az():
    """A simple by_cell metric count test"""
    sender = TestSender()
    nova.by_az(azs, 'sentinel', sender)
    output = sorted(sender.by_az, key=lambda tup: tup[1])
    assert output == [('zone1', 'total_instances', 9, 'sentinel'),
                      ('zone1', 'used_disk', 14, 'sentinel'),
                      ('zone1', 'used_memory', 14, 'sentinel'),
                      ('zone1', 'used_vcpus', 14, 'sentinel')]


def test_by_az_by_domain():
    """A simple by_domain metric count test"""
    sender = TestSender()
    nova.by_az_by_domain(servers, users, 'sentinel', sender)
    output = sorted(sender.by_az_by_domain, key=lambda tup: tup[1])
    assert output == [('zone1', 'user1', 'used_vcpus', 5, 'sentinel'),
                      ('zone1', 'user2', 'used_vcpus', 6, 'sentinel'),
                      ('zone1', 'user3', 'used_vcpus', 3, 'sentinel')]


def test_by_az_by_tenant():
    """A simple by_tenant metric count test"""
    sender = TestSender()
    nova.by_az_by_tenant(servers, 'sentinel', sender)
    output = sorted(sender.by_az_by_tenant, key=lambda tup: (tup[1], tup[2]))
    assert output == [('zone1', 10, 'total_instances', 5, 'sentinel'),
                      ('zone1', 10, 'used_memory', 5, 'sentinel'),
                      ('zone1', 10, 'used_vcpus', 5, 'sentinel'),
                      ('zone1', 20, 'total_instances', 3, 'sentinel'),
                      ('zone1', 20, 'used_memory', 6, 'sentinel'),
                      ('zone1', 20, 'used_vcpus', 6, 'sentinel'),
                      ('zone1', 30, 'total_instances', 1, 'sentinel'),
                      ('zone1', 30, 'used_memory', 3, 'sentinel'),
                      ('zone1', 30, 'used_vcpus', 3, 'sentinel')]


def test_by_tenant():
    """A simple by_tenant metric count test"""
    sender = TestSender()
    nova.by_tenant(servers, 'sentinel', sender)
    output = sorted(sender.by_tenant, key=lambda tup: (tup[0], tup[1]))
    assert output == [(10, 'total_instances', 5, 'sentinel'),
                      (10, 'used_memory', 5, 'sentinel'),
                      (10, 'used_vcpus', 5, 'sentinel'),
                      (20, 'total_instances', 3, 'sentinel'),
                      (20, 'used_memory', 6, 'sentinel'),
                      (20, 'used_vcpus', 6, 'sentinel'),
                      (30, 'total_instances', 1, 'sentinel'),
                      (30, 'used_memory', 3, 'sentinel'),
                      (30, 'used_vcpus', 3, 'sentinel')]
