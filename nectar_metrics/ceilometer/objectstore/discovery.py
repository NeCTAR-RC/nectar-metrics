import requests
import json

from ceilometer.agent import plugin_base


class SwiftDiskDiscovery(plugin_base.DiscoveryBase):

    def discover(self, manager, param=None):
        """Discover object server disks."""

        response = requests.get('http://localhost:6000/recon/diskusage')
        return json.loads(response.text)
        
