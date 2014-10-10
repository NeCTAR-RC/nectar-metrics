from os import path
import logging.config

from nectar_metrics.config import CONFIG


def setup(filename, file_level='INFO', console_level='INFO'):
    config = {
        'version': 1,
        'disable_existing_loggers': False,
        'formatters': {
            'simple': {
                'format': '%(asctime)s %(name)s %(levelname)s %(message)s'
            },
        },
        'handlers': {
            'console': {
                'level': console_level,
                'class':'logging.StreamHandler',
                'formatter': 'simple'
            },
            'file': {
                'level': file_level,
                'class': 'logging.FileHandler',
                'formatter': 'simple',
                'filename': "",
            },
        },
        'root': {
            'handlers': ['console', 'file'],
            'level': 'DEBUG',
        },
    }
    log_dir = CONFIG.get('metrics', 'log_dir')
    if log_dir:
        config['handlers']['file']['filename'] = path.join(log_dir, filename)
    else:
        del config['handlers']['file']
    logging.config.dictConfig(config)
