import os, sys, glob, subprocess

from buildtools.bt_logging import log
from buildtools.os_utils import cmd_output, Chdir, cmd
from logging import critical

class Git(object):
    @classmethod
    def GetCommit(cls, ref='HEAD', short=True, quiet=True):
        try:
            addtl_flags = []
            if short: addtl_flags.append('--short')
            stdout, stderr = cmd_output(['git', 'rev-parse'] + addtl_flags + [ref], echo=not quiet, critical=True)
            return (stdout + stderr).strip()
            # rev = subprocess.Popen(['git', 'rev-parse'] + addtl_flags + [ref], stdout=subprocess.PIPE).communicate()[0][:-1]
            # if rev:
            #    return rev.decode('utf-8')
        except Exception as e:
            print(e)
            pass
        return '[UNKNOWN]'
    @classmethod
    def LSRemote(cls, remote=None, ref=None, quiet=True):
        args = []
        if remote:
            args.append(remote)
        if ref:
            args.append(ref)
        try:
            stderr, stdout = cmd_output(['git', 'ls-remote'] + args, echo=not quiet, critical=True)
            o = {}
            for line in (stdout + stderr).split('\n'):
                line = line.strip()
                if line == '': continue
                hashid, ref = line.split()
                o[ref] = hashid
            return o
        except Exception as e:
            print(e)
            pass
        return None
    
    @classmethod
    def GetBranch(cls, quiet=True):
        try:
            stderr, stdout = cmd_output(["git", "rev-parse", "--abbrev-ref", 'HEAD'], echo=not quiet, critical=True)
            return (stderr + stdout).strip()
            # branch = subprocess.Popen(["git", "rev-parse", "--abbrev-ref", 'HEAD'], stdout=subprocess.PIPE).communicate()[0][:-1]
            # if branch:
            #    return branch.decode('utf-8')
        except Exception as e:
            print(e)
            pass
        return '[UNKNOWN]'
    
    @classmethod
    def IsDirty(cls, quiet=True):
        try:
            # branch = subprocess.Popen(['git', 'ls-files', '-m', '-o', '-d', '--exclude-standard'], stdout=subprocess.PIPE).communicate()[0][:-1]
            # if branch:
            stderr, stdout = cmd_output(['git', 'ls-files', '-m', '-o', '-d', '--exclude-standard'], echo=not quiet, critical=True)
            for line in (stderr + stdout).split('\n'):
                line = line.strip()
                if line != '': return True
            return False
        except Exception as e:
            print(e)
            pass
        return None