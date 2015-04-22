'''
Created on Mar 28, 2015

@author: Rob
'''
import os, re
#import sys
#import glob
#import subprocess

from mercurial import hg, ui

from buildtools.bt_logging import log
from buildtools.os_utils import cmd_output, cmd
from buildtools.repo.base import SCMRepository

HG_VERSION = None
REG_VERSION = re.compile(r'version ([0-9\.]+)')

def checkHg():
    '''Will raise CalledProcessError if something goes sideways.'''
    global HG_VERSION
    if HG_VERSION is None:
        stdout, stderr = cmd_output(['hg', '--version'], critical=True)
        for line in (stdout + stderr).split('\n'):
            m = REG_VERSION.search(line)
            if m:
                HG_VERSION = m.group(1)
                break
        
        log.info('mercurial version %s detected.', HG_VERSION)


class HgRepository(SCMRepository):

    '''Logical representation of a mercurial repository.'''

    def __init__(self, path, origin_uri, quiet=True, noisy_clone=False, show_output=False):
        super(HgRepository, self).__init__(path, quiet=quiet, noisy_clone=noisy_clone)
        self.show_output = show_output

        self.remotes = {'default': origin_uri}
        self.remote = hg.peer(ui.ui(), {}, origin_uri)
        self.repo = None
        self.repoExists = False

        checkHg()
        self._connectRepo()

        self.current_branch = None
        self.current_rev = None
        self.remote_rev = None

    def _hgcmd(self, args):
        stdout, stderr = cmd_output(['hg', '--cwd', self.path, '--encoding', 'UTF-8'] + args, echo=not self.quiet, critical=True)
        if self.show_output:
            with log:
                for line in (stdout + stderr).split('\n'):
                    log.info('-> %s', line)
        return (stdout + stderr)

    def _checkRepo(self):
        if not os.path.isdir(self.path):
            return False
        if not os.path.isdir(os.path.join(self.path, '.hg')):
            return False
        return True

    def _connectRepo(self):
        self.repo = None
        if self._checkRepo():
            self.repo = hg.repository(ui.ui(), self.path)

    def _getRemoteInfo(self, remoteID):
        for line in self._hgcmd(['paths', remoteID]).split('\n'):
            # default =
            # http://hg.limetech.org/projects/tf2items/tf2items_source/
            line = line.strip()
            if line == '':
                continue
            return line

    def UpdateRemotes(self):
        if self.repo is None:
            return
        '''
        comparing with http://hg.limetech.org/projects/tf2items/tf2items_source/
        searching for changes
        changeset:   262:2e1af85fb73b
        tag:         tip
        user:        Asher Baker <asherkin@limetech.org>
        date:        Fri Nov 07 18:11:43 2014 +0000
        summary:     Fix posix builds.
        '''
        stdout, stderr = cmd_output(['hg', 'in', '-ny'], echo=not self.quiet)
        for line in (stdout + stderr).split('\n'):
            line = line.strip()
            if line == '':
                continue
            self.remotes[line] = self._getRemoteInfo(line)

    def getRevision(self):
        if self.repo is None:
            return None
        for line in self._hgcmd(['identify', '-n', '-r', '.']).split('\n'):
            line = line.strip()
            if line == '':
                continue
            return int(line)
        return None

    def getBranch(self):
        if self.repo is None:
            return None
        for line in self._hgcmd(['identify', '-b', '-r', '.']).split('\n'):
            line = line.strip()
            if line == '':
                continue
            return line
        return None

    def GetRepoState(self):
        self.UpdateRemotes()
        self.current_branch = self.getBranch()
        self.current_rev = self.getRevision()

    def GetRemoteState(self, remote='default', branch='default'):
        if self.repo is None:
            return None
        '''
        comparing with http://hg.limetech.org/projects/tf2items/tf2items_source/
        searching for changes
        changeset:   262:2e1af85fb73b
        tag:         tip
        user:        Asher Baker <asherkin@limetech.org>
        date:        Fri Nov 07 18:11:43 2014 +0000
        summary:     Fix posix builds.
        '''

        for line in self._hgcmd(['in', '-b', branch, '-nv', remote]).split('\n'):
            line = line.strip()
            if line == '':
                continue
            if line.startswith('changeset:'):
                self.remote_rev = int(line.split(':')[1].strip())

    def CheckForUpdates(self, remote='default', branch='default', quiet=True):
        if self.repo is None:
            return True
        if not quiet:
            log.info('Checking %s for updates...', self.path)
        with log:
            if not os.path.isdir(self.path):
                return True
            self.GetRepoState()
            self.GetRemoteState(remote, branch)
            if self.current_branch != branch:
                if not quiet:
                    log.info(
                        'Branch is wrong! %s (L) != %s (R)', self.current_branch, branch)
                return True
            if self.current_rev != self.remote_rev:
                if not quiet:
                    log.info(
                        'Revision is out of date! %s (L) != %s (R)', self.current_rev, self.remote_rev)
                return True
        return False

    def IsDirty(self):
        if self.repo is None:
            return True
        for line in self._hgcmd(['status']).split('\n'):
            if line.strip() != '':
                return True
        return False

    def Pull(self, remote='default', branch='default', cleanup=False):
        if not os.path.isdir(self.path):
            cmd(['hg', 'clone', self.remotes[remote], self.path], echo=not self.quiet or self.noisy_clone,
                critical=True, show_output=not self.quiet or self.noisy_clone)
        if self.IsDirty() and cleanup:
            self._hgcmd(['clean', '--all', '--dirs', '--files'])
            self._hgcmd(['revert', '-C', '--all'])
        if self.current_branch != branch:
            self._hgcmd(['checkout', '-C', branch])
        if self.current_rev != self.remote_rev:
            self._hgcmd(['pull', '-r', self.remote_rev])
        return True

    def UpdateSubmodules(self, remote=False):
        '''
        with log.info('Updating submodules in %s...', self.path):
            with Chdir(self.path, quiet=self.quiet):
                if os.path.isfile('.gitmodules'):
                    more_flags = []
                    if remote: more_flags.append('--remote')
                    cmd(['git', 'submodule', 'update', '--init', '--recursive'] + more_flags, echo=not self.quiet, critical=True)
        '''

    def Update(self, cleanup=False):
        return self.Pull(cleanup=cleanup)
