===============================
nectar-metrics
===============================

Metrics collection for the NeCTAR Research Cloud.

* License: GPLv3+ license

Manual Testing
--------------

After setting up a metrics.ini and running nectar-nova-metrics using a
small selection of servers::

   $ nectar-metrics-nova --protocol debug --limit 10

   tenant.2b238c7f0f1348dcba1250841c07bc2b.total_instances 1.00 1415353638
   tenant.2b238c7f0f1348dcba1250841c07bc2b.used_memory 65536.00 1415353638
   tenant.2b238c7f0f1348dcba1250841c07bc2b.used_vcpus 16.00 1415353638
   az.monash-01.total_instances 1.00 1415353638
   az.monash-01.used_memory 65536.00 1415353638
   az.monash-01.used_vcpus 16.00 1415353638
   az.monash-01.used_disk 10.00 1415353638
   az.monash-01.tenant.2b238c7f0f1348dcba1250841c07bc2b.total_instances 1.00 1415353638
   az.monash-01.tenant.2b238c7f0f1348dcba1250841c07bc2b.used_memory 65536.00 1415353638
   az.monash-01.tenant.2b238c7f0f1348dcba1250841c07bc2b.used_vcpus 16.00 1415353638
   az.monash-01.domain.anu_edu_au.used_vcpus 16.00 1415353638
   az.monash-01.instances_deleted 0.00 1415353638
   az.monash-01.instances_created 0.00 1415353638


Common options
--------------

All the collector commands take the following options:

--protocol PROTOCOL
   Sender used to report the metrics (required); one of ``debug``,
   ``gnocchi``, ``victoria`` or ``gnocchi_victoria``.
--victoria-url URL
   VictoriaMetrics base URL (default: [victoria] url from the config
   file).

They also accept the standard ``oslo.config`` and ``oslo.log``
options, e.g. ``--config-file``, ``--debug``, ``--log-file`` and
``--log-dir``; see ``--help`` for the full list. Without
``--config-file`` the config is read from ``/etc/nectar/metrics.ini``,
falling back to a ``metrics.ini`` in the current directory.

Nova
----

Nova metrics::

   $ nectar-metrics-nova --help
   usage: nectar-metrics-nova [-h] [--config-file PATH] [--debug]
                              [--protocol PROTOCOL]
                              [--victoria-url VICTORIA_URL] [--limit LIMIT]
                              ...

   options:
     --limit LIMIT         Limit the response to some servers only.

Nova output is grouped in several ways: by tenant, by cell, by cell by
tenant and by cell by email domain of the user who launched the
hosts.::

   $ nectar-metrics-nova --protocol debug --limit 1
   tenant.2b238c7f0f1348dcba1250841c07bc2b.total_instances 1.00 1415353638
   tenant.2b238c7f0f1348dcba1250841c07bc2b.used_memory 65536.00 1415353638
   tenant.2b238c7f0f1348dcba1250841c07bc2b.used_vcpus 16.00 1415353638
   az.monash-01.total_instances 1.00 1415353638
   az.monash-01.used_memory 65536.00 1415353638
   az.monash-01.used_vcpus 16.00 1415353638
   az.monash-01.used_disk 10.00 1415353638
   az.monash-01.tenant.2b238c7f0f1348dcba1250841c07bc2b.total_instances 1.00 1415353638
   az.monash-01.tenant.2b238c7f0f1348dcba1250841c07bc2b.used_memory 65536.00 1415353638
   az.monash-01.tenant.2b238c7f0f1348dcba1250841c07bc2b.used_vcpus 16.00 1415353638
   az.monash-01.domain.anu_edu_au.used_vcpus 16.00 1415353638
   az.monash-01.instances_deleted 0.00 1415353638
   az.monash-01.instances_created 0.00 1415353638

Cinder
------

Cinder gathers usage information about current cinder usage.::

   $ nectar-metrics-cinder --help
   usage: nectar-metrics-cinder [-h] [--config-file PATH] [--debug]
                                [--protocol PROTOCOL]
                                [--victoria-url VICTORIA_URL] [--limit LIMIT]
                                ...

   options:
     --limit LIMIT         Limit the response to some volumes only.

Cinder metrics are grouped by tenant and by az by tenant::

   $ nectar-metrics-cinder --protocol debug --limit 1
   tenant.f4fff40d98984cea9e39af597456001b.used_volume_size 1000.00 1415354196
   tenant.f4fff40d98984cea9e39af597456001b.total_volumes 1.00 1415354196
   az.NCI.tenant.f4fff40d98984cea9e39af597456001b.used_volume_size 1000.00 1415354196
   az.NCI.tenant.f4fff40d98984cea9e39af597456001b.total_volumes 1.00 1415354196

RCShibboleth
------------

RCShibboleth queries the RCShibboleth database and gathers details of
the current user registrations.::

   $ nectar-metrics-rcshibboleth --help
   usage: nectar-metrics-rcshibboleth [-h] [--config-file PATH] [--debug]
                                      [--protocol PROTOCOL]
                                      [--victoria-url VICTORIA_URL]
                                      [--from-date FROM_DATE]
                                      [--to-date TO_DATE]
                                      ...

   options:
     --from-date FROM_DATE
                           When to backfill data from (YYYY-MM-DD, default:
                           now).
     --to-date TO_DATE     When to backfill data to (YYYY-MM-DD, default: now).


The only metric that is reported is the current registrations grouped by IdP::

   $ nectar-metrics-rcshibboleth --protocol debug
   users.total 5018.00 1424666333
   users.idp_cc_swin_edu_au.total 59.00 1424666333
   users.aaf_latrobe_edu_au.total 40.00 1424666333
   users.idp1_griffith_edu_au.total 83.00 1424666333
   users.idp_csu_edu_au.total 17.00 1424666333
   users.idp_murdoch_edu_au.total 37.00 1424666333
