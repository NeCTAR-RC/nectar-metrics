from gnocchiclient import client

from nectar_metrics import keystone


GNOCCHI_API_VERSION = '1'


def get_client():
    auth = keystone.get_auth_session()
    return client.Client(GNOCCHI_API_VERSION, auth)
