from __future__ import absolute_import
import os
from os import path
import logging

import whisper

from nectar_metrics import log
from nectar_metrics import config
from nectar_metrics.graphite import (PickleSocketMetricSender,
                                     DummySender, SocketMetricSender)

logger = logging.getLogger(__name__)


def send_file(sender, filepath, metricpath, limit=None):
    try:
        time_info, values = whisper.fetch(filepath, 0)
    except whisper.CorruptWhisperFile:
        logger.warning("Corrupt whisper file %s" % filepath)
        return
    metrics = zip(range(*time_info), values)
    count = 0
    for time, value in metrics:
        if value is None:
            continue
        count += 1
        sender.send_metric(metricpath, value, time)
        if limit and count > limit:
            return


def paths_in_directory(directory):
    directory = path.abspath(directory)
    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in filenames:
            filepath = path.join(dirpath, filename)
            if not filename.endswith('.wsp'):
                logger.inf("Skipping %s" % filepath)
                continue
            # convert /var/lib/graphite/server/metric.wsp to
            # server.metric
            metric_path = filepath[len(directory) + 1:].replace('/', '.')[:-4]
            yield filepath, metric_path


def do_report(sender, filepaths, limit=None):
    for filepath, metricpath in paths_in_directory(filepaths):
        logger.info("Processing %s" % filepath)
        send_file(sender, filepath, metricpath)
    sender.flush()


def main():
    from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-v', '--verbose', action='count', default=0,
        help="Increase verbosity (specify multiple times for more)")
    parser.add_argument(
        '-q', '--quiet', action='store_true',
        help="Don't print any logging output")
    parser.add_argument(
        '--protocol', choices=['debug', 'carbon', 'carbon_pickle'],
        required=True)
    parser.add_argument(
        '--carbon-host', help='Carbon Host.')
    parser.add_argument(
        '--carbon-port', default=2003, type=int, help='Carbon Port.')
    parser.add_argument(
        '--config', default=config.CONFIG_FILE, type=str,
        help='Config file path.')
    parser.add_argument(
        '--limit', default=None,
        help='Limit the number of metrics to send from each file.')
    parser.add_argument(
        'path', type=str, help='The path to the whisper files to send.')
    args = parser.parse_args()
    config.read(args.config)

    log_level = 'WARNING'
    if args.verbose == 1:
        log_level = 'INFO'
    elif args.verbose >= 2:
        log_level = 'DEBUG'
    elif args.quiet:
        log_level = None
    log.setup('nova.log', 'INFO', log_level)

    if args.protocol == 'carbon':
        if not args.carbon_host:
            parser.error('argument --carbon-host is required')
        if not args.carbon_port:
            parser.error('argument --carbon-port is required')
        sender = SocketMetricSender(args.carbon_host, args.carbon_port)
    elif args.protocol == 'carbon_pickle':
        if not args.carbon_host:
            parser.error('argument --carbon-host is required')
        if not args.carbon_port:
            parser.error('argument --carbon-port is required')
        sender = PickleSocketMetricSender(args.carbon_host, args.carbon_port)
    elif args.protocol == 'debug':
        sender = DummySender()

    logger.info("Running Report")
    do_report(sender, args.path, args.limit)
