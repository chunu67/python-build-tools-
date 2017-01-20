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
