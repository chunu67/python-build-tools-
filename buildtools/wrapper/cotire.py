import os

from buildtools.bt_logging import log
from buildtools.os_utils import cmd, ENV

def configure_cotire(cfg, cmake):
    global ENV
    with log.info('Configuring cotire...'):
        if not cfg.get('env.cotire.enabled', False):
            log.info('cotire disabled, skipping.')
        else:
            ENV.set('CCACHE_SLOPPINESS', 'time_macros')
            cmake.setFlag('ENABLE_COTIRE', 'On')
            if cfg.get('env.make.jobs', 1) > 1:
                cmake.setFlag('COTIRE_MAXIMUM_NUMBER_OF_UNITY_INCLUDES', cfg.get('env.make.jobs', 1))
