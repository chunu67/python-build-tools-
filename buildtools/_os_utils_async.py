
import sys
import os
from buildtools.bt_logging import log

cmd_output = None

class _PipeReader(ProcessProtocol):

    def __init__(self, asc, process, stdout_callback, stderr_callback, exit_callback):
        self._asyncCommand = asc
        self._cb_stdout = stdout_callback
        self._cb_stderr = stderr_callback
        self._cb_exit = exit_callback
        self.process = process

        self.buf = {
            'stdout': '',
            'stderr': ''
        }
        self.debug = False

    def _processData(self, bid, cb, data):
        if self.debug:
            log.info('%s %s: Received %d bytes', self._logPrefix(), bid, len(data))
        for b in data:
            if b != '\n' and b != '\r' and b != '':
                self.buf[bid] += b
            else:
                buf = self.buf[bid].strip()
                if self.debug:
                    log.info('buf = %r', buf)
                if buf != '':
                    cb(self._asyncCommand, buf)
                self.buf[bid] = ''

    def _getRemainingBuf(self):
        return self.buf['stdout'] + self.buf['stderr']

    def outReceived(self, data):
        self._processData('stdout', self._cb_stdout, data)

    def errReceived(self, data):
        self._processData('stderr', self._cb_stderr, data)

    def _logPrefix(self):
        return '[{}#{}]'.format(self._asyncCommand.refName, self.transport.pid)

    def inConnectionLost(self):
        log.warn('%s Lost connection to stdin.', self._logPrefix())

    def errConnectionLost(self):
        log.warn('%s Lost connection to stderr.', self._logPrefix())

    def processEnded(self, code):
        self._asyncCommand.exit_code = code
        self._cb_exit(code, self._getRemainingBuf())


class ReactorManager:
    instance = None

    @classmethod
    def Start(cls):
        if cls.instance is None:
            cls.instance = threading.Thread(target=reactor.run, args=(False,))
            cls.instance.daemon = True
            cls.instance.start()
            log.info('Twisted Reactor started.')

    @classmethod
    def Stop(cls):
        reactor.stop()
        log.info('Twisted Reactor stopped.')


class AsyncCommand(object):

    def __init__(self, command, stdout=None, stderr=None, echo=False, env=None, PTY=False, refName=None, debug=False):
        
        self.echo = echo
        self.command = command
        self.PTY = PTY
        self.stdout_callback = stdout if stdout is not None else self.default_stdout
        self.stderr_callback = stderr if stderr is not None else self.default_stderr

        self.env = _cmd_handle_env(env)
        self.command = _cmd_handle_args(command)

        self.child = None
        self.refName = self.commandName = os.path.basename(self.command[0])
        if refName:
            self.refName = refName

        self.exit_code = None
        self.exit_code_handler = self.default_exit_handler

        self.log = log

        self.pipe_reader = None
        self.debug = debug

    def default_exit_handler(self, code, remainingBuf):
        if code != 0:
            if code < 0:
                strerr = '%s: Received signal %d' % (abs(self.child.returncode))
                if code < -100:
                    strerr += ' (?!)'
                self.log.error(strerr, self.refName)
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
        pr = _PipeReader(self, self.child, self.stdout_callback, self.stderr_callback, self.exit_code_handler)
        pr.debug = self.debug
        self.child = reactor.spawnProcess(pr, self.command[0], self.command[1:], env=self.env, usePTY=self.PTY)
        if self.child is None:
            self.log.error('Failed to start %r.', ' '.join(self.command))
            return False
        ReactorManager.Start()
        return True

    def Stop(self):
        process = find_process(self.child.pid)
        if process:
            process.terminate()

    def WaitUntilDone(self):
        while self.IsRunning():
            time.sleep(1)
        return self.exit_code

    def IsRunning(self):
        return self.exit_code is not None


def async_cmd(command, stdout=None, stderr=None, env=None):
    # Lazy-load Twisted.
    # package twisted
    from twisted.internet import reactor
    from twisted.internet.protocol import ProcessProtocol
    
    ascmd = AsyncCommand(command, stdout=stdout, stderr=stderr, env=env)
    ascmd.Start()
    return ascmd