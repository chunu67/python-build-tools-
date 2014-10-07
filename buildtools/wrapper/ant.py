import os

from buildtools.os_utils import cmd
    
class Ant(object):
    def __init__(self):
        self.defines = {}
        self.propertyfiles=[]
        
    def AddDefine(self, k, v):
        self.defines[k]=v
        
    def AddPropertyFile(self, filename):
        self.propertyfiles += [filename]
        
    def Build(self, file, targets=['target'], ant='ant'):
        cmdline = [ant]
            
        cmdline += ['-file', target]
        
        for k, v in sorted(self.defines.items()):
            cmdline += ['-D{}={}'.format(k, v)]
            
        for filename in self.propertyfiles:
            cmdline += ['-propertyfile',filename]
            
        cmdline += targets
        
        return cmd(cmdline, critical=True, echo=True)
