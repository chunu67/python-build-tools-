'''
BLURB GOES HERE.

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
import codecs
import os
from tqdm import tqdm

from buildtools import log, os_utils
from buildtools.maestro.base_target import SingleBuildTarget


class CoffeeBuildTarget(SingleBuildTarget):
    BT_TYPE = 'CoffeeScript'
    BT_LABEL = 'COFFEE'

    def __init__(self, target=None, files=[], dependencies=[], coffee_opts=['--no-header','-bcM'], coffee_executable=None):
        if coffee_executable is None:
            coffee_executable = os_utils.which('coffee')
            if coffee_executable is None:
                log.warn('Unable to find coffee on this OS.  Is it in PATH?  Remember to run `gem install -g coffee-script`!')
        self.coffee_executable = coffee_executable
        super(CoffeeBuildTarget, self).__init__(target, files, dependencies)
        self.coffee_opts=coffee_opts

    def get_config(self):
        return {
            'opts': self.coffee_opts,
            'exec': self.coffee_executable,
        }

    def build(self):
        os_utils.ensureDirExists(os.path.join('tmp', os.path.dirname(self.target)))
        os_utils.ensureDirExists(os.path.dirname(self.target))
        coffeefile = os.path.join('tmp', self.target)
        coffeefile, _ = os.path.splitext(coffeefile)
        coffeefile += '.coffee'
        coffeefile = os.path.abspath(coffeefile)
        with codecs.open(coffeefile, 'w', encoding='utf-8-sig') as outf:
            tq = tqdm(self.files, desc='Concatenating...', leave=False)
            for infilename in tq:
                with codecs.open(infilename, 'r', encoding='utf-8-sig') as inf:
                    for line in inf:
                        outf.write(line.rstrip() + "\n")
            tq.close()
        os_utils.cmd([self.coffee_executable] + self.coffee_opts + ['--output', os.path.dirname(self.target), coffeefile], critical=True, echo=False, show_output=True)

class JS2CoffeeBuildTarget(SingleBuildTarget):
    BT_TYPE = 'JS2Coffee'
    BT_LABEL = 'JS2COFFEE'
    def __init__(self, target=None, files=[], dependencies=[], j2coffee_opts=['-i', '2'], js2coffee_path=None):
        if js2coffee_path is None:
            js2coffee_path = os_utils.which('js2coffee')
            if js2coffee_path is None:
                log.warn('Unable to find coffee on this OS.  Is it in PATH?  Remember to run `gem install -g js2coffee`!')
        self.js2coffee_path = js2coffee_path
        super(JS2CoffeeBuildTarget, self).__init__(target, files, [os.path.abspath(__file__)]+dependencies)
        self.js2coffee_opts = j2coffee_opts

    def get_config(self):
        return {
            'opts': self.js2coffee_opts,
            'exec': self.js2coffee_path,
        }

    def build(self):
        os_utils.ensureDirExists(os.path.dirname(self.target))
        stdout, stderr = os_utils.cmd_output([self.js2coffee_path]+self.files+self.js2coffee_opts, echo=False, critical=True)
        if stderr.strip() != '':
            log.error(stderr)
        with codecs.open(self.target, 'w', encoding='utf-8-sig') as outf:
            outf.write(stdout)
