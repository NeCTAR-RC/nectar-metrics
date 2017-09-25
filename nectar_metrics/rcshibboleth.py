import logging
from datetime import datetime, timedelta
import pickle
from collections import defaultdict
from urlparse import urlsplit

import MySQLdb

from nectar_metrics.config import CONFIG
from nectar_metrics.cli import Main

logger = logging.getLogger(__name__)


ODD_IDPS = {
    'urn:mace:federation.org.au:testfed:uq.edu.au':
    'idp.uq.edu.au',

    'urn:mace:federation.org.au:testfed:au-idp.adelaide.edu.au':
    'idp.adelaide.edu.au',

    'urn:mace:federation.org.au:testfed:mq.edu.au':
    'idp.mq.edu.au',
}


def connection(host, db, user, password):
    return MySQLdb.connect(host=host,
                           user=user,
                           passwd=password,
                           db=db)


def list_users(db, time=datetime.now()):
    cursor = db.cursor()
    cursor.execute("SELECT user_id, email, shibboleth_attributes FROM user"
                   " WHERE state = 'created' AND registered_at < '%s'" % time)
    while True:
        row = cursor.fetchone()
        if not row:
            break
        yield {'id': row[0], 'email': row[1],
               'attributes': pickle.loads(row[2])}


def count(sender, users, time):
    sender.send_global('users', 'total', len(users), time)


def by_idp(sender, users, time):
    users_by_idp = defaultdict(list)
    for user in users:
        idp = user['attributes']['idp']
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
    username = CONFIG.get('rcshibboleth', 'username')
    password = CONFIG.get('rcshibboleth', 'password')
    host = CONFIG.get('rcshibboleth', 'host')
    database = CONFIG.get('rcshibboleth', 'database')
    db = connection(host, database, username, password)
    while from_time < to_time:
        now = int(from_time.strftime("%s"))
        users = list(list_users(db, from_time))
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
