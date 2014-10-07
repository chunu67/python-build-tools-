import os, sys, glob, subprocess

from buildtools.bt_logging import log

class BuildEnv(object):
    def __init__(self,initial=None):
        if initial is not None:
            self.env = initial
        else:
            self.env = os.environ
            
    def set(self,key,val):
        log.info('Build env: {} = {}'.format(key, val))
        self.env[key] = val
    
    def get(self,val,default=None):
        if key not in self.env:
            return default
        return self.env[key]
    
    def merge(self,newvars):
        self.env = dict(self.env, **newvars)

class Chdir(object):
    def __init__(self, newdir):
        self.pwd = os.path.abspath(os.getcwd())
        self.chdir = newdir
    
    def __enter__(self):
        try:
            os.chdir(self.chdir)
            log.info('cd ' + self.chdir)
        except:
            log.critical('Failed to chdir to {}.'.format(self.chdir))
            sys.exit(1)
        return self
    
    def __exit__(self, type, value, traceback):
        try:
            os.chdir(self.pwd)
            log.info('cd ' + self.pwd)
        except:
            log.critical('Failed to chdir to {}.'.format(self.pwd))
            sys.exit(1)
        return False
    
def cmd(command, echo=False, env=None, show_output=True, critical=False):
    if env is None:
        global ENV
        env=ENV.env
    # Shell-style globbin'.
    new_args = [command[0]]
    for arg in command[1:]:
        arg=str(arg)
        if '*' in arg or '?' in arg:
            new_args += glob.glob(arg)
        if '~' in arg:
            new_args += os.path.expanduser(arg)
        else:
            new_args += [arg]
            
    # Fix a bug where env vars get some weird types.
    new_env = {}
    for k, v in env.items():
        k = str(k)
        v = str(v)
        new_env[k] = v
        
    command = new_args
    if echo:
        log.info('$ ' + ' '.join(command))
        
    if show_output:
        return subprocess.call(command, env=new_env, shell=False) != 0
    output = ''
    try:
        output = subprocess.check_output(command, env=new_env, stderr=subprocess.STDOUT)
        return True
    except Exception as e:
        log.error(repr(command))
        log.error(output)
        log.error(e)
        if critical:
            sys.exit(1)
        return False

ENV = BuildEnv()