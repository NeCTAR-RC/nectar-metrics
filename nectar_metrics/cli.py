from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

from nectar_metrics import config
from nectar_metrics import log
from nectar_metrics.senders.base import DummySender
from nectar_metrics.senders.composite import GnocchiVictoriaSender
from nectar_metrics.senders.gnocchi import GnocchiSender
from nectar_metrics.senders.victoria import VictoriaMetricsSender
from nectar_metrics import sentry


class Main:
    def __init__(self, name):
        self.parser = ArgumentParser(
            formatter_class=ArgumentDefaultsHelpFormatter
        )
        self.parser.add_argument(
            '-v',
            '--verbose',
            action='count',
            default=0,
            help="Increase verbosity (specify multiple times for more)",
        )
        self.parser.add_argument(
            '-q',
            '--quiet',
            action='store_true',
            help="Don't print any logging output",
        )
        self.parser.add_argument(
            '--protocol',
            choices=[
                'debug',
                'gnocchi',
                'victoria',
                'gnocchi_victoria',
            ],
            required=True,
        )
        self.parser.add_argument(
            '--victoria-url',
            help='VictoriaMetrics base URL (default: [victoria] url '
            'from the config file).',
        )
        self.parser.add_argument(
            '--config',
            default=config.CONFIG_FILE,
            type=str,
            help='Config file path.',
        )
        self.parsed_args = None
        self.name = name

    def add_argument(self, *args, **kwargs):
        return self.parser.add_argument(*args, **kwargs)

    def parse_args(self):
        if not self.parsed_args:
            self.parsed_args = self.parser.parse_args()
            self._post_arg_parsing()
        return self.parsed_args

    def _post_arg_parsing(self):
        config.read(self.parsed_args.config)
        self.logging()
        sentry.setup()

    def sender(self):
        args = self.parse_args()

        if args.protocol == 'gnocchi':
            sender = GnocchiSender()
        elif args.protocol == 'victoria':
            sender = VictoriaMetricsSender(self._victoria_url(args))
        elif args.protocol == 'gnocchi_victoria':
            sender = GnocchiVictoriaSender(self._victoria_url(args))
        elif args.protocol == 'debug':
            sender = DummySender()

        return sender

    def _victoria_url(self, args):
        url = args.victoria_url or config.CONFIG.get('victoria', 'url')
        if not url:
            self.parser.error(
                'VictoriaMetrics URL not configured; set [victoria] url '
                'in the config file or pass --victoria-url'
            )
        return url

    def logging(self):
        args = self.parse_args()

        log_level = 'WARNING'
        if args.verbose == 1:
            log_level = 'INFO'
        elif args.verbose >= 2:
            log_level = 'DEBUG'
        elif args.quiet:
            log_level = None
        log.setup(f'{self.name}.log', 'INFO', log_level)
