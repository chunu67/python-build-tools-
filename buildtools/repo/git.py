'''
Created on Mar 28, 2015

@author: Rob
'''
import os, sys, glob, subprocess

from buildtools.bt_logging import log
from buildtools.os_utils import cmd_output, Chdir, cmd
from buildtools.wrapper.git import Git
from buildtools.repo.base import SCMRepository

class GitRepository(SCMRepository):
    '''Logical representation of a git repository.
    '''
    
    def __init__(self, path, origin_uri, quiet=True, noisy_clone=False):
        super(GitRepository, self).__init__(path, quiet=quiet, noisy_clone=noisy_clone)
        self.remotes = self.orig_remotes = {'origin':origin_uri}
        
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
        returns:
          https://github.com/d3athrow/vgstation13.git
        '''
        
        stdout, stderr = cmd_output(['git', 'remote', 'show', remoteID], echo=not self.quiet)
        for line in (stdout + stderr).split('\n'):
            line = line.strip()
            components = line.split()
            if line.startswith('Fetch URL:'):
                # self.remotes[remoteID]=line[2]
                return line[2]
            
    def UpdateRemotes(self):
        stdout, stderr = cmd_output(['git', 'remote', 'show'], echo=not self.quiet)
        for line in (stdout + stderr).split('\n'):
            line = line.strip()
            if line == '': continue
            if line.startswith('fatal:'):
                log.error('[git] '+line)
                return False
            self.remotes[line] = self._getRemoteInfo(line)
        return True
            
    def GetRepoState(self):
        with Chdir(self.path, quiet=self.quiet):
            if self.UpdateRemotes():
                self.current_branch = Git.GetBranch()
                self.current_commit = Git.GetCommit(short=False)
            
    def GetRemoteState(self, remote='origin', branch='master'):
        with Chdir(self.path, quiet=self.quiet):
            ret = cmd_output(['git', 'fetch', '-q'], echo=not self.quiet)
            if not ret: return False
            stdout,stderr = ret
            for line in (stdout + stderr).split('\n'):
                line = line.strip()
                if line == '': continue
                if line.startswith('fatal:'):
                    log.error('[git] '+line)
                    return False
            remoteinfo = Git.LSRemote(remote, branch)
            ref = 'refs/heads/' + branch
            if ref in remoteinfo:
                self.remote_commit = remoteinfo[ref]
        return True

    def CheckForUpdates(self, remote='origin', branch='master', quiet=True):
        if not quiet: log.info('Checking %s for updates...', self.path)
        with log:
            if not os.path.isdir(self.path):
                return True
            self.GetRepoState()
            if not self.GetRemoteState(remote, branch): return False
            if self.current_branch != branch:
                if not quiet: log.info('Branch is wrong! %s (L) != %s (R)', self.current_branch, branch)
                return True
            if self.current_commit != self.remote_commit:
                if not quiet: log.info('Commit is out of date! %s (L) != %s (R)', self.current_commit, self.remote_commit)
                return True
        return False
                    
    def Pull(self, remote='origin', branch='master', cleanup=False):
        if not os.path.isdir(self.path):
            cmd(['git', 'clone', self.remotes[remote], self.path], echo=not self.quiet or self.noisy_clone, critical=True, show_output=not self.quiet or self.noisy_clone)
        with Chdir(self.path, quiet=self.quiet):
            if Git.IsDirty() and cleanup:
                cmd(['git', 'clean', '-fdx'], echo=not self.quiet, critical=True)
                cmd(['git', 'reset', '--hard'], echo=not self.quiet, critical=True)
            if self.current_branch != branch:
                ref = 'remotes/{}/{}'.format(remote, branch)
                cmd(['git', 'checkout', '-B', branch, ref, '--'], echo=not self.quiet, critical=True)
            if self.current_commit != self.remote_commit:
                cmd(['git', 'reset', '--hard', '{}/{}'.format(remote, branch)], echo=not self.quiet, critical=True)
        return True
            
    def UpdateSubmodules(self, remote=False):
        with log.info('Updating submodules in %s...', self.path):
            with Chdir(self.path, quiet=self.quiet):
                if os.path.isfile('.gitmodules'):
                    more_flags = []
                    if remote: more_flags.append('--remote')
                    cmd(['git', 'submodule', 'update', '--init', '--recursive'] + more_flags, echo=not self.quiet, critical=True)

    def Update(self, cleanup=False):
        return self.Pull(cleanup=cleanup)