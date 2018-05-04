import requests

from ceilometer.agent import plugin_base


class SwiftDiskDiscovery(plugin_base.DiscoveryBase):

    def discover(self, manager, param=None):
        """Discover object server disks."""
        response = requests.get('http://127.0.1:6000/recon/diskusage')
        return response.json()
