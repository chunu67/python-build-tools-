import os
from buildtools.bt_logging import log
from buildtools import os_utils

class CCompiler(object):
    def __init__(self, output, template=None):
        self.files=[]
        self.output=output
        self.cflags=None

        self.compiler=''
        self.linker=''

    def compile(self):
        return

class WindowsCCompiler(CCompiler):
    def __init__(self,output,template=None):
        super(WindowsCCompiler,self).__init__(output,template)
        if template is not None:
            self.cflags=template.cflags
        if self.cflags is None:
            self.cflags = ["-nologo", "-O2", "-MD"]

        self.compiler='cl'
        self.linker='link'

    def compile(self):
        ofiles=[]
        for filename in self.files:
            of = "{}.obj".format(os.path.splitext(filename)[0])
            if os_utils.canCopy(filename, of): # Checks mtime.
                os_utils.cmd([self.compiler,'-c']+self.cflags+['-Fo',filename], critical=True, show_output=True, echo=True)
            ofiles.append(of)
        os_utils.cmd([self.linker,'/lib','/nologo','/out:'+self.output]+ofiles, critical=True, show_output=True, echo=True)
