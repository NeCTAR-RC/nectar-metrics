from oslo_config import cfg

from ceilometer.agent import plugin_base


opt_group = cfg.OptGroup(name='f5',
                         title='Options for F5 SNMP connection')

OPTS = [
    cfg.StrOpt('host',
               help='SNMP hostname or IP address.'),
    cfg.StrOpt('snmp_username',
               default='ceilometer',
               help='SNMP v3 authentication username.'),
    cfg.StrOpt('snmp_password',
               help='SNMP v3 authentication password.',
               secret=True),
    cfg.StrOpt('snmp_auth_proto',
               choices=['md5', 'sha'],
               help='SNMP v3 authentication algorithm.'),
    cfg.StrOpt('snmp_priv_proto',
               choices=['des', 'aes128', '3des', 'aes192', 'aes256'],
               help='SNMP v3 encryption algorithm.'),
    cfg.StrOpt('snmp_priv_password',
               help='SNMP v3 encryption password.',
               secret=True),
]


class F5Discovery(plugin_base.DiscoveryBase):

    def __init__(self, conf):
        super(F5Discovery, self).__init__(conf)
        conf.register_group(opt_group)
        conf.register_opts(OPTS, group=opt_group)

    def _make_resource_url(self, host):
        f5conf = self.conf.f5
        url = 'snmp://'
        username = f5conf.snmp_username
        password = f5conf.snmp_password
        if username:
            url += username
        if password:
            url += ':' + password
        if username or password:
            url += '@'
        url += host

        opts = ['auth_proto', 'priv_proto', 'priv_password']
        query = "&".join(opt + "=" + f5conf['snmp_%s' % opt]
                         for opt in opts
                         if f5conf['snmp_%s' % opt])
        if query:
            url += '?' + query

        return url

    def discover(self, manager, param=None):
        """Discover resources to monitor.

        instance_get_all will return all instances if last_run is None,
        and will return only the instances changed since the last_run time.
        """
        resources = []
        # TODO(andybotting): Support multiple hosts
        hosts = [self.conf.f5.host]
        for host in hosts:
            resource_url = self._make_resource_url(host)
            resource = {
                'resource_id': 'f5',
                'resource_url': resource_url,
            }
            resources.append(resource)
        return resources
