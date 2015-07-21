
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