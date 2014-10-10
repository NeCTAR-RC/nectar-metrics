import os
import sys
import logging

from keystoneclient.v2_0 import client as keystone_client

logger = logging.getLogger(__name__)


def client(username, password, tenant, auth_url):
    auth_url = os.environ.get('OS_AUTH_URL', auth_url)
    username = os.environ.get('OS_USERNAME', username)
    password = os.environ.get('OS_PASSWORD', password)
    tenant = os.environ.get('OS_TENANT_NAME', tenant)
    try:
        return keystone_client.Client(username=username,
                                      password=password,
                                      tenant_name=tenant,
                                      auth_url=auth_url)
    except Exception as exception:
        logger.exception(exception)
        sys.exit()
