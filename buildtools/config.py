import os,yaml

from .logging import log

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