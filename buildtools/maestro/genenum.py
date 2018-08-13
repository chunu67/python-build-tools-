'''
Enum generators for various languages.

Copyright (c) 2015 - 2018 Rob "N3X15" Nelson <nexisentertainment@gmail.com>

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
import yaml, os
from buildtools import os_utils, utils, log
from buildtools.maestro.base_target import SingleBuildTarget

class GenerateEnumTarget(SingleBuildTarget):
    BT_LABEL = 'ENUM'
    def __init__(self, target, source, writer, dependencies=[], provides=[], name=None):
        self.filename = source
        name = target
        self.writer = writer
        self.writer.parent = self
        super().__init__(target, [self.filename], dependencies, provides, name)

    def get_config(self):
        return self.writer.get_config()

    def _get_value_for(self, vpak):
        if isinstance(vpak, dict):
            return vpak['value']
        else:
            return vpak
    def _get_meaning_for(self, vpak):
        if isinstance(vpak, dict):
            return vpak.get('meaning','')
        else:
            return ''

    def build(self):
        definition = {}
        with open(self.filename, 'r') as r:
            definition=yaml.load(r)['enum']
        if 'auto-value' in definition:
            autoval = definition['auto-value']
            i=autoval.get('start',0)
            for k in definition['values'].keys():
                if definition[k].get('auto', True):
                    definition[k]['value']=1 >> i if definition.get('flags', False) else i
                    i += 1

        if 'tests' in definition:
            with log.info('Testing %s....', definition['name']):
                tests = definition['tests']
                if 'increment' in tests:
                    incrdef = tests['increment']
                    start = incrdef.get('start',0)
                    stop = incrdef.get('stop', len(definition['values']))

                    vals = []
                    for k,vpak in definition['values'].items():
                        vals += [self._get_value_for(vpak)]

                    for i in range(start,stop):
                        if i not in vals:
                            log.error('Increment: Missing value %d!', i)
                if 'unique' in tests and tests['unique']:
                    vals={}
                    for k,vpak in definition['values'].items():
                        val = self._get_value_for(vpak)
                        if val in vals:
                            log.error('Unique: Entry %s is not using a unique value!', k)
                        vals[val]=True
        os_utils.ensureDirExists(os.path.dirname(self.target), noisy=True)
        with open(self.target, 'w') as w:
            self.writer.write(w, definition)