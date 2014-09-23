import os

from buildtools.os_utils import cmd
    
class Ant(object):
    def __init__(self):
        self.defines = []
        
    def AddDepend(self, depend):
        self.dependencies += [depend]
        
    def Build(self, file, targets=['target'], ant='ant'):
        cmdline = [ant]
            
        cmdline += ['-file', target]
        
        for k,v in self.defines.items():
            cmdline += ['-D{}={}'.format(k,v)]
            
        cmdline += targets
        
        cmd(cmdline, critical=True, echo=True)