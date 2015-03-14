import os, sys, glob, subprocess

from buildtools.bt_logging import log
from buildtools.os_utils import cmd_output, Chdir, cmd
from logging import critical

class Git(object):
    @classmethod
    def GetCommit(cls, ref='HEAD', short=True):
        try:
            addtl_flags = []
            if short: addtl_flags.append('--short')
            rev = subprocess.Popen(['git', 'rev-parse'] + addtl_flags + [ref], stdout=subprocess.PIPE).communicate()[0][:-1]
            if rev:
                return rev.decode('utf-8')
        except Exception as e:
            print(e)
            pass
        return '[UNKNOWN]'
    @classmethod
    def LSRemote(cls, remote=None, ref=None):
        args = []
        if remote:
            args.append(remote)
        if ref:
            args.append(ref)
        try:
            stderr,stdout = cmd_output(['git','ls-remote']+args, echo=True, critical=True)
            o={}
            for line in (stdout+stderr).split('\n'):
                line=line.strip()
                hashid, ref = line.split()
                o[ref]=hashid
            return o
        except Exception as e:
            print(e)
            pass
        return None
    
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
    
    @classmethod
    def IsDirty(cls):
        try:
            branch = subprocess.Popen(['git', 'ls-files', '-m', '-o', '-d', '--exclude-standard'], stdout=subprocess.PIPE).communicate()[0][:-1]
            if branch:
                for line in branch.decode('utf-8').split('\n'):
                    line = line.strip()
                    if line != '': return True
            return False
        except Exception as e:
            print(e)
            pass
        return None
    
class GitRepository(object):
    '''Logical representation of a git repository.
    '''
    
    def __init__(self, path, origin_uri):
        self.path = path
        self.remotes = {'origin':origin_uri}
        
        self.current_branch = None
        self.current_commit = None
        self.remote_commit = None
        
    def _getRemoteInfo(self, remoteID):
        '''
        $ git remote show origin
        * remote origin
          Fetch URL: https://github.com/d3athrow/vgstation13.git
          Push  URL: https://github.com/d3athrow/vgstation13.git
          HEAD branch: Bleeding-Edge
          Remote branches:
            Bleeding-Edge                                         tracked
        '''
        
        stdout, stderr = cmd_output(['git', 'remote', 'show', remoteID], echo=True)
        for line in (stdout + stderr).split('\n'):
            line = line.strip()
            components = line.split()
            if line.startswith('Fetch URL:'):
                # self.remotes[remoteID]=line[2]
                return line[2]
            
    def UpdateRemotes(self):
        stdout, stderr = cmd_output(['git', 'remote', 'show'], echo=True)
        for line in (stdout + stderr).split('\n'):
            line = line.strip()
            self.remotes[line] = self._getRemoteInfo(line)
            
    def GetRepoState(self):
        with Chdir(self.path, quiet=True):
            self.UpdateRemotes()
            self.current_branch = Git.GetBranch()
            self.current_commit = Git.GetCommit(short=False)
            
    def GetRemoteState(self, remote='origin', branch='master'):
        with Chdir(self.path, quiet=True):
            cmd(['git', 'fetch', '-q'], critical=True, echo=True, show_output=True)
            remoteinfo = Git.LSRemote(remote, branch)
            self.remote_commit = remoteinfo['refs/heads/'+branch]

    def CheckForUpdates(self, remote='origin', branch='master'):
        with log.info('Checking %s for updates...', self.path):
            if not os.path.isdir(self.path):
                return True
            self.GetRepoState()
            self.GetRemoteState(remote, branch)
            if self.current_branch != branch or self.current_commit != self.remote_commit:
                return True
        return False
                    
    def Pull(self, remote='origin', branch='master', cleanup=False):
        if not os.path.isdir(self.path):
            cmd(['git', 'clone', self.remotes[remote], self.path], echo=True, critical=True, show_output=True)
        with Chdir(self.path, quiet=True):
            if Git.IsDirty() and cleanup:
                cmd(['git', 'clean', '-fdx'], echo=True, critical=True)
                cmd(['git', 'reset', '--hard'], echo=True, critical=True)
            if self.current_branch != branch or self.current_commit != self.remote_commit:
                cmd(['git', 'reset', '--hard', '{}/{}'.format(remote, branch)], echo=True, critical=True)
        return True
            
    def UpdateSubmodules(self, remote=False):
        with log.info('Updating submodules in %s...', self.path):
            with Chdir(self.path, quiet=True):
                if os.path.isfile('.gitmodules'):
                    more_flags = []
                    if remote: more_flags.append('--remote')
                    cmd(['git', 'submodule', 'update', '--init', '--recursive'] + more_flags, echo=True, critical=True)
