from unittest import mock

from keystoneauth1 import exceptions as ksa_exceptions
from novaclient import exceptions as nova_exceptions
import pytest

from nectar_metrics import retry


def _nova_error(code):
    exc = nova_exceptions.ClientException(code)
    exc.code = code
    return exc


def test_returns_result_without_retry():
    func = mock.Mock(return_value='ok')
    wrapped = retry.retry_on_transient()(func)

    with mock.patch.object(retry.time, 'sleep') as sleep:
        assert wrapped('arg', kw=1) == 'ok'

    func.assert_called_once_with('arg', kw=1)
    sleep.assert_not_called()


def test_retries_transient_then_succeeds():
    func = mock.Mock(side_effect=[_nova_error(504), _nova_error(503), 'ok'])
    wrapped = retry.retry_on_transient(backoff=1)(func)

    with mock.patch.object(retry.time, 'sleep') as sleep:
        assert wrapped() == 'ok'

    assert func.call_count == 3
    # Exponential backoff: 1s then 2s.
    assert [c.args[0] for c in sleep.call_args_list] == [1, 2]


def test_gives_up_after_max_attempts():
    func = mock.Mock(side_effect=_nova_error(504))
    wrapped = retry.retry_on_transient(max_attempts=3, backoff=1)(func)

    with mock.patch.object(retry.time, 'sleep'):
        with pytest.raises(nova_exceptions.ClientException):
            wrapped()

    assert func.call_count == 3


def test_does_not_retry_non_transient():
    func = mock.Mock(side_effect=_nova_error(400))
    wrapped = retry.retry_on_transient()(func)

    with mock.patch.object(retry.time, 'sleep') as sleep:
        with pytest.raises(nova_exceptions.ClientException):
            wrapped()

    func.assert_called_once()
    sleep.assert_not_called()


def test_retries_connection_failure():
    func = mock.Mock(side_effect=[ksa_exceptions.ConnectFailure('boom'), 'ok'])
    wrapped = retry.retry_on_transient(backoff=1)(func)

    with mock.patch.object(retry.time, 'sleep'):
        assert wrapped() == 'ok'

    assert func.call_count == 2


def test_keystoneauth_status_code_is_transient():
    # keystoneauth1 exposes the status as http_status rather than code.
    assert retry._is_transient(ksa_exceptions.GatewayTimeout())
    assert not retry._is_transient(ksa_exceptions.BadRequest())
