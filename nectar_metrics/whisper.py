"""Replay historical datapoints from Graphite whisper files.

Used for the one-off migration of history into VictoriaMetrics
(--protocol victoria), but works with any sender.

Whisper files hold several retention archives at different
resolutions (e.g. 5m:7d, 10m:2y, 2h:30y). A plain whisper.fetch()
over the whole history returns only the single coarsest archive that
covers the range, silently dropping the higher-resolution recent
bands. This tool slices the history into one disjoint band per
archive - each band being the window for which that archive is the
highest-resolution data available - and replays the bands coarsest
first, so points stream out in chronological order with no duplicate
timestamps.

Re-runs are safe: identical (series, timestamp, value) points are
deduplicated by VictoriaMetrics. Resume = rerun, ideally with the
same --now value so band boundaries are identical.
"""

import logging
import os
from os import path
import re
import time

import whisper

from nectar_metrics.cli import Main

logger = logging.getLogger(__name__)

# The metrics the status page (langstroth) uses, plus the cheap
# active.projects globals - exactly what the live dual-write forwards
# to VictoriaMetrics, so backfilled and live series sets match. Keep
# in sync with nectar_metrics/naming.py.
DEFAULT_INCLUDES = [
    'users.total',
    'az.*.total_instances',
    'az.*.used_vcpus',
    'az.*.used_memory',
    'az.*.used_disk',
    'az.*.instances_created',
    'az.*.instances_deleted',
    'az.*.domain.*.used_vcpus',
    'az.*.allocation_home.*.used_vcpus',
    'active.projects.*',
]


def glob_to_regex(pattern):
    """Translate a graphite glob to a compiled regex.

    Unlike fnmatch, '*' must not cross path components (dots), so
    az.*.used_vcpus does not also match az.x.domain.y.used_vcpus.
    """
    return re.compile(
        '^{}$'.format(re.escape(pattern).replace(r'\*', '[^.]*'))
    )


class RateLimiter:
    """Crude pacing: allow up to per_second sends each second."""

    def __init__(self, per_second):
        self.per_second = per_second
        self.window = time.time()
        self.count = 0

    def wait(self):
        self.count += 1
        if self.count >= self.per_second:
            elapsed = time.time() - self.window
            if elapsed < 1:
                time.sleep(1 - elapsed)
            self.window = time.time()
            self.count = 0


def archive_bands(info, now):
    """Return (archive, from_time, until_time) bands, coarsest first.

    Each band is the slice of history for which that archive is the
    highest-resolution data available. Bands are disjoint, so no
    timestamp is emitted from two archives.
    """
    archives = sorted(info['archives'], key=lambda a: a['secondsPerPoint'])
    bands = []
    boundary = now
    for archive in archives:
        start = now - archive['retention']
        if start < boundary:
            bands.append((archive, start, boundary))
            boundary = start
    bands.reverse()
    return bands


def send_file(
    sender, filepath, metricpath, now, limit=None, limiter=None, dry_run=False
):
    """Replay one whisper file through the sender.

    Returns (points, first_ts, last_ts) for reporting.
    """
    try:
        info = whisper.info(filepath)
    except whisper.CorruptWhisperFile:
        logger.warning(f"Corrupt whisper file {filepath}")
        return (0, None, None)

    count = 0
    first_ts = None
    last_ts = None
    for archive, start, end in archive_bands(info, now):
        # Nudge from_time one step inside the band so whisper selects
        # this archive: fetch() picks the highest-resolution archive
        # whose retention covers the requested start.
        try:
            result = whisper.fetch(
                filepath,
                start + archive['secondsPerPoint'],
                untilTime=end,
                now=now,
            )
        except whisper.InvalidTimeInterval as e:
            logger.warning(f"Skipping band of {filepath}: {e}")
            continue
        if result is None:
            continue
        time_info, values = result
        for ts, value in zip(range(*time_info), values):
            if value is None:
                continue
            count += 1
            if first_ts is None:
                first_ts = ts
            last_ts = ts
            if not dry_run:
                sender.send_metric(metricpath, value, ts)
                if limiter:
                    limiter.wait()
            if limit and count >= limit:
                return (count, first_ts, last_ts)
    return (count, first_ts, last_ts)


def paths_in_directory(directory):
    directory = path.abspath(directory)
    for dirpath, dirnames, filenames in os.walk(directory):
        for filename in sorted(filenames):
            filepath = path.join(dirpath, filename)
            if not filename.endswith('.wsp'):
                logger.info(f"Skipping {filepath}")
                continue
            # convert /var/lib/graphite/server/metric.wsp to
            # server.metric
            metric_path = filepath[len(directory) + 1 :].replace('/', '.')[:-4]
            yield filepath, metric_path


def do_report(
    sender,
    filepaths,
    includes,
    now,
    limit=None,
    max_points_per_sec=None,
    dry_run=False,
):
    patterns = [glob_to_regex(include) for include in includes]
    limiter = None
    if max_points_per_sec:
        limiter = RateLimiter(max_points_per_sec)

    total_points = 0
    total_files = 0
    skipped_files = 0
    for filepath, metricpath in paths_in_directory(filepaths):
        if not any(pattern.match(metricpath) for pattern in patterns):
            skipped_files += 1
            logger.debug(f"Excluded by filters: {metricpath}")
            continue
        logger.info(f"Processing {filepath}")
        count, first_ts, last_ts = send_file(
            sender,
            filepath,
            metricpath,
            now,
            limit=limit,
            limiter=limiter,
            dry_run=dry_run,
        )
        ts_range = f" ({first_ts}..{last_ts})" if count else ""
        logger.info(f"{metricpath}: {count} points{ts_range}")
        total_files += 1
        total_points += count
    if not dry_run:
        sender.flush()
    prefix = "DRY RUN: would send " if dry_run else "Sent "
    logger.info(
        f"{prefix}{total_points} points from {total_files} files "
        f"({skipped_files} files excluded by filters)"
    )
    return (total_files, total_points)


def main():
    parser = Main('whisper')
    parser.add_argument(
        '--limit',
        default=None,
        type=int,
        help='Limit the number of points to send from each file.',
    )
    parser.add_argument(
        '--include',
        action='append',
        default=None,
        help='Graphite glob of metric paths to send (repeatable). '
        'Defaults to the status-page migration set.',
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Count points per metric without sending anything.',
    )
    parser.add_argument(
        '--max-points-per-sec',
        default=5000,
        type=int,
        help='Rate limit for sends; 0 disables the limit.',
    )
    parser.add_argument(
        '--now',
        default=None,
        type=int,
        help='Reference timestamp for archive band boundaries '
        '(default: current time). Reuse the same value when '
        'resuming an interrupted run.',
    )
    parser.add_argument(
        'path', type=str, help='The path to the whisper files to send.'
    )
    args = parser.parse_args()
    logger.info("Running Report")
    includes = args.include or DEFAULT_INCLUDES
    now = args.now or int(time.time())
    do_report(
        parser.sender(),
        args.path,
        includes,
        now,
        limit=args.limit,
        max_points_per_sec=args.max_points_per_sec,
        dry_run=args.dry_run,
    )
