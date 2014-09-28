import os

from buildtools.bt_logging import log
from buildtools.os_utils import cmd

class CMake(object):
    def __init__(self):
        self.flags = {}
        
    def setFlag(self, key, val):
        log.info('CMake: {} = {}'.format(key, val))
        self.flags[key] = val
        
    def run(self, CMAKE, env=os.environ, dir='.'):
        flags = []
        
        for key, value in self.flags.items():
            flags += ['-D{0}={1}'.format(key, value)]
            
        with log.info('Running CMake:'):
            for key, value in env.items():
                log.info('+{0}="{1}"'.format(key, value))
            cmd([CMAKE] + flags + [dir], env=env, critical=True, echo=True)
