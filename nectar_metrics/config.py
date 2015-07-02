import os
from UserDict import UserDict
from ConfigParser import SafeConfigParser


CONFIG_FILE = '/etc/nectar/metrics.ini'
WORKING_PATH = os.getcwd()
ALT_CONFIG_FILE = os.path.join(WORKING_PATH, "metrics.ini")


class ConfigurationDict(UserDict):
    def get(self, section, key, default=None):
        if section in self.data:
            if key in self.data[section]:
                return self.data[section][key]
        return default

    def get_list(self, section, key, default=[]):
        if section in self.data:
            if key in self.data[section]:
                return self.data[section][key].split(',')
        return default

    def set(self, section, key, value):
        if section not in self.data:
            self.data[section] = {}
        self.data[section][key] = value
        return value

CONFIG = ConfigurationDict()


def as_dict(config):
    config_dict = {}
    for section in config.sections():
        config_dict[section] = {}
        for key, val in config.items(section):
            config_dict[section][key] = val
    return config_dict


def read(filename=None):
    if os.path.exists(filename):
        filename = filename
    elif os.path.exists(CONFIG_FILE):
        filename = CONFIG_FILE
    elif os.path.exists(ALT_CONFIG_FILE):
        filename = ALT_CONFIG_FILE
    else:
        raise Exception("Can't find configuration file. %s" % CONFIG_FILE)
    parser = SafeConfigParser()
    parser.read(filename)
    CONFIG.update(as_dict(parser))
