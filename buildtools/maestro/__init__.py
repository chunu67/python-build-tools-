'''
BLURB GOES HERE.

Copyright (c) 2015 - 2017 Rob "N3X15" Nelson <nexisentertainment@gmail.com>

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

'''
import codecs
import logging
import os
import re
import sys
import shutil
from buildtools import os_utils
from buildtools.bt_logging import NullIndenter, log
from buildtools.maestro.base_target import BuildTarget
from buildtools.maestro.fileio import (ConcatenateBuildTarget, CopyFilesTarget,
                                       CopyFileTarget, MoveFileTarget,
                                       ReplaceTextTarget)
from buildtools.maestro.utils import (SerializableFileLambda,
                                      SerializableLambda, callLambda)

import yaml
from tqdm import tqdm


class BuildMaestro(object):
    ALL_TYPES = {}

    def __init__(self, all_targets_file='.alltargets.yml', hidden_build_dir='.build'):
        self.alltargets = []
        self.targets = []
        self.targetsCompleted = []

        self.verbose = False
        self.colors = False

        self.builddir = hidden_build_dir
        self.all_targets_file = os.path.join(self.builddir, hidden_build_dir)

    def add(self, bt):
        self.alltargets.append(bt)
        self.targets += bt.provides()

    def build_argparser(self):
        import argparse
        argp = argparse.ArgumentParser()
        argp.add_argument('--clean', action='store_true', help='Cleans everything.')
        argp.add_argument('--no-colors', action='store_true', help='Disables colors.')
        argp.add_argument('--rebuild', action='store_true', help='Clean rebuild of project.')
        argp.add_argument('--verbose', action='store_true', help='Show hidden buildsteps.')
        return argp

    def parse_args(self, argp=None, args=None):
        if argp is None:
            argp = self.build_argparser()
        return argp.parse_args(args)

    def as_app(self, argp=None, args=None):
        args = self.parse_args(argp, args)
        if args.verbose:
            log.log.setLevel(logging.DEBUG)
            self.verbose = True

        self.colors = not args.no_colors

        if self.colors:
            log.enableANSIColors()

        if args.rebuild or args.clean:
            self.clean()
        if args.clean:
            return
        self.run()

    def clean(self):
        if os.path.isfile(self.all_targets_file):
            with open(self.all_targets_file, 'r', encoding='utf-8') as f:
                for targetfile in sorted(yaml.load(f)):
                    targetfile = os.path.normpath(targetfile)
                    if os.path.isfile(targetfile):
                        if self.colors:
                            log.info('<red>RM</red> %s', targetfile)
                        else:
                            log.info('RM %s', targetfile)
                        os.remove(targetfile)
        if os.path.isdir(self.builddir):
            if self.colors:
                log.info('<red>RMTREE</red> %s <red>(build system stuff)</red>', self.builddir)
            else:
                log.info('RMTREE %s (build system stuff)', self.builddir)
            shutil.rmtree(self.builddir, ignore_errors=True)

    @staticmethod
    def RecognizeType(cls):
        BuildMaestro.ALL_TYPES[cls.BT_TYPE] = cls

    def saveRules(self, filename):
        serialized = {}
        for rule in self.alltargets:
            serialized[rule.name] = rule.serialize()
        with codecs.open(filename + '.yml', 'w', encoding='utf-8') as f:
            yaml.dump(serialized, f, default_flow_style=False)
        with codecs.open(filename, 'w', encoding='utf-8') as f:
            for tKey in sorted(serialized.keys()):
                target = dict(serialized[tKey])
                f.write(u'[{} {}]: {}\n'.format(target['type'], tKey, ', '.join(target.get('dependencies', []))))
                del target['dependencies']
                for provided in target.get('provides', []):
                    if provided != tKey:
                        f.write(u'< {}\n'.format(provided))
                for depend in target.get('files', []):
                    f.write(u'> {}\n'.format(depend))
                del target['files']
                del target['type']
                if len(target.keys()) > 0:
                    yaml.dump(target, f, default_flow_style=False)
                f.write(u'\n')

    def loadRules(self, filename):
        REGEX_RULEHEADER = re.compile('\[([A-Za-z0-9]+) ([^:]+)\]:(.*)$')
        self.targets = []
        self.alltargets = []
        with codecs.open(filename, 'r') as f:
            context = {}
            yamlbuf = ''
            ruleKey = ''
            for oline in f:
                s_line = oline.strip()
                if s_line.startswith('#') or s_line == '':
                    continue
                line = oline.rstrip()
                m = REGEX_RULEHEADER.match(line)
                if m is not None:
                    if len(context.keys()) > 0:
                        self.addFromRules(context, yamlbuf)
                        context = None
                        yamlbuf = ''
                        ruleKey = ''
                    typeID, ruleKey, depends = m.group(1, 2, 3)
                    context = {
                        'type': typeID,
                        'target': ruleKey,
                        'dependencies': [x.strip() for x in depends.split(',') if x != ''],
                        'files': [],
                        'provides': []
                    }
                elif line.startswith('>') and context is not None:
                    context['files'].append(line[1:].strip())
                elif line.startswith('<') and context is not None:
                    context['provides'].append(line[1:].strip())
                else:
                    yamlbuf += oline
            if context is not None:
                self.addFromRules(context, yamlbuf)
        log.info('Loaded %d rules from %s', len(self.alltargets), filename)

    def addFromRules(self, context, yamlbuf):
        # print(repr(yamlbuf))
        if yamlbuf.strip() != '':
            yml = yaml.load(yamlbuf)
            for k, v in yml.items():
                context[k] = v
        cls = self.ALL_TYPES[context['type']]
        bt = cls()
        bt.deserialize(context)
        self.add(bt)

    def get_max_label_length(self):
        max_len = 0
        for bt in self.alltargets:
            max_len = max(max_len, len(bt.get_label()))
        return max_len

    def run(self, verbose=None):
        if verbose is not None:
            self.verbose = verbose
        keys = []
        for target in self.alltargets:
            keys += target.provides()
        # Redundant
        #for target in self.alltargets:
        #    for reqfile in callLambda(target.files):
        #        if reqfile in keys and reqfile not in target.dependencies:
        #            target.dependencies.append(reqfile)
        loop = 0
        #progress = tqdm(total=len(self.targets), unit='target', desc='Building', leave=False)
        self.targetsCompleted = []
        self.targetsDirty = []
        while len(self.targets) > len(self.targetsCompleted) and loop < 1000:
            loop += 1
            for bt in self.alltargets:
                bt.maestro = self
                if bt.canBuild(self, keys) and any([target not in self.targetsCompleted for target in bt.provides()]):
                    bt.try_build()
                    # progress.update(1)
                    self.targetsCompleted += bt.provides()
                    if bt.dirty:
                        self.targetsDirty += bt.provides()
            #log.info('%d > %d',len(self.targets), len(self.targetsCompleted))
        # progress.close()
        alltargets = set()
        for bt in self.alltargets:
            for targetfile in bt.provides():
                alltargets.add(targetfile)
        with open(self.all_targets_file, 'w', encoding='utf-8') as f:
            yaml.dump(alltargets, f, default_flow_style=False)
        if loop >= 1000:
            with log.critical("Failed to resolve dependencies.  The following targets are left unresolved. Exiting."):
                for bt in self.alltargets:
                    if any([target not in self.targetsCompleted for target in bt.provides()]):
                        log.critical(bt.name)
                        log.critical('%r', bt.serialize())
            sys.exit(1)
