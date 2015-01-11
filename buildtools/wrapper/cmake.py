import os

from buildtools.bt_logging import log
from buildtools.os_utils import cmd, ENV

class CMake(object):
    def __init__(self):
        self.flags = {}
        self.generator = None
        
    def setFlag(self, key, val):
        log.info('CMake: {} = {}'.format(key, val))
        self.flags[key] = val
        
    def build(self, CMAKE, dir='.', env=None, target=None, moreflags=[]):
        moreflags += ['--build']
        if target is not None:
            moreflags += ['--target', target]
        self.run(CMAKE, env, dir, moreflags)
        
    def run(self, CMAKE, env=None, dir='.', moreflags=[]):
        if env is None:
            env = ENV.env
        flags = []
        
        if self.generator is not None:
            flags += ['-G', self.generator]
        
        for key, value in self.flags.items():
            flags += ['-D{0}={1}'.format(key, value)]
        
        flags += moreflags
        
        with log.info('Running CMake:'):
            for key, value in env.items():
                log.info('+{0}="{1}"'.format(key, value))
            return cmd([CMAKE] + flags + [dir], env=env, critical=True, echo=True)
        return False
