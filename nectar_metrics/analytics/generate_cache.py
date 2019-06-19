# Quick and dirty script to dump outputs for time-intensive openstack commands
# to pickle and json. This is primarily used to generate a cache for Jupyter
# notebooks to work on, so we don't have to grab data on each run of a notebook

import argparse
from openstack import connection
import pandas as pd

from gnocchiclient.v1 import client

from nectar_metrics import config
from nectar_metrics.config import CONFIG
from nectar_metrics import keystone

config.read(config.CONFIG_FILE)
SESSION = keystone.get_auth_session()


# INSTANCES
def generate_gnocchi_instances(upload_swift=False):
    gnocchi = client.Client(session=SESSION)
    json = gnocchi.resource.list(resource_type='instance')
    while (True):
        j = gnocchi.resource.list(resource_type='instance',
                                  marker=json[-1].get('id'))
        if len(j) == 0:
            break
        json += j
        # print("%s (%s)" % (json[-1].get('id'), len(json)))

    df = pd.DataFrame(json)
    df.to_pickle('gnocchi_instance_list_instance.pkl')

    # Create distributable files
    g = df.drop(['created_by_project_id', 'created_by_user_id', 'creator',
                 'host', 'metrics', 'original_resource_id', 'display_name',
                 'revision_start', 'revision_end'],
                axis=1)
    g.to_pickle('gnocchi_instance_list_restricted.pkl')
    print("Generated gnocchi_instance_list_restricted.pkl")
    g.to_json('gnocchi_instance_list_restricted.json')
    print("Generated gnocchi_instance_list_restricted.json")

    if upload_swift:
        _upload_swift(filename='gnocchi_instance_list_restricted.pkl')
        print("Uploaded gnocchi_instance_list_restricted.pkl")
        _upload_swift(filename='gnocchi_instance_list_restricted.json')
        print("Uploaded gnocchi_instance_list_restricted.json")


# IMAGES
def generate_openstack_image_list(upload_swift=False):
    conn = connection.Connection(session=SESSION)

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

    if upload_swift:
        _upload_swift(filename='openstack_image_list_restricted.pkl')
        print("Uploaded openstack_image_list_restricted.pkl")
        _upload_swift(filename='openstack_image_list_restricted.json')
        print("Uploaded openstack_image_list_restricted.json")


# Upload to swift
def _upload_swift(project=None, container='analytics-data', filename=None):
    if not project:
        project = CONFIG['openstack']['name']

    conn = connection.Connection(session=SESSION)

    if filename:
        conn.create_object(container, filename, filename)


def main():

    parser = argparse.ArgumentParser(
        description="Generates pickle and json cache files from "
                    "OpenStack services.")

    parser.add_argument(
        '--gnocchi-instances', help='Generate instances cache from gnocchi.',
        action='store_true')
    parser.add_argument(
        '--images', help='Generate images cache from glance.',
        action='store_true')
    parser.add_argument(
        '--upload-swift', help='Uploads caches to swift.',
        action='store_true')

    args = parser.parse_args()

    if args.gnocchi_instances:
        generate_gnocchi_instances(upload_swift=args.upload_swift)

    if args.images:
        generate_openstack_image_list(upload_swift=args.upload_swift)
