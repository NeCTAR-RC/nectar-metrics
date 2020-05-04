import logging
from datetime import datetime, timedelta

from collections import defaultdict
try:
    from urlparse import urlsplit
except ImportError:
    from urllib.parse import urlsplit

from manukaclient import client as manuka_client

from nectar_metrics.cli import Main
from nectar_metrics import keystone


logger = logging.getLogger(__name__)


ODD_IDPS = {
    'urn:mace:federation.org.au:testfed:uq.edu.au':
    'idp.uq.edu.au',

    'urn:mace:federation.org.au:testfed:au-idp.adelaide.edu.au':
    'idp.adelaide.edu.au',

    'urn:mace:federation.org.au:testfed:mq.edu.au':
    'idp.mq.edu.au',

    'urn:mace:aaf.edu.au:idp:468d3d0153e23dda76af9397bddf20ca':
    'idp.des.qld.gov.au',
}


def list_users(client, time=datetime.now()):
    return client.users.list(registered_at__lt=time, state='created')


def count(sender, users, time):
    sender.send_global('users', 'total', len(users), time)


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
                logger.debug("Unknown IDP %s" % idp)
                continue
            else:
                logger.warning("Unknown IDP %s" % idp)

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
    parser = Main('rcshibboleth')
    parser.add_argument(
        '--from-date', default=datetime.now(), type=parse_date,
        help='When to backfill data from.')
    parser.add_argument(
        '--to-date', default=datetime.now(),
        help='When to backfill data to.')
    args = parser.parse_args()
    logger.info("Running Report")
    report_metrics(parser.sender(), args.from_date, args.to_date)
