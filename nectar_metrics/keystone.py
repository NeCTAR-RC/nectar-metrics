import os
import sys
import logging

from keystoneauth1.identity import v3
from keystoneauth1 import session
from keystoneclient.v3 import client as ks_client

from nectar_metrics.config import CONFIG

logger = logging.getLogger(__name__)


def get_auth_session():
    username = CONFIG.get('openstack', 'user')
    password = CONFIG.get('openstack', 'passwd')
    project_name = CONFIG.get('openstack', 'name')
    auth_url = CONFIG.get('openstack', 'url')

    auth = v3.Password(username=username,
                       password=password,
                       project_name=project_name,
                       auth_url=auth_url,
                       user_domain_id='default',
                       project_domain_id='default')
    return session.Session(auth=auth)


def client(username, password, tenant, auth_url):
    auth_session = get_auth_session()
    return ks_client.Client(session=auth_session)
