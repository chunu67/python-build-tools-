'''
Created on Mar 26, 2015

@author: Rob
'''

import time, sys, yaml, os, logging, math

def clock():
    if sys.platform == 'win32':
        return time.clock()
    else:
        return time.time()
    
class IDelayer(object):
    def __init__(self, id, min_delay=0):
        self.id = id
        self.minDelay = min_delay
        
    def Check(self):
        return False
    
    def Reset(self):
        pass
        
    def TimeLeft(self):
        return 0
    
class SimpleDelayer(IDelayer):
    def __init__(self, id, min_delay=1):
        super(SimpleDelayer, self).__init__(id, min_delay)
        self.lastCheck = 0
        
    def Check(self, quiet=False):
        ago = max(0, int(time.time() - self.lastCheck))
        if ago >= self.minDelay:
            if not quiet: 
                #logging.info('[%s] Last check was %ds ago (min=%d, %d - %d)...', self.id, ago, self.minDelay, time.time(), self.lastCheck)
                logging.info('[%s] Last check was %ds ago', self.id, ago, self.minDelay, time.time(), self.lastCheck)
            return True
        return False
        
    def Wait(self):
        while not self.Check(True):
            left = max(0, self.TimeLeft())
            if left > 0:
                logging.info('[%s] Sleeping for %ds', self.id, left)
                time.sleep(left)
    
    def Reset(self):
        self.lastCheck = time.time()
        
    def TimeLeft(self):
        return math.ceil(self.minDelay - (time.time() - self.lastCheck))
    
def SimpleDelayRepresenter(dumper, data):
    return dumper.represent_scalar('!simpledelay', '{}@{}'.format(data.id, data.lastCheck))
    
def SimpleDelayConstructor(loader, node):
    id, value = loader.construct_scalar(node).split('@')
    value = float(value)
    s = SimpleDelayer(id, min_delay=0)
    s.lastCheck = value
    return s
    
def SetupYaml():
    yaml.add_constructor(u'!simpledelay', SimpleDelayConstructor)
    yaml.add_representer(SimpleDelayer, SimpleDelayRepresenter)
    
class DelayCollection(object):
    def __init__(self, id, min_delay=1):
        self.id = id
        self.minDelay = min_delay
        self.delayCollection = {}
        
    def serialize(self):
        o = {}
        for k, v in self.delayCollection.items():
            o[k] = v
        return o
    
    def deserialize(self, data):
        self.delayCollection.clear()
        for k, v in data.items():
            self.delayCollection[k] = v
            self.delayCollection[k].minDelay = self.minDelay
        
    def _toIDString(self, id):
        # return '.'.join(self.id.split('.') + id)
        return  '.'.join(id)
        
    def getDelayer(self, id):
        idstr = self._toIDString(id)
        if idstr not in self.delayCollection: 
            logging.info('[%s] Creating %s delayer.', self.id, idstr)
            self.delayCollection[idstr] = SimpleDelayer(idstr, min_delay=self.minDelay)
        return self.delayCollection[idstr] 
    
    def removeDelayer(self, id):
        idstr = self._toIDString(id)
        if idstr in self.delayCollection:
            logging.info('[%s] Dropping %s delayer.', self.id, idstr)
            del self.delayCollection[idstr]
        
    def Check(self, identifier):
        return self.getDelayer(identifier).Check()
        
    def Wait(self, identifier):
        return self.getDelayer(identifier).Wait()
    
    def Reset(self, identifier):
        self.getDelayer(identifier).Reset()
        
    def TimeLeft(self, identifier):
        self.getDelayer(identifier).TimeLeft()