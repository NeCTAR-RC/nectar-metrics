from nectar_metrics import cinder

from .utils import TestSender

users = {1: 'user1', 2: 'user2', 3: 'user3'}

volumes = [{'size': i,
            'availability_zone': 'zone1',
            'user_id': i,
            'os-vol-tenant-attr:tenant_id': i * 10}
           for i in [1, 1, 1, 1, 1, 2, 2, 2, 3]]


def test_by_tenant():
    """A simple by_tenant metric count test"""
    sender = TestSender()
    cinder.by_tenant(volumes, 'sentinel', sender)
    output = sorted(sender.by_tenant, key=lambda tup: (tup[0], tup[1]))
    assert output == \
    [(10, 'total_volumes', 5, 'sentinel'),
     (10, 'used_volume_size', 5, 'sentinel'),
     (20, 'total_volumes', 3, 'sentinel'),
     (20, 'used_volume_size', 6, 'sentinel'),
     (30, 'total_volumes', 1, 'sentinel'),
     (30, 'used_volume_size', 3, 'sentinel')]


def test_by_az_by_tenant():
    """A simple by_tenant metric count test"""
    sender = TestSender()
    cinder.by_az_by_tenant(volumes, 'sentinel', sender)
    output = sorted(sender.by_az_by_tenant, key=lambda tup: (tup[1], tup[2]))
    assert output == \
    [('zone1', 10, 'total_volumes', 5, 'sentinel'),
     ('zone1', 10, 'used_volume_size', 5, 'sentinel'),
     ('zone1', 20, 'total_volumes', 3, 'sentinel'),
     ('zone1', 20, 'used_volume_size', 6, 'sentinel'),
     ('zone1', 30, 'total_volumes', 1, 'sentinel'),
     ('zone1', 30, 'used_volume_size', 3, 'sentinel')]
