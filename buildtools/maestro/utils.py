import codecs
import os
import re
import shutil

from buildtools import log, os_utils
from buildtools.maestro.base_target import BuildTarget


class ReplaceTextTarget(BuildTarget):
    BT_TYPE = 'ReplaceText'

    def __init__(self, target=None, filename=None, replacements=None, dependencies=[]):
        self.replacements = replacements
        self.subject=filename
        super(ReplaceTextTarget, self).__init__(target, [filename], dependencies)

    def serialize(self):
        dat = super(ReplaceTextTarget, self).serialize()
        dat['replacements'] = self.replacements
        return dat

    def deserialize(self,data):
        super(ReplaceTextTarget, self).deserialize(data)
        self.replacements=data['replacements']
        self.subject=data['files'][0]

    def build(self):
        if self.checkMTimes(self.files + self.dependencies, self.target, self.replacements):
            with log.info('Writing %s...', self.target):
                os_utils.ensureDirExists(os.path.dirname(self.target))
                with codecs.open(self.subject, 'r') as inf:
                    with codecs.open(self.target + '.out', 'w', encoding='utf-8') as outf:
                        for line in inf:
                            for needle, replacement in self.replacements.items():
                                line = re.sub(needle, replacement, line)
                            outf.write(line)
                shutil.move(self.target + '.out', self.target)
