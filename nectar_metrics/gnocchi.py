from gnocchiclient import client
from gnocchiclient import exceptions as gnocchi_exceptions

from nectar_metrics import keystone


GNOCCHI_API_VERSION = '1'
exceptions = gnocchi_exceptions


def get_client():
    auth = keystone.get_auth_session()
    return client.Client(GNOCCHI_API_VERSION, auth)
