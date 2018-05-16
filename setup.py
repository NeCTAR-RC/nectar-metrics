#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages
import uuid

try:  # for pip >= 10
    from pip._internal.req import parse_requirements
except ImportError:  # for pip <= 9.0.3
    from pip.req import parse_requirements


readme = open('README.rst').read()
history = open('HISTORY.rst').read().replace('.. :changelog:', '')
requirements = parse_requirements("requirements.txt", session=uuid.uuid1())

entry_points = {
    'console_scripts':
    ['nectar-metrics-nova = nectar_metrics.nova:main',
     'nectar-metrics-cinder = nectar_metrics.cinder:main',
     'nectar-metrics-rcshibboleth = nectar_metrics.rcshibboleth:main',
     'nectar-metrics-whisper = nectar_metrics.whisper:main'],
    'ceilometer.poll.central':
    ['nectar.volumes = nectar_metrics.ceilometer.volume.cinder:CinderPollster',
     'nectar.cinder_pools = nectar_metrics.ceilometer.volume.cinder:CinderPoolPollster', # noqa
     'nectar.allocations = nectar_metrics.ceilometer.allocation.pollster:AllocationPollster'], # noqa
    'ceilometer.poll.objectstore':
    ['nectar.swift = nectar_metrics.ceilometer.objectstore.swift:SwiftDiskPollster'], # noqa
    'ceilometer.discover.objectstore':
    ['swift_disks = nectar_metrics.ceilometer.objectstore.discovery:SwiftDiskDiscovery'], # noqa
    'ceilometer.discover.central':
    ['all_allocations = nectar_metrics.ceilometer.allocation.discovery:AllocationDiscovery', # noqa
     'cinder_pools = nectar_metrics.ceilometer.volume.discovery:PoolDiscovery'], # noqa
}

setup(
    name='nectar-metrics',
    version='0.2.0',
    description='Metrics collection for the NeCTAR Research Cloud.',
    long_description=readme + '\n\n' + history,
    author='Russell Sim',
    author_email='russell.sim@gmail.com',
    url='https://github.com/NeCTAR-RC/nectar-metrics',
    packages=find_packages(exclude=['tests', 'local']),
    package_dir={'nectar_metrics': 'nectar_metrics'},
    include_package_data=True,
    install_requires=[str(r.req) for r in requirements],

    license="GPLv3+",
    zip_safe=False,
    keywords='nectar-metrics',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Natural Language :: English',
        "Programming Language :: Python :: 2",
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],
    entry_points=entry_points,
)
