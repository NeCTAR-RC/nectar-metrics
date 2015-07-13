import logging
import datetime
from time import mktime

from nectar_metrics.config import CONFIG
from nectar_metrics.cli import Main
from nectar_metrics.db import connection as db_connection

logger = logging.getLogger(__name__)
flavor = {}


def list_faults(db, from_date, to_date):
    cursor = db.cursor()
    cursor.execute("SELECT cell_name, count(*) AS errors FROM instance_faults "
                   "INNER JOIN instances ON (instance_uuid = instances.uuid) "
                   "WHERE instance_faults.created_at BETWEEN '%s'"
                   "AND '%s' GROUP BY cell_name" % (from_date, to_date))

    while True:
        row = cursor.fetchone()
        if not row:
            break
        yield {'cell': row[0], 'count': row[1]}

CELL_MAPPINGS = {
    'nectar!intersect-01': 'intersect-01',
    'nectar!intersect-02': 'intersect-02',
    'nectar!melbourne!np': 'melbourne-np',
    'nectar!melbourne!qh2': 'melbourne-qh2',
    'nectar!NCI': 'NCI',
    'nectar!qh2-uom': 'melbourne-qh2-uom',
    'nectar!qld': 'qld',
    'nectar!qld-upstart': 'QRIScloud',
    'nectar!tas!tas-m': 'tasmania',
    'nectar!pawsey-01': 'pawsey-01',
    'nectar!monash!monash-01': 'monash-01',
    'nectar!monash!monash-02': 'monash-02',
    'nectar!sa-cw': 'sa',
}


def do_faults(sender, db):
    metric = 'instance_faults'
    current_time = datetime.datetime.now()
    current_time -= datetime.timedelta(minutes=current_time.minute,
                                       seconds=current_time.second,
                                       microseconds=current_time.microsecond)

    # Query last 24 hours of faults.
    date = current_time - datetime.timedelta(days=1)
    while date < datetime.datetime.now():
        end = date + datetime.timedelta(hours=1)
        middle = date + datetime.timedelta(minutes=30)
        faults = list_faults(db, date, end)
        now = int(mktime(middle.timetuple()))
        mappings = CELL_MAPPINGS.copy()
        for f in faults:
            try:
                zone = CELL_MAPPINGS[f['cell']]
                mappings.pop(f['cell'])
                value = f['count']
                sender.send_by_az(zone, metric, value, now)
            except KeyError:
                continue
        for cell, zone in mappings.items():
            sender.send_by_az(zone, metric, 0, now)
        date = end


def do_report(sender):
    username = CONFIG.get('nova_db', 'username')
    password = CONFIG.get('nova_db', 'password')
    host = CONFIG.get('nova_db', 'host')
    database = CONFIG.get('nova_db', 'database')
    db = db_connection(host, database, username, password)
    do_faults(sender, db)
    sender.flush()


def main():
    parser = Main('nova')
    args = parser.parse_args()
    logger.info("Running Report")
    do_report(parser.sender())
