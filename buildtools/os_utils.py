'''
OS Utilities.

Copyright (c) 2015 Rob "N3X15" Nelson <nexisentertainment@gmail.com>

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

'''
import os
import sys
import glob
import subprocess
import shutil
import platform
import time
import re
import threading

from subprocess import CalledProcessError
from functools import reduce

# package psutil
import psutil 


from buildtools.bt_logging import log

buildtools_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
scripts_dir = os.path.join(buildtools_dir, 'scripts')

REG_EXCESSIVE_WHITESPACE = re.compile(r'\s{2,}')


def clock():
    if sys.platform == 'win32':
        return time.clock()
    else:
        return time.time()


def getElapsed(start):
    return '%d:%02d:%02d.%03d' % reduce(lambda ll, b: divmod(ll[0], b) + ll[1:], [((clock() - start) * 1000,), 1000, 60, 60])


def secondsToStr(t):
    return "%d:%02d:%02d.%03d" % \
        reduce(lambda ll, b: divmod(ll[0], b) + ll[1:],
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

    @classmethod
    def dump(cls, env):
        for key, value in sorted(env.iteritems()):
            log.info('+{0}="{1}"'.format(key, value))


def ensureDirExists(path, mode=0o777, noisy=False):
    if not os.path.isdir(path):
        os.makedirs(path, mode)
        if noisy:
            log.info('Created %s.', path)


class DeferredLogEntry(object):

    def __init__(self, label):
        self.label = label

    def toStr(self, entryVars):
        return self.label.format(**entryVars)


class TimeExecution(object):

    def __init__(self, label):
        self.start_time = None
        self.vars = {}
        if isinstance(label, str):
            self.label = DeferredLogEntry('Completed in {elapsed}s - {label}')
            self.vars['label'] = label
        elif isinstance(label, DeferredLogEntry):
            self.label = label

    def __enter__(self):
        self.start_time = clock()
        return self

    def __exit__(self, typeName, value, traceback):
        self.vars['elapsed'] = secondsToStr(clock() - self.start_time)
        with log:
            log.info(self.label.toStr(self.vars))
        return False


class Chdir(object):

    def __init__(self, newdir, quiet=False):
        self.pwd = os.path.abspath(os.getcwd())
        self.chdir = newdir
        self.quiet = quiet

    def __enter__(self):
        try:
            if os.getcwdu() != self.chdir:
                os.chdir(self.chdir)
                if not self.quiet:
                    log.info('cd ' + self.chdir)
        except:
            log.critical('Failed to chdir to {}.'.format(self.chdir))
            sys.exit(1)
        return self

    def __exit__(self, typeName, value, traceback):
        try:
            if os.getcwdu() != self.pwd:
                os.chdir(self.pwd)
                if not self.quiet:
                    log.info('cd ' + self.pwd)
        except:
            log.critical('Failed to chdir to {}.'.format(self.pwd))
            sys.exit(1)
        return False


def is_executable(fpath):
    if sys.platform == 'win32':
        if not fpath.endswith('.exe'):
            fpath += '.exe'
    return os.path.isfile(fpath) and os.access(fpath, os.X_OK)


def which(program):
    fpath, _ = os.path.split(program)
    if fpath:
        if is_executable(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_executable(exe_file):
                return exe_file

    return None


def _cmd_handle_env(env):
    if env is None:
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
    for arg in command:  # 1:
        arg = str(arg)
        if '*' in arg or '?' in arg:
            new_args += glob.glob(arg)
        elif '~' in arg:
            new_args += [os.path.expanduser(arg)]
        else:
            new_args += [arg]
    return new_args


def find_process(pid):
    for proc in psutil.process_iter():
        try:
            if proc.pid == pid:
                if proc.status() == psutil.STATUS_ZOMBIE:
                    log.warn('Detected zombie process #%s, skipping.', proc.pid)
                    continue
                return proc
        except psutil.AccessDenied:
            continue
    return None



def cmd(command, echo=False, env=None, show_output=True, critical=False):
    new_env = _cmd_handle_env(env)
    command = _cmd_handle_args(command)
    if echo:
        log.info('$ ' + (' '.join(command)))

    if show_output:
        return subprocess.call(command, env=new_env, shell=False) == 0
    output = ''
    try:
        output = subprocess.check_output(command, env=new_env, stderr=subprocess.STDOUT)
        return True
    except CalledProcessError as cpe:
        log.error(cpe.output)
        if critical:
            raise cpe
        log.error(cpe)
        return False
    except Exception as e:
        log.error(e)
        log.error(output)
        if critical:
            raise e
        log.error(e)
        return False


def cmd_output(command, echo=False, env=None, critical=False):
    '''
    :returns List[2]: (stdout,stderr)
    '''
    new_env = _cmd_handle_env(env)
    command = _cmd_handle_args(command)
    if echo:
        log.info('$ ' + (' '.join(command)))

    try:
        return subprocess.Popen(command, env=new_env, stdout=subprocess.PIPE, stderr=subprocess.PIPE).communicate()
    except Exception as e:
        log.error(repr(command))
        if critical:
            raise e
        log.error(e)
    return False


def cmd_daemonize(command, echo=False, env=None, critical=False):
    new_env = _cmd_handle_env(env)
    command = _cmd_handle_args(command)
    if echo:
        log.info('& ' + ' '.join(command))

    try:
        if platform.system() == 'Windows':
            # HACK
            batch = os.tmpnam() + '.bat'
            with open(batch, 'w') as b:
                b.write(' '.join(command))
            os.startfile(batch)
        else:
            subprocess.Popen(command, env=new_env)
        return True
    except Exception as e:
        log.error(repr(command))
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


def canCopy(src, dest, **op_args):
    return not os.path.isfile(dest) or op_args.get('ignore_mtime', False) or (os.stat(src).st_mtime - os.stat(dest).st_mtime > 1)


def _op_copy(fromfile, newroot, **op_args):
    newfile = os.path.join(newroot, os.path.basename(fromfile))
    if canCopy(fromfile, newfile, **op_args):
        if op_args.get('verbose', False):
            log.info('Copying {} -> {}'.format(fromfile, newfile))
        shutil.copy2(fromfile, newfile)


def copytree(fromdir, todir, ignore=None, verbose=False, ignore_mtime=False):
    optree(fromdir, todir, _op_copy, ignore,
           verbose=verbose, ignore_mtime=ignore_mtime)


def optree(fromdir, todir, op, ignore=None, **op_args):
    if ignore is None:
        ignore = []
    # print('ignore=' + repr(ignore))
    for root, _, files in os.walk(fromdir):
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
                log.info(u'mkdir {}'.format(newroot))
            os.makedirs(newroot)
        for filename in files:
            fromfile = os.path.join(root, filename)
            _, ext = os.path.splitext(os.path.basename(fromfile))
            if ext in ignore:
                if op_args.get('verbose', False):
                    log.info(u'Skipping {} ({})'.format(fromfile, ext))
                continue
            op(fromfile, newroot, **op_args)


def safe_rmtree(dirpath):
    for root, dirs, files in os.walk(dirpath, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))


def RemoveExcessiveWhitespace(text):
    return REG_EXCESSIVE_WHITESPACE.sub('', text)


def sizeof_fmt(num):
    for x in ['bytes', 'KB', 'MB', 'GB', 'TB']:
        if num < 1024.0:
            return "%3.1f %s" % (num, x)
        num /= 1024.0


def standardize_path(path):
    pathchunks = path.split('/')
    path = pathchunks[0]
    for chunk in pathchunks[1:]:
        path = os.path.join(path, chunk)
    return path


def decompressFile(path):
    '''
    Decompresses the file to the current working directory.
    '''
    if path.endswith('.tar.gz'):
        cmd(['tar', 'xzf', path], echo=True, critical=True)
        return True
    elif path.endswith('.tar.bz'):
        cmd(['tar', 'xjf', path], echo=True, critical=True)
        return True
    elif path.endswith('.tar.xz'):
        cmd(['tar', 'xJf', path], echo=True, critical=True)
        return True
    elif path.endswith('.tar.7z'):
        cmd(['7za', 'x', path], echo=True, critical=True)
        cmd(['tar', 'xf', path[:-3]], echo=True, critical=True)
        os.remove(path[-3])
        return True
    elif path.endswith('.zip'):
        cmd(['unzip', path[:-3]], echo=True, critical=True)
        return True
    return False

ENV = BuildEnv()

# Platform-specific extensions
if platform.system() == 'Windows':
    from buildtools._os_utils_win32 import WindowsEnv
else:
    import buildtools._os_utils_linux
    buildtools._os_utils_linux.cmd_output = cmd_output
    from buildtools._os_utils_linux import GetDpkgShlibs, InstallDpkgPackages, DpkgSearchFiles
    
# Stubs for lazy-loading twisted shit.
def init_async():
    # Lazy-load Twisted.
    import buildtools._os_utils_async as asynclib
    asynclib.os_utils=sys.modules[__name__]
    return asynclib

def async_cmd(command, stdout=None, stderr=None, env=None):
    return init_async().async_cmd(command, stdout, stderr, env)

def AsyncCommand(command, stdout=None, stderr=None, echo=False, env=None, PTY=False, refName=None, debug=False):
    return init_async().AsyncCommand(command, stdout, stderr, env)


class ReactorManager:
    instance = None

    @classmethod
    def Start(cls):
        init_async().ReactorManager.Start()

    @classmethod
    def Stop(cls):
        init_async().ReactorManager.Stop()

