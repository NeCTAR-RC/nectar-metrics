import json

import requests
from requests import adapters
from urllib3.util.retry import Retry

from nectar_metrics import config
from nectar_metrics import naming
from nectar_metrics.senders import base


CONF = config.CONFIG

# Flush automatically once this many datapoints are buffered so the
# whisper backfill (hundreds of millions of points) keeps memory
# bounded.
FLUSH_AT = 50000


class VictoriaMetricsSender(base.BaseSender):
    """Sends metrics to the VictoriaMetrics JSON line import API.

    Dotted metric paths composed by the BaseSender helpers (and by the
    whisper backfill tool) are mapped to Prometheus-style names and
    labels via nectar_metrics.naming; paths outside the migrated set
    are dropped. Values keep full float precision and timestamps are
    sent in milliseconds, so live writes and backfilled history are
    byte-identical on the wire.
    """

    def __init__(self, url=None):
        super().__init__()
        url = url or CONF.get('victoria', 'url')
        if not url:
            raise ValueError(
                "VictoriaMetrics URL not set; add [victoria] url to the "
                "config file or pass --victoria-url"
            )
        self.url = url.rstrip('/')
        self.session = self._build_session()
        # (name, sorted label items) -> ([timestamps_ms], [values])
        self.buffered = {}
        self.buffered_count = 0
        self.sent = 0
        self.dropped = 0

    def _build_session(self):
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=(500, 502, 503, 504),
            allowed_methods=frozenset(['POST']),
        )
        adapter = adapters.HTTPAdapter(max_retries=retries)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def send_metric(self, metric, value, now):
        mapped = naming.from_dotted_path(metric)
        if mapped is None:
            self.dropped += 1
            self.log.debug("Dropping unmigrated metric %s", metric)
            return None
        name, labels = mapped
        key = (name, tuple(sorted(labels.items())))
        if key not in self.buffered:
            self.buffered[key] = ([], [])
        timestamps, values = self.buffered[key]
        timestamps.append(int(now) * 1000)
        values.append(float(value))
        self.buffered_count += 1
        if self.buffered_count >= FLUSH_AT:
            self.flush()
        return (name, labels, float(value), int(now))

    def flush(self):
        if not self.buffered:
            return
        lines = []
        for (name, labels), (timestamps, values) in self.buffered.items():
            series = {'__name__': name}
            series.update(dict(labels))
            lines.append(
                json.dumps(
                    {
                        'metric': series,
                        'values': values,
                        'timestamps': timestamps,
                    }
                )
            )
        response = self.session.post(
            f'{self.url}/api/v1/import',
            data='\n'.join(lines).encode('utf-8'),
            timeout=(5, 60),
        )
        # Raise on persistent failure (after retries on 5xx) so a cron
        # run fails visibly instead of silently losing datapoints.
        response.raise_for_status()
        self.sent += self.buffered_count
        self.log.debug(
            "Sent %d datapoints in %d series", self.buffered_count, len(lines)
        )
        self.buffered = {}
        self.buffered_count = 0
