"""Replay historical site and host datapoints from Gnocchi.

The sites.* and hosts.* metric families have the GnocchiSender as
their only long-term store. This tool reads their measure history
straight from Gnocchi and replays it through a sender, composing the
same dotted metric paths the collectors do, so the resulting series
are identical to live writes.

Two Gnocchi resource types are read:

- site resources: metrics named
  {capacity,usage,availability}.{scope}.{vcpu|memory|disk} become
  sites.{site}.{metric} paths.
- resource_provider resources: the
  resource_provider.usage.{home}.{vcpu|memory|disk} metrics written
  by the GnocchiSender become hosts.{host}.{home}.used_* paths.
  Ended resources are included: earlier incarnations of a hypervisor
  hold older history. Metrics written by the ceilometer placement
  pollster (capacity, unscoped usage totals) are skipped.

Where a timestamp is covered by more than one archive-policy
granularity, the finest granularity wins.

Re-runs are safe: identical (series, timestamp, value) points are
deduplicated by VictoriaMetrics.
"""

from datetime import datetime
import time

from oslo_config import cfg
from oslo_log import log as logging

from nectar_metrics.cli import Main
from nectar_metrics import config
from nectar_metrics import gnocchi

CONF = config.CONF
logger = logging.getLogger(__name__)


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


AGGREGATION = 'mean'

SITE_RESOURCES = ('vcpu', 'memory', 'disk')
SITE_KINDS = ('capacity', 'usage', 'availability')

# Reverse of the GnocchiSender metric name mangling
# (metric.replace('used_', '').rstrip('s')).
RES_TO_USED = {
    'vcpu': 'used_vcpus',
    'memory': 'used_memory',
    'disk': 'used_disk',
}

RP_USAGE_PREFIX = 'resource_provider.usage.'


def finest_points(measures):
    """Reduce gnocchi measures to {epoch: value}, finest wins.

    measures are (timestamp, granularity, value) triples; where a
    timestamp appears at several granularities, the value from the
    finest (smallest) granularity is kept.
    """
    points = {}
    for ts, granularity, value in measures:
        if isinstance(ts, str):
            ts = datetime.fromisoformat(ts)
        epoch = int(ts.timestamp())
        best = points.get(epoch)
        if best is None or granularity < best[0]:
            points[epoch] = (granularity, value)
    return {ts: value for ts, (_, value) in points.items()}


def site_paths(resource):
    """Yield (dotted_path, metric_id) for a site resource."""
    site = resource['name']
    for metric_name, metric_id in sorted(resource['metrics'].items()):
        parts = metric_name.split('.')
        if (
            len(parts) == 3
            and parts[0] in SITE_KINDS
            and parts[2] in SITE_RESOURCES
        ):
            yield f'sites.{site}.{metric_name}', metric_id
        else:
            logger.debug("Skipping site metric %s on %s", metric_name, site)


def host_paths(resource):
    """Yield (dotted_path, metric_id) for a resource_provider.

    The hostname is flattened the same way BaseSender flattens it
    for the dotted path, so backfilled and live series carry an
    identical host label.
    """
    host = resource['name'].replace('.', '_').replace('-', '_')
    for metric_name, metric_id in sorted(resource['metrics'].items()):
        if not metric_name.startswith(RP_USAGE_PREFIX):
            logger.debug(
                "Skipping resource_provider metric %s on %s",
                metric_name,
                resource['name'],
            )
            continue
        remainder = metric_name[len(RP_USAGE_PREFIX) :].split('.')
        # home is one or two segments, e.g. PT or national.monash;
        # a bare resource (no home) is a ceilometer total.
        if len(remainder) < 2 or remainder[-1] not in RES_TO_USED:
            logger.debug(
                "Skipping resource_provider metric %s on %s",
                metric_name,
                resource['name'],
            )
            continue
        home = '.'.join(remainder[:-1])
        used = RES_TO_USED[remainder[-1]]
        yield f'hosts.{host}.{home}.{used}', metric_id


def replay_metric(
    sender, client, path, metric_id, limit=None, limiter=None, dry_run=False
):
    """Replay one gnocchi metric through the sender.

    Returns the number of points sent (or counted, for a dry run).
    """
    try:
        measures = client.metric.get_measures(
            metric=metric_id, aggregation=AGGREGATION
        )
    except gnocchi.exceptions.ClientException as e:
        logger.warning("Skipping metric %s (%s): %s", path, metric_id, e)
        return 0

    points = finest_points(measures)
    count = 0
    for ts in sorted(points):
        count += 1
        if not dry_run:
            sender.send_metric(path, points[ts], ts)
            if limiter:
                limiter.wait()
        if limit and count >= limit:
            break
    logger.info("%s: %s points", path, count)
    return count


def do_report(
    sender, client, limit=None, max_points_per_sec=None, dry_run=False
):
    limiter = None
    if max_points_per_sec:
        limiter = RateLimiter(max_points_per_sec)

    total_points = 0
    total_metrics = 0
    for resource_type, paths in (
        ('site', site_paths),
        ('resource_provider', host_paths),
    ):
        for resource in client.resource.list(resource_type=resource_type):
            for path, metric_id in paths(resource):
                total_points += replay_metric(
                    sender,
                    client,
                    path,
                    metric_id,
                    limit=limit,
                    limiter=limiter,
                    dry_run=dry_run,
                )
                total_metrics += 1
    if not dry_run:
        sender.flush()
    prefix = "DRY RUN: would send " if dry_run else "Sent "
    logger.info(f"{prefix}{total_points} points from {total_metrics} metrics")
    return (total_metrics, total_points)


def main():
    metrics_cli = Main(
        'gnocchi_backfill',
        [
            cfg.IntOpt(
                'limit',
                help='Limit the number of points to send from each metric.',
            ),
            cfg.BoolOpt(
                'dry-run',
                default=False,
                help='Count points per metric without sending anything.',
            ),
            cfg.IntOpt(
                'max-points-per-sec',
                default=5000,
                help='Rate limit for sends; 0 disables the limit.',
            ),
        ],
    )
    logger.info("Running Report")
    do_report(
        metrics_cli.sender(),
        gnocchi.get_client(),
        limit=CONF.limit,
        max_points_per_sec=CONF.max_points_per_sec,
        dry_run=CONF.dry_run,
    )
