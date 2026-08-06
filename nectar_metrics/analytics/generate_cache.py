# Quick and dirty script to dump outputs for time-intensive openstack commands
# to pickle and json. This is primarily used to generate a cache for Jupyter
# notebooks to work on, so we don't have to grab data on each run of a notebook

from openstack import connection
import pandas as pd

from gnocchiclient.v1 import client
from oslo_config import cfg
from oslo_log import log as logging

from nectar_metrics import config
from nectar_metrics import keystone
from nectar_metrics import sentry

CONF = config.CONF

cli_opts = [
    cfg.BoolOpt(
        'instances',
        default=False,
        help='Generate instances cache from gnocchi.',
    ),
    cfg.BoolOpt(
        'glance-images',
        default=False,
        help='Generate images cache from glance.',
    ),
    cfg.BoolOpt(
        'upload-swift',
        default=False,
        help='Uploads caches to swift.',
    ),
]

SESSION = None
VERSION = 1


# INSTANCES
def generate_gnocchi_instances(upload_swift=False):
    gnocchi = client.Client(session=SESSION)
    json = gnocchi.resource.list(resource_type='instance')
    while True:
        j = gnocchi.resource.list(
            resource_type='instance', marker=json[-1].get('id')
        )
        if len(j) == 0:
            break
        json += j
        # print("%s (%s)" % (json[-1].get('id'), len(json)))

    df = pd.DataFrame(json)
    df.to_pickle('gnocchi_instance_list_instance.pkl')

    # Create distributable files
    g = df.drop(
        [
            'created_by_project_id',
            'created_by_user_id',
            'creator',
            'host',
            'metrics',
            'original_resource_id',
            'display_name',
            'revision_start',
            'revision_end',
        ],
        axis=1,
    )
    filenames = _dump_file(g, "gnocchi_instance_list_restricted")

    if upload_swift:
        for filename in filenames:
            _upload_swift(filename=filename)


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
    filenames = _dump_file(c, "openstack_image_list_restricted")

    if upload_swift:
        for filename in filenames:
            _upload_swift(filename=filename)


# Dump file to disk.
# Returns a list of filenames written
def _dump_file(dataframe, filename, pickle=True, json=True, version=VERSION):
    filename = f"v{VERSION}_{filename}"
    p_filename = filename + '.pkl'
    j_filename = filename + '.json'
    dataframe.to_pickle(p_filename)
    print(f"Generated {p_filename}")
    dataframe.to_json(j_filename)
    print(f"Generated {j_filename}")

    return (p_filename, j_filename)


# Upload to swift
def _upload_swift(project=None, container='analytics-data', filename=None):
    if not project:
        project = CONF.openstack.name

    conn = connection.Connection(session=SESSION)

    if filename:
        conn.create_object(container, filename, filename)
        print(f"Uploaded {filename}")


def main():
    global SESSION

    logging.register_options(CONF)
    CONF.register_cli_opts(cli_opts)
    config.init(prog='analytics-generate-cache')
    logging.setup(CONF, 'nectar_metrics')
    sentry.setup()
    SESSION = keystone.get_auth_session()

    if CONF.instances:
        generate_gnocchi_instances(upload_swift=CONF.upload_swift)

    if CONF.glance_images:
        generate_openstack_image_list(upload_swift=CONF.upload_swift)
