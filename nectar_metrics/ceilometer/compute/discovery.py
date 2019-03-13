from oslo_utils import timeutils

from ceilometer.compute import discovery


class InstanceAllDiscovery(discovery.InstanceDiscovery):
    method = 'naive'

    def discover_nova_polling(self, manager, param=None):
        secs_from_last_update = 0
        utc_now = timeutils.utcnow(True)
        secs_from_last_expire = 0
        if self.last_run:
            secs_from_last_update = timeutils.delta_seconds(
                self.last_run, utc_now)
        if self.last_cache_expire:
            secs_from_last_expire = timeutils.delta_seconds(
                self.last_cache_expire, utc_now)

        instances = []
        # NOTE(ityaptin) we update make a nova request only if
        # it's a first discovery or resources expired
        with self.lock:
            if (not self.last_run or secs_from_last_update >=
                    self.expiration_time):
                try:
                    if (secs_from_last_expire < self.cache_expiry and
                            self.last_run):
                        since = self.last_run.isoformat()
                    else:
                        since = None
                        self.instances.clear()
                        self.last_cache_expire = utc_now
                    instances = self.nova_cli.instance_get_all(since)
                    self.last_run = utc_now
                except Exception:
                    # NOTE(zqfan): instance_get_all is wrapped and will
                    # log exception when there is any error. It is no need to
                    #  raise it again and print one more time.
                    return []

            for instance in instances:
                if getattr(instance, 'OS-EXT-STS:vm_state', None) in [
                   'deleted', 'error']:
                    self.instances.pop(instance.id, None)
                else:
                    self.instances[instance.id] = instance

        return self.instances.values()
