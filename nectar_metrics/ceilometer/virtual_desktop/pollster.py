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
                for samp in family.samples:
                    # NOTE: Samples are a tuple for old versions (0.1.1)
                    # of prometheus client, but it's an object in newer
                    # (0.12.0) versions. Force to tuple for compatibility
                    s = tuple(samp)
                    labels = s[1]
                    value = s[2]
                    if labels:
                        for label_name, label_value in labels.items():
                            name = "virtual_desktop.desktops.{}.{}".format(
                                       action, label_name)
                            samples.append(sample.Sample(
                                name=name,
                                type=sample.TYPE_GAUGE,
                                unit='desktops',
                                volume=value,
                                user_id=None,
                                project_id=None,
                                resource_id=label_value))
                    else:
                        name = "global.virtual_desktop.desktops.{}".format(
                                   action)
                        samples.append(sample.Sample(
                            name=name,
                            type=sample.TYPE_GAUGE,
                            unit='desktops',
                            volume=value,
                            user_id=None,
                            project_id=None,
                            resource_id='global-stats'))

        sample_iters = []
        sample_iters.append(samples)
        LOG.debug("Sending package samples %s", sample_iters)
        return itertools.chain(*sample_iters)
