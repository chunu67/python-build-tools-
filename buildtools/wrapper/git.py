import os, sys, glob, subprocess

from buildtools.bt_logging import log

class Git(object):
    @classmethod
    def GetCommit(cls):
        try:
            rev = subprocess.Popen(['git', 'rev-parse', '--short', 'HEAD'], stdout=subprocess.PIPE).communicate()[0][:-1]
            if rev:
                return rev.decode('utf-8')
        except Exception as e:
            print(e)
            pass
        return '[UNKNOWN]'
    
    @classmethod
    def GetBranch(cls):
        try:
            branch = subprocess.Popen(["git", "rev-parse", "--abbrev-ref", 'HEAD'], stdout=subprocess.PIPE).communicate()[0][:-1]
            if branch:
                return branch.decode('utf-8')
        except Exception as e:
            print(e)
            pass
        return '[UNKNOWN]'