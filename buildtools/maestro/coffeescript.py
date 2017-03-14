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

from buildtools import log, os_utils
from buildtools.maestro.base_target import BuildTarget


class CoffeeBuildTarget(BuildTarget):
    BT_TYPE = 'CoffeeScript'

    def __init__(self, target=None, files=[], dependencies=[]):
        super(CoffeeBuildTarget, self).__init__(target, files, dependencies)

    def build(self):
        args = ['-bcM']  # m
        if self.checkMTimes(self.files + self.dependencies, self.target, args):
            os_utils.ensureDirExists(os.path.join('tmp', os.path.dirname(self.target)))
            os_utils.ensureDirExists(os.path.dirname(self.target))
            coffeefile = os.path.join('tmp', self.target)
            coffeefile, _ = os.path.splitext(coffeefile)
            coffeefile += '.coffee'
            coffeefile = os.path.abspath(coffeefile)
            with codecs.open(coffeefile, 'w', encoding='utf-8') as outf:
                for infilename in self.files:
                    with codecs.open(infilename, 'r') as inf:
                        for line in inf:
                            outf.write(line.rstrip() + "\n")
            log.info("COFFEE %s", self.target)
            os_utils.cmd([COFFEE] + args + ['--output', os.path.dirname(self.target), coffeefile], critical=True, echo=False, show_output=True)

COFFEE = os_utils.which('coffee')
if COFFEE is None:
    log.warn('Unable to find coffee on this OS.  Is it in PATH?  Remember to run `gem install coffee-script`!')
