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
            stdout,stderr = cmd_output(['git','rev-parse']+addtl_flags, echo=not self.quiet, critical=True)
            return (stdout+stderr)
            #rev = subprocess.Popen(['git', 'rev-parse'] + addtl_flags + [ref], stdout=subprocess.PIPE).communicate()[0][:-1]
            #if rev:
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
    
class GitRepository(object):
    '''Logical representation of a git repository.
    '''
    
    def __init__(self, path, origin_uri, quiet=True):
        self.path = path
        self.remotes = {'origin':origin_uri}
        self.quiet = quiet
        
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
            self.remotes[line] = self._getRemoteInfo(line)
            
    def GetRepoState(self):
        with Chdir(self.path, quiet=self.quiet):
            self.UpdateRemotes()
            self.current_branch = Git.GetBranch()
            self.current_commit = Git.GetCommit(short=False)
            
    def GetRemoteState(self, remote='origin', branch='master'):
        with Chdir(self.path, quiet=self.quiet):
            cmd(['git', 'fetch', '-q'], critical=True, echo=not self.quiet)
            remoteinfo = Git.LSRemote(remote, branch)
            self.remote_commit = remoteinfo['refs/heads/' + branch]

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
            cmd(['git', 'clone', self.remotes[remote], self.path], echo=not self.quiet, critical=True, show_output=not self.quiet)
        with Chdir(self.path, quiet=self.quiet):
            if Git.IsDirty() and cleanup:
                cmd(['git', 'clean', '-fdx'], echo=not self.quiet, critical=True)
                cmd(['git', 'reset', '--hard'], echo=not self.quiet, critical=True)
            if self.current_branch != branch or self.current_commit != self.remote_commit:
                cmd(['git', 'reset', '--hard', '{}/{}'.format(remote, branch)], echo=not self.quiet, critical=True)
        return True
            
    def UpdateSubmodules(self, remote=False):
        with log.info('Updating submodules in %s...', self.path):
            with Chdir(self.path, quiet=self.quiet):
                if os.path.isfile('.gitmodules'):
                    more_flags = []
                    if remote: more_flags.append('--remote')
                    cmd(['git', 'submodule', 'update', '--init', '--recursive'] + more_flags, echo=not self.quiet, critical=True)
