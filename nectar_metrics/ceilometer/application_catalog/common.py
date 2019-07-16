from ceilometer import keystone_client

from muranoclient import client


def murano_client(conf):
    creds = conf.service_credentials
    mclient = client.Client(
        version='1',
        session=keystone_client.get_session(conf),
        region_name=creds.region_name,
        service_type='application-catalog',
    )
    return mclient
