class SubprocessThrewError(Exception):
    def __init__(self, cmdline, errormsg):
        from buildtools.os_utils import _args2str
        self.cmdline=cmdline
        if type(self.cmdline) == list:
            self.cmdline = _args2str(self.cmdline)
        self.errormsg=errormsg

    def __str__(self):
        return f'Subprocess `{self.cmdline}` failed: {self.errormsg}'
