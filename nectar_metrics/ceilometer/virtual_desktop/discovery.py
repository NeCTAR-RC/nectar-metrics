from ceilometer.polling import plugin_base

from oslo_log import log
from oslo_config import cfg

from prometheus_client.parser import text_string_to_metric_families

import requests
from requests.auth import HTTPBasicAuth


LOG = log.getLogger(__name__)


opt_group = cfg.OptGroup(name='bumblebee',
                         title='Options for Bumblebee')

OPTS = [
    cfg.StrOpt('url',
               help='Bumblebee metrics URL'),
    cfg.StrOpt('username',
               help='Bumblebee metrics username'),
    cfg.StrOpt('password',
               secret=True,
               help='Bumblebee metrics password'),
]


class VirtualDesktopDiscovery(plugin_base.DiscoveryBase):

    def __init__(self, conf):
        conf.register_group(opt_group)
        conf.register_opts(OPTS, group=opt_group)
        super(VirtualDesktopDiscovery, self).__init__(conf)

    def discover(self, manager, param=None):
        if (not self.conf.bumblebee.url or not self.conf.bumblebee.username
                or not self.conf.bumblebee.password):
            LOG.error("Bumblebee url, username or password missing. "
                      "Please check your configuration")
            raise

        response = requests.get(
            self.conf.bumblebee.url,
            auth=HTTPBasicAuth(
                self.conf.bumblebee.username,
                self.conf.bumblebee.password))

        # Return only bumblebee metrics from the prometheus data format
        return [f for f in text_string_to_metric_families(response.text)
                if f.name.startswith('bumblebee')]
