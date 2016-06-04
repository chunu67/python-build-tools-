'''
OS Utilities.

Copyright (c) 2015 - 2016 Rob "N3X15" Nelson <nexisentertainment@gmail.com>

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
import zipfile

from subprocess import CalledProcessError
from functools import reduce

# package psutil
import psutil


from buildtools.bt_logging import log

buildtools_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
scripts_dir = os.path.join(buildtools_dir, 'scripts')

REG_EXCESSIVE_WHITESPACE = re.compile(r'\s{2,}')
PLATFORM = platform.system()


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
        self.keycapmap = {k.upper(): k for k in self.env}
        self.noisy = True

    def getKey(self, key):
        okey = key
        key = key.upper()
        if key not in self.keycapmap:
            self.keycapmap[key] = okey
        return self.keycapmap[key]

    def set(self, key, val,noisy=None):
        if noisy is None:
            noisy=self.noisy
        key = self.getKey(key)
        if noisy: log.info('Build env: {} = {}'.format(key, val))
        self.env[key] = val

    def get(self, key, default=None):
        key = self.getKey(key)
        if key not in self.env:
            return default
        return self.env[key]

    def merge(self, newvars):
        self.env = dict(self.env, **newvars)

    def prependTo(self, key, value, delim=';', noisy=None):
        if noisy is None:
            noisy=self.noisy
        key = self.getKey(key)
        if noisy: log.info('Build env: {1} prepended to {0}'.format(key, value))
        self.env[key] = delim.join([value] + ENV.env[key].split(delim))

    def appendTo(self, key, value, delim=';', noisy=None):
        if noisy is None:
            noisy=self.noisy
        key = self.getKey(key)
        if noisy: log.info('Build env: {1} appended to {0}'.format(key, value))
        self.env[key] = delim.join(ENV.env[key].split(delim) + [value])

    def clone(self):
        return BuildEnv(self.env.copy())

    def dumpToLog(self, keys=None):
        if keys is None:
            keys = self.env.keys()
        ENV.dump(self.env, keys)

    def which(self, program, skip_paths=[]):
        fpath, _ = os.path.split(program)
        if fpath:
            if is_executable(program):
                return program
        else:
            for path in self.get("PATH").split(os.pathsep):
                path = path.strip('"')
                is_skipped_path=False
                for badpath in skip_paths:
                    if badpath.lower() in path.lower():
                        is_skipped_path=True
                        break
                if is_skipped_path:
                    continue
                exe_file = os.path.join(path, program)
                if sys.platform == 'win32':
                    for ext in self.get("PATHEXT").split(os.pathsep):
                        proposed_file = exe_file + ""
                        if not proposed_file.endswith(ext):
                            proposed_file += ext
                            if os.path.isfile(proposed_file):
                                exe_file = proposed_file
                                #print('{}: {}'.format(exe_file,ext))
                                break
                if is_executable(exe_file):
                    return exe_file
        return None

    def removeDuplicatedEntries(self,key,noisy=None,delim=os.pathsep):
        if noisy is None:
            noisy=self.noisy
        newlist=[]
        key=self.getKey(key)
        for entry in self.env[key].split(delim):
            entry = entry.strip('"')
            if entry in newlist:
                if noisy: log.info('Build env: Removing %r from %s: duplicated entry.',entry,key)
                continue
            newlist+=[entry]
        self.env[key]=delim.join(newlist)

    @classmethod
    def dump(cls, env, keys=None):
        for key, value in sorted(env.iteritems()):
            if keys is not None and key not in keys:
                continue
            log.info('+{0}="{1}"'.format(key, value))


def ensureDirExists(path, mode=0o777, noisy=False):
    if path != '' and not os.path.isdir(path):
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
    return os.path.isfile(fpath) and os.access(fpath, os.X_OK)


def which(program):
    return ENV.which(program)


def assertWhich(program, fail_raise=False):
    fullpath = ENV.which(program)
    with log.info('Checking if %s exists...', program):
        if fullpath is None:
            errmsg = '{executable} is not in PATH!'.format(executable=program)
            if fail_raise:
                raise RuntimeError(errmsg)
            else:
                log.critical(errmsg)
                sys.exit(1)
        else:
            log.info('Found: %s', fullpath)
    return fullpath


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


def _cmd_handle_args(command, globbify):
    # Shell-style globbin'.
    new_args = []  # command[0]]
    for arg in command:  # 1:
        arg = str(arg)
        if globbify:
            if '~' in arg:
                arg = os.path.expanduser(arg)
            if '*' in arg or '?' in arg:
                new_args += glob.glob(arg)
                continue

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


def cmd(command, echo=False, env=None, show_output=True, critical=False, globbify=True):
    new_env = _cmd_handle_env(env)
    command = _cmd_handle_args(command,globbify)
    if echo:
        log.info('$ ' + (' '.join(command)))
            
    output = ''
    try:
        if show_output:
            code = subprocess.call(command, env=new_env, shell=False)
            success = code == 0
            if critical and code:
                raise CalledProcessError(code, command)
            return success
        else:
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


def single_copy(fromfile, newroot, **op_args):
    newfile = os.path.join(newroot, os.path.basename(fromfile))
    if op_args.get('as_file', False) or '.' in newroot:
        newfile = newroot
    if canCopy(fromfile, newfile, **op_args):
        if op_args.get('verbose', False):
            log.info('Copying {} -> {}'.format(fromfile, newfile))
        shutil.copy2(fromfile, newfile)


def copytree(fromdir, todir, ignore=None, verbose=False, ignore_mtime=False):
    optree(fromdir, todir, single_copy, ignore,
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

REG_DRIVELETTER = re.compile(r'^([A-Z]):\\')


def cygpath(inpath):
    chunks = inpath.split('\\')
    chunks[0] = chunks[0].lower()[:-1]
    return '/cygdrive/' + '/'.join(chunks)


def decompressFile(archive):
    '''
    Decompresses the file to the current working directory.
    '''
    #print('Trying to decompress ' + archive)
    tarpath=ENV.which('tar',skip_paths=['mingw']) # MinGW tar is broken, just throws errors (Jan 9 2016)
    if archive.endswith('.tar.gz') or archive.endswith('.tgz'):
        if PLATFORM == 'Windows' and 'cygwin' in tarpath.lower():
            archive = cygpath(archive)
        cmd([tarpath, 'xzf', archive], echo=True, show_output=False, critical=True)
        return True
    elif archive.endswith('.tar.bz2') or archive.endswith('.tbz'):
        if PLATFORM == 'Windows' and 'cygwin' in tarpath.lower():
            archive = cygpath(archive)
        cmd([tarpath, 'xjf', archive], echo=True, show_output=False, critical=True)
        return True
    elif archive.endswith('.tar.xz'):
        if PLATFORM == 'Windows' and 'cygwin' in tarpath.lower():
            archive = cygpath(archive)
        cmd([tarpath, 'xJf', archive], echo=True, show_output=False, critical=True)
        return True
    elif archive.endswith('.tar.7z'):
        cmd(['7za', 'x', '-aoa', archive], echo=True, show_output=False, critical=True)
        if PLATFORM == 'Windows' and 'cygwin' in tarpath.lower():
            archive = cygpath(archive)
        cmd([tarpath, 'xf', archive[:-3]], echo=True, show_output=False, critical=True)
        os.remove(archive[:-3])
        return True
    elif archive.endswith('.7z'):
        if PLATFORM == 'Windows':
            archive = cygpath(archive)
        cmd(['7za', 'x', '-aoa', archive], echo=True, show_output=False, critical=True)
    elif archive.endswith('.zip'):
        # unzip is unstable on Windows.
        #cmd(['unzip', archive[:-4]], echo=True, show_output=False, critical=True)
        with zipfile.ZipFile(archive) as arch:
            arch.extractall('.')
        return True
    elif archive.endswith('.rar'):
        # if PLATFORM == 'Windows':
        #    archive = cygpath(archive)
        cmd(['7z', 'x', '-aoa', archive], echo=True, show_output=False, critical=True)
    else:
        log.critical(u'Unknown file extension: %s', archive)
    return False


ENV = BuildEnv()

# Platform-specific extensions
if platform.system() == 'Windows':
    from buildtools._os_utils_win32 import WindowsEnv
else:
    import buildtools._os_utils_linux
    buildtools._os_utils_linux.cmd_output = cmd_output
    from buildtools._os_utils_linux import GetDpkgShlibs, InstallDpkgPackages, DpkgSearchFiles
