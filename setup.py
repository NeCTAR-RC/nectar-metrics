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
    'console_scripts': [
        'nectar-metrics-nova = nectar_metrics.nova:main',
        'nectar-metrics-cinder = nectar_metrics.cinder:main',
        'nectar-metrics-rcshibboleth = nectar_metrics.rcshibboleth:main',
        'nectar-metrics-whisper = nectar_metrics.whisper:main',
    ],
    'ceilometer.poll.central': [
        'nectar.instances = nectar_metrics.ceilometer.compute.pollster:ComputePollster', # noqa
        'nectar.volumes = nectar_metrics.ceilometer.volume.cinder:CinderPollster', # noqa
        'nectar.cinder_pools = nectar_metrics.ceilometer.volume.cinder:CinderPoolPollster', # noqa
        'nectar.allocations.status = nectar_metrics.ceilometer.allocation.pollster:AllocationStatusPollster', # noqa
        'nectar.allocations.novaquota = nectar_metrics.ceilometer.allocation.pollster:NovaQuotaAllocationPollster', # noqa
        'nectar.allocations.cinderquota = nectar_metrics.ceilometer.allocation.pollster:CinderQuotaAllocationPollster', # noqa
        'nectar.allocations.swiftquota = nectar_metrics.ceilometer.allocation.pollster:SwiftQuotaAllocationPollster', # noqa
        'nectar.resource_providers = nectar_metrics.ceilometer.placement.pollster:ResourceProviderPollster', # noqa
        'nectar.container_infra = nectar_metrics.ceilometer.container_infra.pollster:MagnumClusterPollster', # noqa
        'nectar.application_catalog = nectar_metrics.ceilometer.application_catalog.pollster:MuranoEnvironmentPollster',  # noqa
        'nectar.network_ip_availability = nectar_metrics.ceilometer.network.pollster:NetworkIPAvailabilityPollster', # noqa
    ],
    'ceilometer.builder.poll.central': [
        'f5_virtualservers = nectar_metrics.ceilometer.f5.pollster:F5VirtualServerPollster', # noqa
    ],
    'ceilometer.poll.objectstore': [
        'nectar.swift = nectar_metrics.ceilometer.objectstore.swift:SwiftDiskPollster', # noqa
    ],
    'ceilometer.discover.objectstore': [
        'swift_disks = nectar_metrics.ceilometer.objectstore.discovery:SwiftDiskDiscovery', # noqa
    ],
    'ceilometer.discover.central': [
        'all_allocations = nectar_metrics.ceilometer.allocation.discovery:AllocationDiscovery', # noqa
        'all_instances = nectar_metrics.ceilometer.compute.discovery:InstanceAllDiscovery', # noqa
        'cinder_pools = nectar_metrics.ceilometer.volume.discovery:PoolDiscovery', # noqa
        'resource_providers = nectar_metrics.ceilometer.placement.discovery:ResourceProviderDiscovery', # noqa
        'f5_loadbalancers = nectar_metrics.ceilometer.f5.discovery:F5Discovery', # noqa
        'container_infra = nectar_metrics.ceilometer.container_infra.discovery:MagnumClusterDiscovery', # noqa
        'application_catalog = nectar_metrics.ceilometer.application_catalog.discovery:MuranoEnvironmentDiscovery',  # noqa
        'network_ip_availability = nectar_metrics.ceilometer.network.discovery:NetworkIPAvailabilityDiscovery', # noqa
    ],
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
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)', # noqa
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
