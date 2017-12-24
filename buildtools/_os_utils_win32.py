'''
Windows-Specific os_utils.

Copyright (c) 2015 - 2017 Rob "N3X15" Nelson <nexisentertainment@gmail.com>

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
import sys
import codecs

from buildtools.bt_logging import log

cmd_output = None
ENV = None

class WindowsEnv:
    """Utility class to get/set windows environment variable"""

    def __init__(self, scope):
        log.info('Python version: 0x%0.8X' % sys.hexversion)
        if sys.hexversion > 0x03000000:
            import winreg #IGNORE:import-error
        else:
            import _winreg as winreg #IGNORE:import-error
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

        import win32api #IGNORE:import-error
        import win32con #IGNORE:import-error
        assert win32api.SendMessage(win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE, 0, 'Environment')

        """
        # For some strange reason, calling SendMessage from the current process
        # doesn't propagate environment changes at all.
        # TODO: handle CalledProcessError (for assert)
        subprocess.check_call('''\"%s" -c "import win32api, win32con; assert win32api.SendMessage(win32con.HWND_BROADCAST, win32con.WM_SETTINGCHANGE, 0, 'Environment')"''' % sys.executable)
        """

def getVSVars(vspath, arch='x86', batfile=None, env=ENV):
    '''
    :param batfile:
        Location to place the batch file.
    '''
    if batfile is None:
        batfile='getvsvars.bat'
    #C:\Program Files (x86)\Microsoft Visual Studio 14.0\VC\bin\vcvars32.bat
    with codecs.open(batfile,'w', encoding='utf-8') as f:
        f.write('@echo off\r\n')
        f.write('echo call "{}\\vcvarsall.bat" {}\r\n'.format(vspath,arch))
        f.write('call "{}\\vcvarsall.bat" {}\r\n'.format(vspath,arch))
        f.write('echo ###\r\n')
        f.write('echo INCLUDE=%INCLUDE%\r\n')
        f.write('echo LIB=%LIB%\r\n')
        f.write('echo LIBPATH=%LIBPATH%\r\n')
        f.write('echo PATH=%PATH%\r\n')
    stdout, stderr = cmd_output(['cmd', '/c', batfile], echo=True, critical=True)
    inVSVars=False
    for line in (stdout + stderr).decode('utf-8').splitlines():
        #print(line)
        if inVSVars and '=' in line:
            k,v=line.split('=',1)
            ENV.set(k,v,noisy=True)
        if line == '###': inVSVars=True
