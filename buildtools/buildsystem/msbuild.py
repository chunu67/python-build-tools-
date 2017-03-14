'''
MSBuild wrapper

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
from buildtools import ENV, os_utils
class MSBuild(object):
    def __init__(self):
        # ["msbuild", self.__solution, "/m", "/property:Configuration=Release"]
        self.solution=''
        self.configuration=None
        self.platform=None

    def run(self, MSBUILD='msbuild', project=None, env=ENV):
        cmd = ["msbuild", self.solution, "/m"]
        props=[]
        if self.configuration is not None:
            props.append("Configuration="+self.configuration)
        if self.platform is not None:
            props.append('Platform='+self.platform)
        if len(props)>0:
            cmd.append('/p:'+';'.join(props))
        if project is not None:
            cmd.append("/target:"+project)
        os_utils.cmd(cmd,env=env,echo=True,critical=True,show_output=True)
