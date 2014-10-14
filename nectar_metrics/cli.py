from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

from nectar_metrics import log
from nectar_metrics import config
from nectar_metrics.graphite import (PickleSocketMetricSender,
                                     DummySender, SocketMetricSender)


class Main(object):
    def __init__(self, name):
        self.parser = ArgumentParser(
            formatter_class=ArgumentDefaultsHelpFormatter)
        self.parser.add_argument(
            '-v', '--verbose', action='count', default=0,
            help="Increase verbosity (specify multiple times for more)")
        self.parser.add_argument(
            '-q', '--quiet', action='store_true',
            help="Don't print any logging output")
        self.parser.add_argument(
            '--protocol', choices=['debug', 'carbon', 'carbon_pickle'],
            required=True)
        self.parser.add_argument(
            '--carbon-host', help='Carbon Host.')
        self.parser.add_argument(
            '--carbon-port', default=2003, type=int, help='Carbon Port.')
        self.parser.add_argument(
            '--config', default=config.CONFIG_FILE, type=str,
            help='Config file path.')
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

    def sender(self):
        args = self.parse_args()

        if args.protocol == 'carbon':
            if not args.carbon_host:
                self.parser.error('argument --carbon-host is required')
            if not args.carbon_port:
                self.parser.error('argument --carbon-port is required')
            sender = SocketMetricSender(args.carbon_host, args.carbon_port)
        elif args.protocol == 'carbon_pickle':
            if not args.carbon_host:
                self.parser.error('argument --carbon-host is required')
            if not args.carbon_port:
                self.parser.error('argument --carbon-port is required')
            sender = PickleSocketMetricSender(args.carbon_host,
                                              args.carbon_port)
        elif args.protocol == 'debug':
            sender = DummySender()

        return sender

    def logging(self):
        args = self.parse_args()

        log_level = 'WARNING'
        if args.verbose == 1:
            log_level = 'INFO'
        elif args.verbose >= 2:
            log_level = 'DEBUG'
        elif args.quiet:
            log_level = None
        log.setup('%s.log' % self.name, 'INFO', log_level)
