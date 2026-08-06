import os
import sys

from oslo_config import cfg


CONF = cfg.CONF

metrics_opts = [
    cfg.StrOpt(
        'working_dir',
        default='.',
        help='Directory used to store state between runs.',
    ),
]

openstack_opts = [
    cfg.StrOpt('user', help='OpenStack username.'),
    cfg.StrOpt('passwd', secret=True, help='OpenStack password.'),
    cfg.StrOpt('name', help='OpenStack project name.'),
    cfg.StrOpt('url', help='Keystone authentication URL.'),
]

gnocchi_opts = [
    cfg.StrOpt(
        'archive_policy',
        help='Archive policy used when creating new metrics.',
    ),
]

victoria_opts = [
    cfg.StrOpt('url', help='VictoriaMetrics base URL.'),
]

sentry_opts = [
    cfg.StrOpt(
        'dsn',
        secret=True,
        help='GlitchTip/Sentry compatible DSN. When set, unhandled '
        'exceptions and ERROR level log messages are reported.',
    ),
    cfg.StrOpt('environment', help='Sentry environment name.'),
]

CONF.register_opts(metrics_opts, group='metrics')
CONF.register_opts(openstack_opts, group='openstack')
CONF.register_opts(gnocchi_opts, group='gnocchi')
CONF.register_opts(victoria_opts, group='victoria')
CONF.register_opts(sentry_opts, group='sentry')


def default_config_files():
    """Find metrics.ini in the standard locations.

    Searches the oslo.config default directories (~/.nectar/, ~/,
    /etc/nectar/ and /etc/) and falls back to a metrics.ini in the
    current working directory.
    """
    files = cfg.find_config_files(
        project='nectar', prog='metrics', extension='.ini'
    )
    if not files:
        local = os.path.join(os.getcwd(), 'metrics.ini')
        if os.path.exists(local):
            files = [local]
    return files


def init(args=None, prog=None):
    """Parse the config files and command line options."""
    if args is None:
        args = sys.argv[1:]
    CONF(
        args,
        project='nectar-metrics',
        prog=prog,
        default_config_files=default_config_files(),
    )
    if not CONF.config_file:
        raise Exception("Can't find configuration file: metrics.ini")
