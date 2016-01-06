'''
Profiling/Delay-related things.

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

@author: Rob
Created on Mar 26, 2015
'''

import time
import sys
import yaml
#import os
import logging
import math


def clock():
    if sys.platform == 'win32':
        return time.clock()
    else:
        return time.time()


class IDelayer(object):

    def __init__(self, _id, min_delay=0):
        self.id = _id
        self.minDelay = min_delay

    def Check(self, quiet=False): #IGNORE:unused-argument
        return False

    def Reset(self):
        pass

    def TimeLeft(self):
        return


class SimpleDelayer(IDelayer):

    def __init__(self, _id, min_delay=1):
        super(SimpleDelayer, self).__init__(_id, min_delay)
        self.lastCheck = 0

    def Check(self, quiet=False):
        ago = max(0, int(time.time() - self.lastCheck))
        if ago >= self.minDelay:
            if not quiet:
                #logging.info('[%s] Last check was %ds ago (min=%d, %d - %d)...', self.id, ago, self.minDelay, time.time(), self.lastCheck)
                logging.info('[%s] Last check was %ds ago', self.id, ago)
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
    _id, value = loader.construct_scalar(node).split('@')
    value = float(value)
    s = SimpleDelayer(_id, min_delay=0)
    s.lastCheck = value
    return s


def SetupYaml():
    yaml.add_constructor(u'!simpledelay', SimpleDelayConstructor)
    yaml.add_representer(SimpleDelayer, SimpleDelayRepresenter)


class DelayCollection(object):

    def __init__(self, _id, min_delay=1):
        self.id = _id
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

    def _toIDString(self, _id):
        # return '.'.join(self.id.split('.') + id)
        return '.'.join(_id)

    def getDelayer(self, _id):
        idstr = self._toIDString(_id)
        if idstr not in self.delayCollection:
            logging.info('[%s] Creating %s delayer.', self.id, idstr)
            self.delayCollection[idstr] = SimpleDelayer(
                idstr, min_delay=self.minDelay)
        return self.delayCollection[idstr]

    def removeDelayer(self, _id):
        idstr = self._toIDString(_id)
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
