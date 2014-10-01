#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
test_nectar-metrics
----------------------------------

Tests for `nectar-metrics` module.
"""

from nectar_metrics import nova

users = {1: 'user1', 2: 'user2', 3: 'user3'}

servers = [{'flavor': {'id': i},
            'OS-EXT-AZ:availability_zone': 'zone1',
            'user_id': i,
            'tenant_id': i * 10}
           for i in [1, 1, 1, 1, 1, 2, 2, 2, 3]]

flavors = {1: {'vcpus': 1, 'ram': 1, 'disk': 1},
           2: {'vcpus': 2, 'ram': 2, 'disk': 2},
           3: {'vcpus': 3, 'ram': 3, 'disk': 3}}


def test_server_metrics():
    """A simple flavor metric count test"""
    assert nova.server_metrics(servers, flavors) == \
        {'total_instances': 9,
         'used_disk': 14,
         'used_memory': 14,
         'used_vcpus': 14}


cells = {'zone1': servers}


class TestSender():
    def __init__(self):
        self.graphite_domain = []
        self.graphite_cell = []
        self.graphite_tenant = []

    def send_graphite_domain(self, *args):
        self.graphite_domain.append(args)

    def send_graphite_cell(self, *args):
        self.graphite_cell.append(args)

    def send_graphite_tenant(self, *args):
        self.graphite_tenant.append(args)


def test_by_cell():
    """A simple by_cell metric count test"""
    sender = TestSender()
    nova.by_cell(cells, flavors, 'sentinel', sender)

    assert sender.graphite_cell == \
        [('zone1', 'total_instances', 9, 'sentinel'),
         ('zone1', 'used_memory', 14, 'sentinel'),
         ('zone1', 'used_vcpus', 14, 'sentinel'),
         ('zone1', 'used_disk', 14, 'sentinel')]


def test_by_domain():
    """A simple by_domain metric count test"""
    sender = TestSender()
    nova.by_domain(servers, flavors, users, 'sentinel', sender)
    assert sender.graphite_domain == \
        [('zone1', 'user2', 'used_vcpus', 6, 'sentinel'),
         ('zone1', 'user3', 'used_vcpus', 3, 'sentinel'),
         ('zone1', 'user1', 'used_vcpus', 5, 'sentinel')]


def test_by_tenant():
    """A simple by_tenant metric count test"""
    sender = TestSender()
    nova.by_tenant(servers, flavors, 'sentinel', sender)
    assert sender.graphite_tenant == \
        [(10, 1, 'total_instances', 5, 'sentinel'),
         (10, 1, 'used_vcpus', 5, 'sentinel'),
         (20, 2, 'total_instances', 3, 'sentinel'),
         (20, 2, 'used_vcpus', 6, 'sentinel'),
         (30, 3, 'total_instances', 1, 'sentinel'),
         (30, 3, 'used_vcpus', 3, 'sentinel')]
