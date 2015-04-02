import os
import sys
import glob
import subprocess
import shutil
import platform
import time
import re
import threading

if sys.platform.startswith('linux'):
    import fcntl

from buildtools.bt_logging import log
from compileall import expand_args
from subprocess import CalledProcessError

buildtools_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
scripts_dir = os.path.join(buildtools_dir, 'scripts')


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
    import apt
    with log.info('Checking dpkg packages...'):
        cache = apt.Cache()
        num_changes = 0
        with cache.actiongroup():
            for pkg in packages:
                if not cache.has_key(pkg):
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
    stdout, stderr = cmd_output(
        ['perl', os.path.join(scripts_dir, 'dpkg-dump-shpkgs.pl')] + files, critical=True)
    if stdout or stderr:
        for line in (stdout + stderr).split('\n'):
            line = line.strip()
            if line == '':
                continue
            # dpkg-dump-shpkgs.pl: warning: binaries to analyze should already
            # be installed in their package's directory
            if 'dpkg-dump-shpkgs.pl:' in line:
                (scriptname, msgtype, msg) = [x.strip()
                                              for x in line.split(':')]
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
        from subprocess import check_call
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
        assert win32api.SendMessage(
            win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE, 0, 'Environment')

        """
        # For some strange reason, calling SendMessage from the current process
        # doesn't propagate environment changes at all.
        # TODO: handle CalledProcessError (for assert)
        subprocess.check_call('''\
"%s" -c "import win32api, win32con; assert win32api.SendMessage(win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE, 0, 'Environment')"''' % sys.executable)
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


class TimeExecution(object):

    def __init__(self, label):
        self.start_time = None
        self.label = label

    def __enter__(self):
        self.start_time = clock()
        return self

    def __exit__(self, type, value, traceback):
        log.info(
            '  Completed in {1}s - {0}'.format(self.label, secondsToStr(clock() - self.start_time)))
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


def which(program):
    import os

    def is_exe(fpath):
        if sys.platform == 'win32':
            if not fpath.endswith('.exe'):
                fpath += '.exe'
        return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

    fpath, fname = os.path.split(program)
    if fpath:
        if is_exe(program):
            return program
    else:
        for path in os.environ["PATH"].split(os.pathsep):
            path = path.strip('"')
            exe_file = os.path.join(path, program)
            if is_exe(exe_file):
                return exe_file

    return None


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
    for arg in command:  # 1:
        arg = str(arg)
        if '*' in arg or '?' in arg:
            new_args += glob.glob(arg)
        elif '~' in arg:
            new_args += [os.path.expanduser(arg)]
        else:
            new_args += [arg]
    return new_args


class _StreamReader(threading.Thread):

    def __init__(self, asc, fd, callback):
        assert callable(fd.readline)
        threading.Thread.__init__(self)
        self._asyncCommand = asc
        self._fd = fd
        self._cb = callback
        
        #if sys.platform.startswith('linux'):
        #    # Disable buffering
        #    fd = self._fd.fileno()
        #    fl = fcntl.fcntl(fd, fcntl.F_GETFL)
        #    fcntl.fcntl(fd, fcntl.F_SETFL, fl | os.O_NONBLOCK)

    def _getChild(self):
        return self._asyncCommand.child
    def run(self):
        '''The body of the tread: read lines and put them on the queue.'''
        #for line in iter(self._fd.readline, ''):
        #    self._cb(self._asyncCommand, line.strip())
        
        buf = ''
        while True:
            if self._asyncCommand.exit_code is not None:
                return
            b = self._fd.read(1)
            if b == '':
                pollResult = self._getChild().poll()
                if pollResult != None:
                    self._asyncCommand.exit_code = self._getChild().returncode
                    self._asyncCommand.exit_code_handler(buf)
                    return
                continue
            if b != '\n' and b != '\r':
                buf += b
            else:
                buf = buf.strip()
                if buf != '':
                    self._cb(self._asyncCommand, buf)
                    buf = ''

    def eof(self):
        '''Check whether there is no more content to expect.'''
        return not self.is_alive()


class AsyncCommand(object):

    def __init__(self, command, stdout=None, stderr=None, echo=False, env=None, critical=False):
        self.echo = echo
        self.command = command
        self.stdout_callback = stdout if stdout is not None else self.default_stdout
        self.stderr_callback = stderr if stderr is not None else self.default_stderr

        self.env = _cmd_handle_env(env)
        self.command = _cmd_handle_args(command)

        self.child = None
        self.commandName = os.path.basename(self.command[0])

        self.exit_code = None
        self.exit_code_handler = self.default_exit_handler

        self.log = log
        
        self.stdout_thread=None
        self.stderr_thread=None

    def default_exit_handler(self, buf):
        if self.child.returncode != 0:
            if self.child.returncode < 0:
                strerr = 'Received signal %d' % (abs(self.child.returncode))
                if self.child.returncode < -100:
                    strerr += ' (?!)'
                self.log.error(strerr)
            else:
                self.log.warning(
                    '%s exited with code %d: %s', self.commandName, self.exit_code, buf)
        else:
            self.log.info('%s process has exited normally.', self.commandName)

    def default_stdout(self, ascmd, buf):
        ascmd.log.info('[%s] %s', ascmd.commandName, buf)

    def default_stderr(self, ascmd, buf):
        ascmd.log.error('[%s] %s', ascmd.commandName, buf)

    def Start(self):
        if self.echo:
            self.log.info('(ASYNC) $ ' + ' '.join(self.command))
        self.child = subprocess.Popen(
            self.command, shell=True, env=self.env, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if self.child is None:
            self.log.error('Failed to start %r.', ' '.join(self.command))
            return False
        self.stdout_thread = _StreamReader(self, self.child.stdout, self.stdout_callback)
        self.stdout_thread.start()
        self.stderr_thread = _StreamReader(self, self.child.stderr, self.stderr_callback)
        self.stderr_thread.start()
        return True

    def WaitUntilDone(self):
        while not self.stdout_thread.eof() or not self.stderr_thread.eof():
            time.sleep(1)
        self.stderr_thread.join()
        self.stdout_thread.join()
        return self.exit_code

    def IsRunning(self):
        return self.exit_code != None

    def _process_stream(self, stream, callback):
        buf = ''
        while True:
            if self.exit_code is not None:
                return
            b = stream.read(1)
            if b == '':
                pollResult = self.child.poll()
                if pollResult != None:
                    self.exit_code = self.child.returncode
                    self.exit_code_handler(buf)
                    return
                continue
            if b != '\n' and b != '\r':
                buf += b
            else:
                buf = buf.strip()
                if buf != '':
                    callback(self, buf)
                    buf = ''


def async_cmd(command, stdout=None, stderr=None, env=None, critical=False):
    ascmd = AsyncCommand(
        command, stdout=stdout, stderr=stderr, env=env, critical=critical)
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
        output = subprocess.check_output(
            command, env=new_env, stderr=subprocess.STDOUT)
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


def cmd_daemonize(command, echo=False, env=None, show_output=True, critical=False):
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


def copytree(fromdir, todir, ignore=[], verbose=False, ignore_mtime=False):
    optree(fromdir, todir, _op_copy, ignore,
           verbose=verbose, ignore_mtime=ignore_mtime)


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


def safe_rmtree(dir):
    for root, dirs, files in os.walk(dir, topdown=False):
        for name in files:
            os.remove(os.path.join(root, name))
        for name in dirs:
            os.rmdir(os.path.join(root, name))

REG_EXCESSIVE_WHITESPACE = re.compile('\s{2,}')


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
