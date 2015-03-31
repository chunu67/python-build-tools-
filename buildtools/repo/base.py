'''
Created on Mar 28, 2015

@author: Rob
'''

class SCMRepository(object):
    '''Logical representation of a source code repository.'''
    
    def __init__(self, path, quiet=True, noisy_clone=False):
        self.path = path
        self.quiet = quiet
        self.noisy_clone = noisy_clone

    def CheckForUpdates(self, quiet=True):
        return False
                    
    def Update(self, cleanup=False):
        return False