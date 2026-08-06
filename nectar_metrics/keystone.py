from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneclient.v3 import client as ks_client

from nectar_metrics import config


CONF = config.CONF


def get_auth_session():
    auth = v3.Password(
        username=CONF.openstack.user,
        password=CONF.openstack.passwd,
        project_name=CONF.openstack.name,
        auth_url=CONF.openstack.url,
        user_domain_id='default',
        project_domain_id='default',
    )
    return session.Session(auth=auth)


def client():
    auth_session = get_auth_session()
    return ks_client.Client(session=auth_session)
