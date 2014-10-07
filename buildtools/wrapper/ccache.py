import os

from buildtools.bt_logging import log
from buildtools.os_utils import cmd, ENV

def configure_ccache(cfg, cmake):
    global ENV
    with log.info('Configuring ccache...'):
        if not cfg.get('env.ccache.enabled', False):
            log.info('ccache disabled, skipping.')
        
            # Otherwise, strange things happen.
            ENV.set('CC', ENV.get('CC','gcc') + '.real')
            ENV.set('CXX', ENV.get('CXX','g++') + '.real')
        else:
            CCACHE = cfg.get('bin.ccache', 'ccache')
            DISTCC = cfg.get('bin.distcc', 'distcc')
            
            if cfg.get('env.distcc.enabled', False):
                ENV.set('CCACHE_PREFIX', DISTCC)

            # Fixes a bug where CMake sets this all incorrectly. 
            # http://public.kitware.com/Bug/view.php?id=12274
            cmake.setFlag('CMAKE_CXX_COMPILER_ARG1', ENV.env['CXX'])
            # set_cmake_env('CMAKE_ASM_COMPILER_ARG1',ENV.env['ASM'])
            
            ENV.set('CC', CCACHE + ' ' + ENV.env['CC'])
            ENV.set('CXX', CCACHE + ' ' + ENV.env['CXX'])
            # ENV.set('ASM',CCACHE + ' ' + ENV.env['ASM'])