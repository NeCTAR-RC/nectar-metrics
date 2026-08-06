import sys

from oslo_config import cfg
from oslo_log import log as logging

from nectar_metrics import config
from nectar_metrics.senders.base import DummySender
from nectar_metrics.senders.composite import GnocchiVictoriaSender
from nectar_metrics.senders.gnocchi import GnocchiSender
from nectar_metrics.senders.victoria import VictoriaMetricsSender
from nectar_metrics import sentry


CONF = config.CONF

cli_opts = [
    cfg.StrOpt(
        'protocol',
        required=True,
        choices=[
            'debug',
            'gnocchi',
            'victoria',
            'gnocchi_victoria',
        ],
        help='Sender used to report the metrics.',
    ),
    cfg.StrOpt(
        'victoria-url',
        help='VictoriaMetrics base URL (default: [victoria] url '
        'from the config file).',
    ),
]


class Main:
    def __init__(self, name, extra_opts=None):
        self.name = name
        self.conf = CONF
        logging.register_options(self.conf)
        self.conf.register_cli_opts(cli_opts)
        if extra_opts:
            self.conf.register_cli_opts(extra_opts)
        prog = 'nectar-metrics-' + name.replace('_', '-')
        try:
            config.init(prog=prog)
        except cfg.RequiredOptError as exc:
            sys.exit(f'{prog}: error: {exc}')
        logging.setup(self.conf, 'nectar_metrics')
        sentry.setup()

    def sender(self):
        if self.conf.protocol == 'gnocchi':
            sender = GnocchiSender()
        elif self.conf.protocol == 'victoria':
            sender = VictoriaMetricsSender(self._victoria_url())
        elif self.conf.protocol == 'gnocchi_victoria':
            sender = GnocchiVictoriaSender(self._victoria_url())
        else:
            sender = DummySender()

        return sender

    def _victoria_url(self):
        url = self.conf.victoria_url or self.conf.victoria.url
        if not url:
            sys.exit(
                'VictoriaMetrics URL not configured; set [victoria] url '
                'in the config file or pass --victoria-url'
            )
        return url
