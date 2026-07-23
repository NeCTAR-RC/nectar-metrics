import json

import pytest

from nectar_metrics import config
from nectar_metrics.senders import victoria
from nectar_metrics.senders.graphite import SocketMetricSender


def test_socket_sender_sends_bytes(mocker):
    socket_class = mocker.patch(
        'nectar_metrics.senders.graphite.socket.socket')
    sock = socket_class.return_value
    sender = SocketMetricSender('carbon.example.com', 2003)
    sender.send_metric('az.zone1.used_vcpus', 10.5, 1400000000)
    sock.sendall.assert_called_once_with(
        b'az.zone1.used_vcpus 10.50 1400000000\n')


def make_sender(mocker):
    sender = victoria.VictoriaMetricsSender(url='http://vm:8428/')
    sender.session = mocker.Mock()
    return sender


def posted_series(sender):
    (url,), kwargs = sender.session.post.call_args
    lines = kwargs['data'].decode('utf-8').split('\n')
    return url, [json.loads(line) for line in lines]


def test_victoria_send_and_flush(mocker):
    sender = make_sender(mocker)
    sender.send_by_az('zone1', 'used_vcpus', 10, 1400000000)
    sender.send_by_az('zone1', 'used_vcpus', 11, 1400000300)
    sender.send_global('users.total', 500001, 1400000000)
    sender.flush()

    url, series = posted_series(sender)
    assert url == 'http://vm:8428/api/v1/import'
    by_name = dict((line['metric']['__name__'], line) for line in series)
    vcpus = by_name['nectar_used_vcpus']
    assert vcpus['metric'] == {'__name__': 'nectar_used_vcpus',
                               'az': 'zone1'}
    assert vcpus['timestamps'] == [1400000000000, 1400000300000]
    assert vcpus['values'] == [10.0, 11.0]
    users = by_name['nectar_users_total']
    assert users['metric'] == {'__name__': 'nectar_users_total'}
    assert users['values'] == [500001.0]
    # buffer cleared after flush
    assert sender.buffered == {}
    assert sender.buffered_count == 0


def test_victoria_preserves_precision(mocker):
    sender = make_sender(mocker)
    sender.send_metric('az.zone1.used_vcpus', 10.123456789, 1400000000)
    sender.flush()
    _, series = posted_series(sender)
    assert series[0]['values'] == [10.123456789]


def test_victoria_drops_unmigrated(mocker):
    sender = make_sender(mocker)
    sender.send_by_tenant('8ffff', 'used_vcpus', 1, 1400000000)
    sender.send_by_idp('idp_unimelb_edu_au', 'total', 5, 1400000000)
    sender.send_by_host_by_home('qh2-rcc-1', 'national', 'used_vcpus',
                                2, 1400000000)
    sender.send_capacity_by_site('monash', 'national', 'vcpu',
                                 100, 1400000000)
    assert sender.buffered == {}
    assert sender.dropped == 4
    sender.flush()
    sender.session.post.assert_not_called()


def test_victoria_domain_labels(mocker):
    sender = make_sender(mocker)
    sender.send_by_az_by_domain('zone1', 'unimelb_edu_au', 'used_vcpus',
                                7, 1400000000)
    sender.send_by_az_by_home('zone1', 'monash', 'used_vcpus',
                              8, 1400000000)
    sender.flush()
    _, series = posted_series(sender)
    by_name = dict((line['metric']['__name__'], line) for line in series)
    assert by_name['nectar_domain_used_vcpus']['metric'] == {
        '__name__': 'nectar_domain_used_vcpus',
        'az': 'zone1',
        'domain': 'unimelb.edu.au'}
    assert by_name['nectar_allocation_home_used_vcpus']['metric'] == {
        '__name__': 'nectar_allocation_home_used_vcpus',
        'az': 'zone1',
        'home': 'monash'}


def test_victoria_auto_flush(mocker, monkeypatch):
    monkeypatch.setattr(victoria, 'FLUSH_AT', 3)
    sender = make_sender(mocker)
    for i in range(3):
        sender.send_by_az('zone1', 'used_vcpus', i, 1400000000 + i)
    assert sender.session.post.call_count == 1
    assert sender.buffered == {}


def test_victoria_url_from_config():
    config.CONFIG.set('victoria', 'url', 'http://fromconf:8428')
    try:
        sender = victoria.VictoriaMetricsSender()
        assert sender.url == 'http://fromconf:8428'
    finally:
        del config.CONFIG.data['victoria']


def test_victoria_no_url_raises():
    assert config.CONFIG.get('victoria', 'url') is None
    with pytest.raises(ValueError):
        victoria.VictoriaMetricsSender()
