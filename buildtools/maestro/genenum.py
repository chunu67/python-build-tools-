'''
Enum generators for various languages.

Copyright (c) 2015 - 2021 Rob "N3X15" Nelson <nexisentertainment@gmail.com>

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
import os

from ruamel.yaml import YAML
yaml = YAML(typ='safe', pure=True)

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

    def _get_for(self, vpak, key, default=''):
        if isinstance(vpak, dict):
            return vpak.get(key, default)
        else:
            return default

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

        flags = False
        if 'flags' in definition and definition['flags']:
            flags=True
            definition['tests']=definition.get('tests',{})
            definition['tests']['unique']=definition['tests'].get('unique',True)
            definition['tests']['single-bit-only']=definition['tests'].get('single-bit-only',True)

        default = definition.get('default', 0)
        for k,vpak in definition['values'].items():
            val = self._get_value_for(vpak)
            if self._get_for(vpak, 'default', False):
                if flags:
                    default |= val
                else:
                    default = val

        if flags or 'tests' in definition:
            with log.info('Testing %s....', definition['name']):
                tests = definition.get('tests',{})
                if 'increment' in tests:
                    incrdef = tests['increment']
                    start = incrdef.get('start',0)
                    stop = incrdef.get('stop', len(definition['values']))

                    vals = []
                    for k,vpak in definition['values'].items():
                        vals += [self._get_value_for(vpak)]

                    for i in range(start,stop):
                        if i not in vals:
                            log.error('increment: Missing value %d!', i)
                if 'unique' in tests and tests['unique']:
                    vals={}
                    for k,vpak in definition['values'].items():
                        val = self._get_value_for(vpak)
                        if val in vals:
                            log.error('unique: Entry %s is not using a unique value!', k)
                        vals[val]=True
                if flags:
                    if 'single-bit-only' in tests and tests['single-bit-only']:
                        for k,vpak in definition['values'].items():
                            val = self._get_value_for(vpak)
                            c = 0
                            while val > 0:
                                c = val & 1
                                val >>= 1
                                if c > 1:
                                    log.error('single-bit-only: Entry %s has too many bits!', k)
                                    break
        definition['default'] = default
        os_utils.ensureDirExists(os.path.dirname(self.target), noisy=True)
        with open(self.target, 'w') as w:
            self.writer.write(w, definition)
