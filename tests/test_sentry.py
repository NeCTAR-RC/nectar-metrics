import importlib.metadata
import os
import sys
from unittest import mock

import pytest

from nectar_metrics import config
from nectar_metrics import sentry


CONF = config.CONF

DSN = 'https://key@glitchtip.example.com/1'
RELEASE = 'nectar-metrics@1.0.0'


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    monkeypatch.delenv('SENTRY_DSN', raising=False)
    yield
    CONF.clear_override('dsn', group='sentry')
    CONF.clear_override('environment', group='sentry')


@mock.patch('nectar_metrics.sentry._get_release', return_value=RELEASE)
@mock.patch('nectar_metrics.sentry.sentry_sdk')
class TestSentrySetup:
    def test_setup_no_config(self, mock_sdk, mock_release):
        assert not sentry.setup()
        mock_sdk.init.assert_not_called()

    def test_setup_with_dsn(self, mock_sdk, mock_release):
        CONF.set_override('dsn', DSN, group='sentry')
        CONF.set_override('environment', 'testing', group='sentry')
        assert sentry.setup()
        mock_sdk.init.assert_called_once_with(
            dsn=DSN,
            environment='testing',
            release=RELEASE,
            auto_session_tracking=False,
        )
        mock_sdk.set_tag.assert_called_once_with(
            'command', os.path.basename(sys.argv[0])
        )

    def test_setup_dsn_only(self, mock_sdk, mock_release):
        CONF.set_override('dsn', DSN, group='sentry')
        assert sentry.setup()
        mock_sdk.init.assert_called_once_with(
            dsn=DSN,
            environment=None,
            release=RELEASE,
            auto_session_tracking=False,
        )

    def test_setup_dsn_from_environment(self, mock_sdk, mock_release):
        with mock.patch.dict(os.environ, {'SENTRY_DSN': DSN}):
            assert sentry.setup()
        mock_sdk.init.assert_called_once_with(
            dsn=DSN,
            environment=None,
            release=RELEASE,
            auto_session_tracking=False,
        )


class TestGetRelease:
    def test_get_release(self):
        with mock.patch(
            'nectar_metrics.sentry.importlib.metadata.version',
            return_value='1.0.0',
        ) as mock_version:
            assert sentry._get_release() == RELEASE
        mock_version.assert_called_once_with('nectar-metrics')

    def test_get_release_not_installed(self):
        with mock.patch(
            'nectar_metrics.sentry.importlib.metadata.version',
            side_effect=importlib.metadata.PackageNotFoundError,
        ):
            assert sentry._get_release() is None
