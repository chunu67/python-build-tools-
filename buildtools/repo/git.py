'''
Created on Mar 28, 2015

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
'''
import os
import sys
import glob
import subprocess

from buildtools.bt_logging import log
from buildtools.os_utils import cmd_output, Chdir, cmd, ENV
from buildtools.wrapper.git import Git
from buildtools.repo.base import SCMRepository


class GitRepository(SCMRepository):
    '''Logical representation of a git repository.'''

    def __init__(self, path, origin_uri, quiet=True, noisy_clone=False):
        super(GitRepository, self).__init__(path, quiet=quiet, noisy_clone=noisy_clone)

        # Known remotes.
        self.remotes = self.orig_remotes = {'origin': origin_uri}
        # Git configuration variables.
        self.config_vars = {}

        self.current_branch = None
        self.current_commit = None
        self.remote_commit = None

        self.noPasswordEnv = ENV.clone().env
        self.noPasswordEnv['GIT_TERMINAL_PROMPT']='0'

    def _git(self, args, echo=False):
        ret = cmd_output(['git'] + args, echo=echo, env=self.noPasswordEnv)

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

        stdout, stderr = cmd_output(['git', 'remote', 'show', remoteID], echo=not self.quiet, env=self.noPasswordEnv)
        for line in (stdout + stderr).split('\n'):
            line = line.strip()
            components = line.split()
            if line.startswith('Fetch URL:'):
                # self.remotes[remoteID]=line[2]
                return line[2]

    def UpdateRemotes(self,remote=None):
        if remote is not None:
            self.remotes[remote]=self._getRemoteInfo(remote)
            return True
        stdout, stderr = cmd_output(['git', 'remote', 'show'], echo=not self.quiet, env=self.noPasswordEnv)
        for line in (stdout + stderr).split('\n'):
            line = line.strip()
            if line == '':
                continue
            if line.startswith('fatal:'):
                log.error('[git] ' + line)
                return False
            self.remotes[line] = self._getRemoteInfo(line)
        return True

    def GetRepoState(self,remote=None):
        with Chdir(self.path, quiet=self.quiet):
            if self.UpdateRemotes(remote):
                self.current_branch = Git.GetBranch()
                self.current_commit = Git.GetCommit(short=False)

    def GetRemoteState(self, remote='origin', branch='master'):
        with Chdir(self.path, quiet=self.quiet):
            ret = cmd_output(['git', 'fetch', '-q'], echo=not self.quiet, env=self.noPasswordEnv)
            if not ret:
                return False
            stdout, stderr = ret
            for line in (stdout + stderr).split('\n'):
                line = line.strip()
                if line == '':
                    continue
                if line.startswith('fatal:'):
                    log.error('[git] ' + line)
                    return False
            remoteinfo = Git.LSRemote(remote, branch)
            if remoteinfo is None:
                return False
            ref = 'refs/heads/' + branch
            if ref in remoteinfo:
                self.remote_commit = remoteinfo[ref]
        return True

    def CheckForUpdates(self, remote='origin', branch='master', quiet=True):
        if not quiet:
            log.info('Checking %s for updates...', self.path)
        with log:
            if not os.path.isdir(self.path):
                return True
            self.GetRepoState(remote)
            if not self.GetRemoteState(remote, branch):
                return False
            if self.current_branch != branch:
                if not quiet:
                    log.info('Branch is wrong! %s (L) != %s (R)', self.current_branch, branch)
                return True
            if self.current_commit != self.remote_commit:
                if not quiet:
                    log.info('Commit is out of date! %s (L) != %s (R)', self.current_commit, self.remote_commit)
                return True
        return False

    def Pull(self, remote='origin', branch='master', commit=None, cleanup=False):
        if not os.path.isdir(self.path):
            cmd(['git', 'clone', self.remotes[remote], self.path], echo=not self.quiet or self.noisy_clone, critical=True, show_output=not self.quiet or self.noisy_clone, env=self.noPasswordEnv)
        with Chdir(self.path, quiet=self.quiet):
            if cleanup:
                cmd(['git', 'clean', '-fdx'], echo=not self.quiet, critical=True)
                cmd(['git', 'reset', '--hard'], echo=not self.quiet, critical=True)
            if self.current_branch != branch:
                ref = 'remotes/{}/{}'.format(remote, branch)
                cmd(['git', 'checkout', '-B', branch, ref, '--'], echo=not self.quiet, critical=True)
            if commit is not None:
                cmd(['git', 'checkout', commit], echo=not self.quiet, critical=True)
            else:
                if self.current_commit != self.remote_commit:
                    cmd(['git', 'reset', '--hard', '{}/{}'.format(remote, branch)], echo=not self.quiet, critical=True)
        return True

    def UpdateSubmodules(self, remote=False):
        with log.info('Updating submodules in %s...', self.path):
            with Chdir(self.path, quiet=self.quiet):
                if os.path.isfile('.gitmodules'):
                    more_flags = []
                    if remote:
                        more_flags.append('--remote')
                    cmd(['git', 'submodule', 'update', '--init', '--recursive'] + more_flags, echo=not self.quiet, critical=True, env=self.noPasswordEnv)

    def Update(self, cleanup=False):
        return self.Pull(cleanup=cleanup)
