import os

from buildtools.os_utils import cmd
    
class FPM(object):
    def __init__(self):
        self.name = ''
        self.version = ''
        self.input_type = ''
        self.output_type = ''
        self.workdir = ''
        self.increment = 0
        
        self.dependencies = []
        self.conflicts = []
        self.replaces = []
        self.provides = []
        self.inputs = []
        
        self.filebinds = []
    
    def LoadControl(self, filename):
        '''
        Load Debian CONTROL file.
        '''
        with open(filename, 'r') as f:
            for line in f:
                directive, content = line.split(':', 1)
                func = getattr(self, '_handle_' + directive.lower())
                if func: func(content.strip(), line)
    
    def _handle_package(self, content, line):
        self.name = content
        
    def _handle_version(self, content, line):
        self.version = content
        
    def _handle_section(self, content, line):
        return  # web
        
    def _handle_priority(self, content, line):
        return  # optional
    
    def _handle_architecture(self, content, line):
        self.architecture = content
        
    def _handle_essential(self, content, line):
        return  # yes/no
    
    def _handle_depends(self, content, line):
        self.dependencies = [x.strip() for x in content.split(',')]
        
    def _handle_maintainer(self, content, line):
        self.maintainer = content
        
    def _handle_description(self, content, line):
        self.description = content
        
    def AddDepend(self, depend):
        self.dependencies += [depend]
        
    def Build(self, target_file, fpm='fpm'):
        cmdline = [fpm]
            
        cmdline += ['-s', self.input_type]
        cmdline += ['-t', self.output_type]
        cmdline += ['-C', self.workdir]
        cmdline += ['-p', target_file]
        cmdline += ['-n', self.name]
        cmdline += ['-v', self.version]
        cmdline += ['-a', self.architecture]
        
        if self.maintainer != '':cmdline += ['-m', self.maintainer]
        if self.description != '':cmdline += ['--description', self.description]
        if self.iteration > 0: cmdline += ['--iteration', self.iteration]
        
        for dep in self.dependencies:
            cmdline += ['-d', dep]
            
        for provided in self.provides:
            cmdline += ['--provides', provided]
            
        for conflict in self.conflicts:
            cmdline += ['--conflicts', conflict]
            
        for replacee in self.replaces:
            cmdline += ['--replaces', replacee]
            
        for inp in self.inputs:
            cmdline += [inp]
            
        cmd(cmdline, critical=True, echo=True)
