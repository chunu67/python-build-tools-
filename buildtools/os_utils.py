import os, sys, glob, subprocess, shutil, platform, time

from buildtools.bt_logging import log

def clock():
    if sys.platform == 'win32':
        return time.clock()
    else:
        return time.time()

def getElapsed(start):
    return '%d:%02d:%02d.%03d' % reduce(lambda ll, b : divmod(ll[0], b) + ll[1:], [((clock() - start) * 1000,), 1000, 60, 60])

def secondsToStr(t):
    return "%d:%02d:%02d.%03d" % \
        reduce(lambda ll, b : divmod(ll[0], b) + ll[1:],
            [(t * 1000,), 1000, 60, 60])

class BuildEnv(object):
    def __init__(self, initial=None):
        if initial is not None:
            self.env = initial
        else:
            self.env = os.environ
            
    def set(self, key, val):
        log.info('Build env: {} = {}'.format(key, val))
        self.env[key] = val
    
    def get(self, key, default=None):
        if key not in self.env:
            return default
        return self.env[key]
    
    def merge(self, newvars):
        self.env = dict(self.env, **newvars)
        
class TimeExecution(object):
    def __init__(self, label):
        self.start_time = None
        self.label = label
    
    def __enter__(self):
        self.start_time = clock()
        return self
    
    def __exit__(self, type, value, traceback):
        log.info('  Completed in {1}s - {0}'.format(self.label, secondsToStr(clock() - self.start_time)))
        return False

class Chdir(object):
    def __init__(self, newdir, quiet=False):
        self.pwd = os.path.abspath(os.getcwd())
        self.chdir = newdir
        self.quiet = quiet
    
    def __enter__(self):
        try:
            os.chdir(self.chdir)
            if not self.quiet:
                log.info('cd ' + self.chdir)
        except:
            log.critical('Failed to chdir to {}.'.format(self.chdir))
            sys.exit(1)
        return self
    
    def __exit__(self, type, value, traceback):
        try:
            os.chdir(self.pwd)
            if not self.quiet:
                log.info('cd ' + self.pwd)
        except:
            log.critical('Failed to chdir to {}.'.format(self.pwd))
            sys.exit(1)
        return False
    
def _cmd_handle_env(env):
    if env is None:
        global ENV
        env = ENV.env
            
    # Fix a bug where env vars get some weird types.
    new_env = {}
    for k, v in env.items():
        k = str(k)
        v = str(v)
        new_env[k] = v
    return new_env

def _cmd_handle_args(command):
    # Shell-style globbin'.
    new_args = []  # command[0]]
    for arg in command[:]:  # 1:
        arg = str(arg)
        if '*' in arg or '?' in arg:
            new_args += glob.glob(arg)
        elif '~' in arg:
            new_args += os.path.expanduser(arg)
        else:
            new_args += [arg]
    return new_args
    
def cmd(command, echo=False, env=None, show_output=True, critical=False):
    new_env = _cmd_handle_env(env)
    command = _cmd_handle_args(command)
    if echo:
        log.info('$ ' + ' '.join(command))
        
    if show_output:
        return subprocess.call(command, env=new_env, shell=False) == 0
    output = ''
    try:
        output = subprocess.check_output(command, env=new_env, stderr=subprocess.STDOUT)
        return True
    except Exception as e:
        log.error(repr(command))
        log.error(output)
        if critical:
            raise e
        log.error(e)
        return False
    
def cmd_output(command, echo=False, env=None, critical=False):
    new_env = _cmd_handle_env(env)
    command = _cmd_handle_args(command)
    if echo:
        log.info('$ ' + ' '.join(command))
        
    try:
        return subprocess.Popen(command, env=new_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    except Exception as e:
        log.error(repr(command))
        if critical:
            raise e
        log.error(e)
        return False
    
def cmd_daemonize(command, echo=False, env=None, show_output=True, critical=False):
    new_env = _cmd_handle_env(env)
    command = _cmd_handle_args(command)
    if echo:
        log.info('& ' + ' '.join(command))
        
    try:
        subprocess.Popen(command, env=new_env)
        return True
    except Exception as e:
        log.error(repr(command))
        log.error(output)
        if critical:
            raise e
        log.error(e)
        return False

def old_copytree(src, dst, symlinks=False, ignore=None):
    if not os.path.exists(dst):
        os.makedirs(dst)
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            copytree(s, d, symlinks, ignore)
        else:
            if not os.path.exists(d) or os.stat(src).st_mtime - os.stat(dst).st_mtime > 1:
                shutil.copy2(s, d)
    
def _op_copy(fromfile, newroot, **op_args):
    newfile = os.path.join(newroot, os.path.basename(fromfile))
    if not os.path.isfile(newfile) or op_args.get('ignore_mtime',False) or (os.stat(fromfile).st_mtime - os.stat(newfile).st_mtime > 1):
        if op_args.get('verbose', False):
            log.info('Copying {} -> {}'.format(fromfile, newfile))
        shutil.copy2(fromfile, newfile)
        
def copytree(fromdir, todir, ignore=[], verbose=False, ignore_mtime=False):
    optree(fromdir, todir, _op_copy, ignore, verbose=verbose, ignore_mtime=ignore_mtime)

def optree(fromdir, todir, op, ignore=[], **op_args):
    # print('ignore=' + repr(ignore))
    for root, dirs, files in os.walk(fromdir):
        path = root.split(os.sep)
        start = len(fromdir)
        if root[start:].startswith(os.sep):
            start += 1
        substructure = root[start:]
        assert not substructure.startswith(os.sep)
        newroot = os.path.join(todir, substructure)
        if any([(x + '/' in ignore) for x in path]):
            if op_args.get('verbose', False):
                log.info(u'Skipping {}'.format(substructure))
            continue
        if not os.path.isdir(newroot):
            if op_args.get('verbose', False):
                log.info('mkdir {}'.format(newroot))
            os.makedirs(newroot)
        for file in files:
            fromfile = os.path.join(root, file)
            title, ext = os.path.splitext(os.path.basename(fromfile))
            if ext in ignore:
                if op_args.get('verbose', False):
                    log.info(u'Skipping {} ({})'.format(fromfile, ext))
                continue
            op(fromfile, newroot, **op_args)
            
ENV = BuildEnv()
