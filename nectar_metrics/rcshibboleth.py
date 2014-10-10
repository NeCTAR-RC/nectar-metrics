import logging
from datetime import datetime, timedelta
import pickle
from collections import defaultdict
from urlparse import urlsplit

import MySQLdb

from nectar_metrics import log
from nectar_metrics import config
from nectar_metrics.config import CONFIG
from nectar_metrics.graphite import (PickleSocketMetricSender,
                                     DummySender, SocketMetricSender)

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
                   " WHERE state = 'created' AND terms < '%s'" % time)
    while True:
        row = cursor.fetchone()
        if not row:
            break
        yield {'id': row[0], 'email': row[1],
               'attributes': pickle.loads(row[2])}


def count(sender, users, time):
    sender.send_metric('users.total', len(users), time)


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
        sender.send_metric('users.%s.total' % idp, len(users), time)


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
    from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter
    parser = ArgumentParser(formatter_class=ArgumentDefaultsHelpFormatter)
    parser.add_argument(
        '-v', '--verbose', action='count', default=0,
        help="Increase verbosity (specify multiple times for more)")
    parser.add_argument(
        '--protocol', choices=['debug', 'carbon', 'carbon_pickle'],
        required=True)
    parser.add_argument(
        '--carbon-host', help='Carbon Host.')
    parser.add_argument(
        '--carbon-port', default=2003, type=int,
        help='Carbon Port.')
    parser.add_argument(
        '--config', default=config.CONFIG_FILE, type=str,
        help='Config file path.')
    parser.add_argument(
        '--from-date', default=datetime.now(), type=parse_date,
        help='When to backfill data from.')
    parser.add_argument(
        '--to-date', default=datetime.now(),
        help='When to backfill data to.')
    args = parser.parse_args()
    config.read(args.config)

    log_level = 'WARNING'
    if args.verbose == 1:
        log_level = 'INFO'
    elif args.verbose >= 2:
        log_level = 'DEBUG'
    log.setup('rcshibboleth.log', 'INFO', log_level)

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
    report_metrics(sender, args.from_date, args.to_date)
