'''
Salty Configuration, meaning that a bunch of this code is stolen from Salt :V

Copyright (c) 2015 - 2016 Rob "N3X15" Nelson <nexisentertainment@gmail.com>

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
import collections
import jinja2
import sys
import codecs

from buildtools.bt_logging import log, NullIndenter
from buildtools.os_utils import ensureDirExists
import fnmatch
from buildtools.ext.salt.jinja_ext import salty_jinja_envs

def delimget(cfg, key, default=None, delim='.'):
    parts = key.split(delim)
    try:
        value = cfg[parts[0]]
        if len(parts) == 1:
            return value
        for part in parts[1:]:
            value = value[part]
        return value
    except (KeyError, TypeError):
        return default

def delimset(cfg, key, value, delim='.'):
    parts = key.split(delim)
    try:
        if len(parts) == 1:
            cfg[parts[0]] = value
        if parts[0] not in cfg:
            cfg[parts[0]] = collections.OrderedDict()
        L = cfg[parts[0]]
        for part in parts[1:-1]:
            if part not in L:
                L[part] = collections.OrderedDict()
            L = L[part]
        L[parts[-1]] = value
    except (KeyError, TypeError):
        return

def flattenDict(cfg, delim='/', ppath=[], out=None):
    if out is None:
        out = collections.OrderedDict()
    for key, value in cfg.iteritems():
        cpath = ppath + [key]
        strpath = delim.join(cpath)
        if isinstance(value, dict):
            flattenDict(value, delim, cpath, out)
        elif isinstance(value, (list, set)):
            flattenList(value, delim, cpath, out)
        else:
            out[strpath] = value
    return out


def flattenList(cfg, delim='/', ppath=[], out=None):
    if out is None:
        out = collections.OrderedDict()
    for key, value in enumerate(cfg):
        cpath = ppath + [key]
        strpath = delim.join(cpath)
        if isinstance(value, dict):
            flattenDict(value, delim, cpath, out)
        elif isinstance(value, (list, set)):
            flattenList(value, delim, cpath, out)
        else:
            out[strpath] = value
    return out

def replace_var(input, varname, replacement):
    return input.replace('%%' + varname + '%%', replacement)


def replace_vars(input, var_replacements):
    for key, val in var_replacements.items():
        input = replace_var(input, key, val)
    return input


def dict_merge(a, b, path=None):
    "merges b into a"
    if path is None:
        path = []
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                dict_merge(a[key], b[key], path + [str(key)])
            elif a[key] == b[key]:
                pass  # same leaf value
            else:
                # Old behavior: scream
                # raise Exception('Conflict at %s' % '.'.join(path + [str(key)]))
                # New behavior: Overwrite A with B.
                a[key] = b[key]
        else:
            a[key] = b[key]
    return a


class BaseConfig(object):

    def __init__(self):
        self.cfg = {}

    def __getitem__(self, key):
        return self.cfg.__getitem__(key)

    def __setitem__(self, key, value):
        return self.cfg.__setitem__(key, value)

    def get(self, key, default=None, delim='.'):
        return delimget(self.cfg, key, default, delim)

    def set(self, key, value, delim='.'):
        delimset(self.cfg, key, value, delim)


class ConfigFile(BaseConfig):

    def __init__(self, filename=None, default={}, template_dir='.', variables={}, verbose=False):
        env_vars = salty_jinja_envs()
        env_vars['loader'] = jinja2.loaders.FileSystemLoader(template_dir)
        self.environment = jinja2.Environment(**env_vars)
        self.cfg = {}
        if filename is None:
            self.cfg = default
        else:
            self.Load(filename, merge=False, defaults=default, variables=variables, verbose=verbose)

    def Load(self, filename, merge=False, defaults=None, variables={}, verbose=False):
        lh = NullIndenter()
        if verbose:
            lh = log.info("Loading %s...", filename)
        with lh:
            if not os.path.isfile(filename):
                if defaults is None:
                    if verbose: log.error('Failed to load %s.', filename)
                    return False
                else:
                    if verbose: log.warn('File not found, loading defaults.')
                    ensureDirExists(os.path.dirname(filename))
                    self.dump_to_file(filename, defaults)

            if os.path.isfile(filename):
                rendered = ''
                try:
                    template = self.environment.get_template(filename)
                    rendered = template.render(variables)
                except jinja2.exceptions.TemplateNotFound:
                    if verbose: log.warn('Jinja2 failed to load %s (TemplateNotFound). Failing over to plain string.', filename)
                    with codecs.open(filename, 'r') as f:
                        rendered = f.read()

                newcfg = self.load_from_string(rendered)
                if merge:
                    self.cfg = dict_merge(self.cfg, newcfg)
                else:
                    self.cfg = newcfg
        return True

    def Save(self, filename):
        self.dump_to_file(filename, self.cfg)

    def LoadFromFolder(self, path, pattern='*.yml', variables={}, verbose=False):
        'For conf.d/ stuff.'
        for root, _, files in os.walk(path):
            for filename in files:
                absfilename = os.path.join(root, filename)
                if fnmatch.fnmatch(absfilename, pattern):
                    self.Load(absfilename, merge=True, variables=variables, verbose=verbose)
        # for filename in glob.glob(os.path.join(path,pattern)):
        #    self.Load(filename, merge=True)

    def dump_to_file(self, filename, cfg):
        pass

    def load_from_string(self, string):
        return {}


class YAMLConfig(ConfigFile):
    def dict_representer(self, dumper, data):
        return dumper.represent_dict(data.iteritems())

    def dict_constructor(self, loader, node):
        return collections.OrderedDict(loader.construct_pairs(node))

    def __init__(self, filename=None, default={}, template_dir='.', variables={}, verbose=False, ordered_dicts=False):
        self._ordered_dicts=False
        super(YAMLConfig, self).__init__(filename, default, template_dir, variables, verbose)
        self._ordered_dicts=ordered_dicts

    def dump_to_file(self, filename, data):
        import yaml
        with codecs.open(filename, 'w', encoding='utf-8') as f:
            dumper = yaml.Dumper(f, default_flow_style=False)
            #if self._ordered_dicts:
            dumper.add_representer(collections.OrderedDict, self.dict_representer)
            try:
                dumper.open()
                dumper.represent(data)
                dumper.close()
            finally:
                dumper.dispose()

    def load_from_string(self, string):
        import yaml
        loader = yaml.Loader(string)
        if self._ordered_dicts:
            loader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, self.dict_constructor)
        try:
            return loader.get_single_data()
        finally:
            loader.dispose()


class Config(YAMLConfig):

    '''DEPRECATED: Use YAMLConfig instead.'''

    def __init__(self, filename=None, default={}, template_dir='.', variables={}, verbose=False):
        log.warn('Config class is deprecated.  Use YAMLConfig instead.')
        super(Config, self).__init__(filename, default, template_dir, variables, verbose)


class TOMLConfig(ConfigFile):

    def __init__(self, filename=None, default={}, template_dir='.', variables={}, verbose=False):
        super(TOMLConfig, self).__init__(filename, default, template_dir, variables, verbose)

    def dump_to_file(self, filename, data):
        import toml
        with open(filename, 'w') as f:
            f.write(toml.dumps(data))

    def load_from_string(self, string):
        import toml
        return toml.loads(string)


class Properties(object):

    def __init__(self):
        self.properties = {}

    def Load(self, filename, default=None, expand_vars={}):
        with log.info("Loading %s...", filename):
            if not os.path.isfile(filename):
                if default is None:
                    log.critical('File not found, exiting!')
                    log.info('To load defaults, specify default=<dict> to Properties.Load().')
                    sys.exit(1)
                else:
                    log.warn('File not found, loading defaults.')
                    with open(filename, 'w') as f:
                        self.dumpTo(default, f)

            with open(filename, 'r') as f:
                for line in f:
                    if line.strip() == '':
                        continue
                    # Ignore comments.
                    if line.strip().startswith('#'):
                        continue

                    key, value = line.strip().split('=', 1)
                    if key in self.properties:
                        log.warn('Key "%s" already exists, overwriting!', key)
                    value = replace_vars(value, expand_vars)
                    self.properties[key] = value

            if default is None:
                return
            for k, v in default.items():
                if k not in self.properties:
                    self.properties[k] = v
                    log.info('Added default property %s = %s', k, v)

    def Save(self, filename):
        with log.info("Saving %s...", filename):
            with open(filename, 'w') as f:
                Properties.dumpTo(self.properties, f)

    @classmethod
    def dumpTo(cls, properties, f):
        for k, v in sorted(properties.items()):
            f.write("{}={}\n".format(k, v))

    def __getitem__(self, key):
        return self.properties.__getitem__(key)

    def __setitem__(self, key, value):
        return self.properties.__setitem__(key)
