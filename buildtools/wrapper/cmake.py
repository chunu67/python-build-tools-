import os

from buildtools.bt_logging import log
from buildtools.os_utils import cmd

class CMake(object):
    def __init__(self):
        self.flags = []
        
    def setFlag(self, key, val):
        log.info('CMake: {} = {}'.format(key, val))
        self.flags[key] = val
        
    def run(cfg, env=os.environ, dir='.'):
        CMAKE = cfg.get('bin.cmake', 'cmake')
        flags = []
        
        for key, value in self.flags.items():
            flags += ['-D{0}={1}'.format(key, value)]
            
        with log.info('Running CMake:'):
            for key, value in BUILD_ENV.items():
                log.info('+{0}="{1}"'.format(key, value))
            lolenv=env
            cmd([CMAKE] + flags + [dir], env=lolenv, critical=True, echo=True)
