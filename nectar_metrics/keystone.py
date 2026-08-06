from keystoneauth1 import loading as ks_loading
from keystoneclient.v3 import client as ks_client
import openstack

from nectar_metrics import config


CONF = config.CONF


def get_auth_session():
    """Return a keystoneauth session.

    Uses the [service_auth] config section when auth_type is set
    there, otherwise falls back to OS_* environment variables or
    clouds.yaml via openstacksdk.
    """
    if CONF[config.SERVICE_AUTH_GROUP].auth_type:
        auth = ks_loading.load_auth_from_conf_options(
            CONF, config.SERVICE_AUTH_GROUP
        )
        return ks_loading.load_session_from_conf_options(
            CONF, config.SERVICE_AUTH_GROUP, auth=auth
        )
    conn = openstack.connect()
    return conn.session


def client():
    auth_session = get_auth_session()
    return ks_client.Client(session=auth_session)
