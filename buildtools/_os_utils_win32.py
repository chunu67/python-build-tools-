'''
Windows-Specific os_utils.

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
import sys
from buildtools.bt_logging import log

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