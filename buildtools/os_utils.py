import os
import sys
import glob
import subprocess
import shutil
import platform
import time
import re
import threading
import select
from twisted.internet import reactor

from buildtools.bt_logging import log
from subprocess import CalledProcessError
import psutil
from twisted.internet.protocol import ProcessProtocol

buildtools_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
scripts_dir = os.path.join(buildtools_dir, 'scripts')

REG_EXCESSIVE_WHITESPACE = re.compile('\s{2,}')

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


def InstallDpkgPackages(packages):
    import apt #IGNORE:import-error
    with log.info('Checking dpkg packages...'):
        cache = apt.Cache()
        num_changes = 0
        with cache.actiongroup():
            for pkg in packages:
                if pkg not in cache:
                    log.critical('UNKNOWN APT PACKAGE {}!'.format(pkg))
                    sys.exit(1)
                package = cache[pkg]
                if not package.is_installed:
                    package.mark_install()
                    num_changes += 1
        if num_changes == 0:
            log.info('No changes required, skipping.')
            return

        cache.commit(apt.progress.text.AcquireProgress(),
                     apt.progress.base.InstallProgress())


def GetDpkgShlibs(files):
    deps = {}
    stdout, stderr = cmd_output(['perl', os.path.join(scripts_dir, 'dpkg-dump-shpkgs.pl')] + files, critical=True)
    if stdout or stderr:
        for line in (stdout + stderr).split('\n'):
            line = line.strip()
            if line == '':
                continue
            # dpkg-dump-shpkgs.pl: warning: binaries to analyze should already
            # be installed in their package's directory
            if 'dpkg-dump-shpkgs.pl:' in line:
                (_, msgtype, msg) = [x.strip() for x in line.split(':')]
                if msg == 'binaries to analyze should already be installed in their package\'s directory':
                    continue
                if msgtype == 'warning':
                    log.warning(msg)
                elif msgtype == 'error':
                    log.error(msg)
                continue
            elif line.startswith('shlibs:'):
                # shlibs:Depends=libboost-context1.55.0,
                # libboost-filesystem1.55.0, libboost-program-options1.55.0,
                # ...
                lc = line.split('=', 1)
                assert len(lc) == 2
                assert not lc[0][7:].startswith(':')
                deps[lc[0][7:]] = [x.strip() for x in lc[1].split(',')]
            else:
                log.warning('UNHANDLED: %s', line)
    return deps


def DpkgSearchFiles(files):
    '''Find packages for a given set of files.'''

    stdout, stderr = cmd_output(['dpkg', '--search'] + files, critical=True)

    '''
    libc6:amd64: /lib/x86_64-linux-gnu/libc-2.19.so
    libcap2:amd64: /lib/x86_64-linux-gnu/libcap.so.2
    libcap2:amd64: /lib/x86_64-linux-gnu/libcap.so.2.24
    libc6:amd64: /lib/x86_64-linux-gnu/libcidn-2.19.so
    libc6:amd64: /lib/x86_64-linux-gnu/libcidn.so.1
    libcomerr2:amd64: /lib/x86_64-linux-gnu/libcom_err.so.2
    libcomerr2:amd64: /lib/x86_64-linux-gnu/libcom_err.so.2.1
    libc6:amd64: /lib/x86_64-linux-gnu/libcrypt-2.19.so
    libcryptsetup4:amd64: /lib/x86_64-linux-gnu/libcryptsetup.so.4
    libcryptsetup4:amd64: /lib/x86_64-linux-gnu/libcryptsetup.so.4.6.0
    libc6:amd64: /lib/x86_64-linux-gnu/libcrypt.so.1
    libc6:amd64: /lib/x86_64-linux-gnu/libc.so.6
    '''

    packages = []
    if stdout or stderr:
        for line in (stdout + stderr).split('\n'):
            line = line.strip()
            if line == '':
                continue

            chunks = line.split()
            # libc6:amd64: /lib/x86_64-linux-gnu/libc.so.6
            if len(chunks) == 2:
                pkgName = chunks[0][:-1]  # Strip ending colon
                if pkgName not in packages:
                    packages += [pkgName]
            else:
                log.error(
                    'UNHANDLED dpkg --search LINE (len == %d): "%s"', len(chunks), line)

    return packages


class WindowsEnv:
    """Utility class to get/set windows environment variable"""
    def __init__(self, scope):
        log.info('Python version: 0x%0.8X' % sys.hexversion)
        if sys.hexversion > 0x03000000:
            import winreg
        else:
            import _winreg as winreg
        self.winreg = winreg

        assert scope in ('user', 'system')
        self.scope = scope
        if scope == 'user':
            self.root = winreg.HKEY_CURRENT_USER
            self.subkey = 'Environment'
        else:
            self.root = winreg.HKEY_LOCAL_MACHINE
            self.subkey = r'SYSTEM\CurrentControlSet\Control\Session Manager\Environment'

    def get(self, name, default=None):
        with self.winreg.OpenKey(self.root, self.subkey, 0, self.winreg.KEY_READ) as key:
            try:
                value, _ = self.winreg.QueryValueEx(key, name)
            except WindowsError:
                value = default
            return value

    def set(self, name, value):
        # Note: for 'system' scope, you must run this as Administrator
        with self.winreg.OpenKey(self.root, self.subkey, 0, self.winreg.KEY_ALL_ACCESS) as key:
            self.winreg.SetValueEx(
                key, name, 0, self.winreg.REG_EXPAND_SZ, value)

        import win32api
        import win32con
        assert win32api.SendMessage(win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE, 0, 'Environment')

        """
        # For some strange reason, calling SendMessage from the current process
        # doesn't propagate environment changes at all.
        # TODO: handle CalledProcessError (for assert)
        subprocess.check_call('''\"%s" -c "import win32api, win32con; assert win32api.SendMessage(win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE, 0, 'Environment')"''' % sys.executable)
        """


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
        self.label=label
        
    def toStr(self, entryVars):
        return self.label.format(**entryVars)

class TimeExecution(object):

    def __init__(self, label):
        self.start_time = None
        self.vars={}
        if isinstance(label, str):
            self.label = DeferredLogEntry('Completed in {elapsed}s - {label}')
            self.vars['label']=label
        elif isinstance(label, DeferredLogEntry):
            self.label = label

    def __enter__(self):
        self.start_time = clock()
        return self

    def __exit__(self, typeName, value, traceback):
        self.vars['elapsed']=secondsToStr(clock() - self.start_time)
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
            os.chdir(self.chdir)
            if not self.quiet:
                log.info('cd ' + self.chdir)
        except:
            log.critical('Failed to chdir to {}.'.format(self.chdir))
            sys.exit(1)
        return self

    def __exit__(self, typeName, value, traceback):
        try:
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


class _PipeReader(ProcessProtocol):
    def __init__(self, asc, process, stdout_callback, stderr_callback, exit_callback):
        self._asyncCommand = asc
        self._cb_stdout = stdout_callback
        self._cb_stderr = stderr_callback
        self._cb_exit = exit_callback
        self.process = process
        
        self.buf={
            'stdout':'',
            'stderr':''
        }
    def _processData(self,bid,cb,data):
        log.debug('%s: Received %d bytes',bid,len(data))
        for b in data:
            if b != '\n' and b != '\r' and b != '':
                self.buf[bid] += b
            else:
                buf = self.buf[bid].strip()
                cb(self._asyncCommand,buf)
                self.buf[bid]=''
                
    def _getRemainingBuf(self):
        return self.buf['stdout']+self.buf['stderr']
                
    def outReceived(self, data):
        self._processData('stdout',self._cb_stdout,data)
                
    def errReceived(self, data):
        self._processData('stderr',self._cb_stderr,data)
        
    def inConnectionLost(self):
        log.warn('[%s#%d] Lost connection to stdin.',self._asyncCommand.commandName, self.transport.pid)
        
    def errConnectionLost(self):
        log.warn('[%s#%d] Lost connection to stderr.',self._asyncCommand.commandName, self.transport.pid)
        
    def processEnded(self, code):
        self._asyncCommand.exit_code=code
        self._cb_exit(code, self._getRemainingBuf())


class AsyncCommand(object):
    def __init__(self, command, stdout=None, stderr=None, echo=False, env=None, PTY=False, refName=None):
        self.echo = echo
        self.command = command
        self.PTY=PTY
        self.stdout_callback = stdout if stdout is not None else self.default_stdout
        self.stderr_callback = stderr if stderr is not None else self.default_stderr

        self.env = _cmd_handle_env(env)
        self.command = _cmd_handle_args(command)

        self.child = None
        self.refName = self.commandName = os.path.basename(self.command[0])
        if refName:
            self.refName=refName

        self.exit_code = None
        self.exit_code_handler = self.default_exit_handler

        self.log = log

        self.pipe_reader = None

    def default_exit_handler(self, code, remainingBuf):
        if code != 0:
            if code < 0:
                strerr = '%s: Received signal %d' % (abs(self.child.returncode))
                if code < -100:
                    strerr += ' (?!)'
                self.log.error(strerr,self.refName)
            else:
                self.log.warning('%s exited with code %d: %s', self.refName, remainingBuf)
        else:
            self.log.info('%s has exited normally.', self.refName)

    def default_stdout(self, ascmd, buf):
        ascmd.log.info('[%s] %s', ascmd.refName, buf)

    def default_stderr(self, ascmd, buf):
        ascmd.log.error('[%s] %s', ascmd.refName, buf)

    def Start(self):
        if self.echo:
            self.log.info('[ASYNC] $ "%s"', '" "'.join(self.command))
        pr = _PipeReader(self, self.child, self.stdout_callback, self.stderr_callback,self.exit_code_handler)
        self.child = reactor.spawnProcess(pr, self.command[0], self.command[1:], env=self.env,usePTY=self.PTY)
        if self.child is None:
            self.log.error('Failed to start %r.', ' '.join(self.command))
            return False
        reactorThread = threading.Thread(target=reactor.run, args=(False,))
        reactorThread.daemon(True)
        reactorThread.start()
        return True

    def Stop(self):
        if find_process(self.child.pid):
            os.kill(self.child.pid)

    def WaitUntilDone(self):
        while self.IsRunning():
            time.sleep(1)
        return self.exit_code

    def IsRunning(self):
        return self.exit_code is not None

def async_cmd(command, stdout=None, stderr=None, env=None):
    ascmd = AsyncCommand(command, stdout=stdout, stderr=stderr, env=env)
    ascmd.Start()
    return ascmd


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
            raise e
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
    :returns (stdout,stderr)
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
        ignore=[]
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
                log.info('mkdir {}'.format(newroot))
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

ENV = BuildEnv()
