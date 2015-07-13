import MySQLdb


def connection(host, db, user, password):
    return MySQLdb.connect(host=host,
                           user=user,
                           passwd=password,
                           db=db)
