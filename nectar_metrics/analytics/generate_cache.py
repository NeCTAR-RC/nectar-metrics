import argparse
import logging
import numpy as np
from openstack import connection
import pandas as pd

from gnocchiclient.v1 import client

from nectar_metrics import config
from nectar_metrics import keystone


config.read(config.CONFIG_FILE)
session = keystone.get_auth_session()

# INSTANCES
def generate_gnocchi_instances():
    gnocchi = client.Client(session=session)
    json = gnocchi.resource.list(resource_type='instance')
    while (True):
        j = gnocchi.resource.list(resource_type='instance', marker=json[-1].get('id'))
        if len(j) == 0:
            break
        json += j
        #print("%s (%s)" % (json[-1].get('id'), len(json)))

    df = pd.DataFrame(json)
    df.to_pickle('gnocchi_resource_list_instance.pkl')

    # Create distributable files
    g = df.drop(['created_by_project_id','created_by_user_id','creator',
                 'host','metrics','original_resource_id','display_name',
                 'revision_start','revision_end'], 
                axis=1)
    g.to_pickle('gnocchi_resource_list_restricted.pkl')
    print("Generated gnocchi_resource_list_restricted.pkl")
    g.to_json('gnocchi_resource_list_restricted.json')
    print("Generated gnocchi_resource_list_restricted.json")


# IMAGES
def generate_openstack_image_list():
    conn = connection.Connection(session=session)

    images = pd.DataFrame(conn.image.images())
    community = pd.DataFrame(conn.image.images(visibility='community'))

    images.to_pickle('openstack_image_list.pkl')
    community.to_pickle('openstack_image_list_community.pkl')

    # Create distributable files
    a = images[['id', 'name']]
    b = community[['id', 'name']]
    c = pd.merge(a, b, how='outer')
    c.to_pickle('openstack_image_list_restricted.pkl')
    print("Generated openstack_image_list_restricted.pkl")
    c.to_json('openstack_image_list_restricted.json')
    print("Generated openstack_image_list_restricted.json")


def main():
    parser = argparse.ArgumentParser(
                description="Generates pickle and json cache files from "
                            "OpenStack services.")

    parser.add_argument(
        '--gnocchi-instances', help='Generate instances cache from gnocchi.', action='store_true')
    parser.add_argument(
        '--images', help='Generate images cache from glance.', action='store_true')

    args = parser.parse_args()

    if args.gnocchi_instances:
        generate_gnocchi_instances()

    if args.images:
        generate_openstack_image_list()
