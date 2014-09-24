import os, yaml

from buildtools.bt_logging import log
    
def replace_var(input, varname, replacement):
    return input.replace('%%' + varname + '%%', replacement)

def replace_vars(input, var_replacements):
    for key, val in var_replacements.items():
        input = replace_var(input, key, val)
    return input

class Config(object):
    def __init__(self, filename, default={}):
        log.info("Loading {}...".format(filename))
        with log:
            self.cfg = default
            if not os.path.isfile(filename):
                log.warn('File not found, loading defaults.')
                with open(filename, 'w') as f:
                    yaml.dump(self.cfg, f, default_flow_style=False)
                
            with open(filename, 'r') as f:
                self.cfg = yaml.load(f)
        
    def __getitem__(self, key):
        return self.cfg.__getitem__(key)
    
    def __setitem__(self, key, value):
        return self.cfg.__setitem__(key)
    
    def get(self, key, default=None):
        parts = key.split('.')
        try:
            value = self.cfg[parts[0]]
            if len(parts) == 1:
                return value
            for part in parts[1:]:
                value = value[part]
            return value
        except KeyError:
            return default

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
                    # Ignore comments.
                    if line.strip().startswith('#'): continue
                    
                    key, value = line.split('=', 1)
                    if key in self.properties:
                        log.warn('Key "%s" already exists, overwriting!',key)
                    value=replace_vars(value, expand_vars)
                    self.properties[key] = value
                    
            for k, v in default.items():
                if k not in self.properties:
                    self.properties[k] = v
                    log.info('Added default property %s = %s',k,v)
                
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
