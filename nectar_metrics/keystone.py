from keystoneclient.v2_0 import client as keystone_client


def client(username, key, tenant_id, auth_url):
    return keystone_client.Client(username=username,
                                  password=key,
                                  tenant_name=tenant_id,
                                  auth_url=auth_url)
