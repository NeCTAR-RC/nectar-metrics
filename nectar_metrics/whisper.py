from __future__ import absolute_import
import os
from os import path
import logging

import whisper

from nectar_metrics.cli import Main

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
                logger.info("Skipping %s" % filepath)
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
    parser = Main('whisper')
    parser.add_argument(
        '--limit', default=None,
        help='Limit the number of metrics to send from each file.')
    parser.add_argument(
        'path', type=str, help='The path to the whisper files to send.')
    args = parser.parse_args()
    logger.info("Running Report")
    do_report(parser.sender(), args.path, args.limit)
