import itertools
import re

from ceilometer.polling import plugin_base
from ceilometer import sample

from oslo_log import log


LOG = log.getLogger(__name__)


class VirtualDesktopPollster(plugin_base.PollsterBase):
    """Collect stats on murano application environments"""

    @property
    def default_discovery(self):
        return 'virtual_desktops'

    def get_samples(self, manager, cache, resources):
        samples = []

        for family in resources:
            m = re.search(r'bumblebee_desktops_(?P<action>[^\W_]+)',
                          family.name)
            if m:  # matched action from bumblebee_desktops_<action>_by_domain
                action = m.groupdict().get('action')
                for s in family.samples:
                    if s.labels:
                        for label, val in s.labels.items():
                            name = "virtual_desktop.desktops.{}.{}".format(
                                       action, label)
                            samples.append(sample.Sample(
                                name=name,
                                type=sample.TYPE_GAUGE,
                                unit='desktops',
                                volume=s.value,
                                user_id=None,
                                project_id=None,
                                resource_id=val))
                    else:
                        name = "global.virtual_desktop.desktops.{}".format(
                                   action)
                        samples.append(sample.Sample(
                            name=name,
                            type=sample.TYPE_GAUGE,
                            unit='desktops',
                            volume=s.value,
                            user_id=None,
                            project_id=None,
                            resource_id='global-stats'))

        sample_iters = []
        sample_iters.append(samples)
        LOG.debug("Sending package samples %s", sample_iters)
        return itertools.chain(*sample_iters)
