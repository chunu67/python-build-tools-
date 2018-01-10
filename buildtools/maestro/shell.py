import subprocess

from buildtools import os_utils
from buildtools.maestro.base_target import BuildTarget

class CommandBuildTarget(BuildTarget):
    BT_LABEL = 'SHELL'
    #BT_COLOR = 'red'

    def __init__(self, targets, files, cmd, show_output=False, echo=False, dependencies=[], provides=[], name=None):
        self.cmd = cmd
        self.show_output = show_output
        self.echo = echo
        newt = []
        for x in targets:
            if x.startswith('@'):
                x = self.genVirtualTarget(x[1:])
            newt.append(x)
        super().__init__(newt, files, dependencies, provides, name or subprocess.list2cmdline(cmd))

    def get_config(self):
        return {
            'cmd': self.cmd,
            'show_output': self.show_output,
            'echo': self.echo
        }

    def build(self):
        os_utils.cmd(self.cmd, show_output=self.show_output, echo=self.echo, critical=True, globbify=False)
        for t in self.provides():
            self.touch(t)
