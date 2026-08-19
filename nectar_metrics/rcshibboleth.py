from datetime import datetime, timedelta

from collections import defaultdict

try:
    from urlparse import urlsplit
except ImportError:
    from urllib.parse import urlsplit

from manukaclient import client as manuka_client
from oslo_config import cfg
from oslo_log import log as logging

from nectar_metrics.cli import Main
from nectar_metrics import config
from nectar_metrics import keystone
from nectar_metrics import retry


CONF = config.CONF
logger = logging.getLogger(__name__)


ODD_IDPS = {
    'urn:mace:federation.org.au:testfed:uq.edu.au': 'idp.uq.edu.au',
    'urn:mace:federation.org.au:testfed:au-idp.adelaide.edu.au': 'idp.adelaide.edu.au',
    'urn:mace:federation.org.au:testfed:mq.edu.au': 'idp.mq.edu.au',
    'urn:mace:aaf.edu.au:idp:468d3d0153e23dda76af9397bddf20ca': 'idp.des.qld.gov.au',
}


@retry.retry_on_transient()
def list_users(client, time=datetime.now()):
    return client.users.list(registered_at__lt=time, state='created')


def count(sender, users, time):
    sender.send_global('users.total', len(users), time)


def by_idp(sender, users, time):
    users_by_idp = defaultdict(list)
    for user in users:
        for eid in user.external_ids:
            idp = eid.idp
            url = urlsplit(idp)
            if url.netloc:
                users_by_idp[url.netloc.replace('.', '_')].append(user)
            elif idp in ODD_IDPS:
                users_by_idp[ODD_IDPS[idp].replace('.', '_')].append(user)
            elif idp == 'idp.fake.nectar.org.au':
                logger.debug(f"Unknown IDP {idp}")
                continue
            else:
                logger.warning(f"Unknown IDP {idp}")

    for idp, users in users_by_idp.items():
        sender.send_by_idp(idp, 'total', len(users), time)


def report_metrics(sender, from_time, to_time):
    session = keystone.get_auth_session()
    client = manuka_client.Client('1', session=session)
    while from_time < to_time:
        now = int(from_time.strftime("%s"))
        users = list(list_users(client, from_time))
        count(sender, users, now)
        by_idp(sender, users, now)
        from_time = from_time + timedelta(hours=1)
    sender.flush()


def parse_date(datestring):
    return datetime.strptime(datestring, '%Y-%m-%d')


def main():
    metrics_cli = Main(
        'rcshibboleth',
        [
            cfg.Opt(
                'from-date',
                type=parse_date,
                help='When to backfill data from (YYYY-MM-DD).',
            ),
            cfg.Opt(
                'to-date',
                type=parse_date,
                help='When to backfill data to (YYYY-MM-DD).',
            ),
        ],
    )
    logger.info("Running Report")
    # With no dates given, report a single iteration at the current time.
    now = datetime.now()
    from_time = CONF.from_date or now
    to_time = CONF.to_date or now + timedelta(seconds=1)
    report_metrics(metrics_cli.sender(), from_time, to_time)
