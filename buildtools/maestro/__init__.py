import codecs
import sys

import yaml

from buildtools.bt_logging import log
from buildtools.maestro.base_target import BuildTarget
from buildtools.maestro.utils import *


class BuildMaestro(object):
    ALL_TYPES = {}

    def __init__(self):
        self.alltargets = []
        self.targets = []
        self.targetsCompleted = []

    def add(self, bt):
        self.alltargets.append(bt)
        self.targets.append(bt.target)

    @staticmethod
    def RecognizeType(cls):
        BuildMaestro.ALL_TYPES[cls.BT_TYPE] = cls

    def saveRules(self, filename):
        serialized = {}
        for rule in self.alltargets:
            serialized[rule.target] = rule.serialize()
        with codecs.open(filename+'.yml', 'w', encoding='utf-8') as f:
            yaml.dump(serialized, f, default_flow_style=False)
        with codecs.open(filename, 'w', encoding='utf-8') as f:
            for tKey in sorted(serialized.keys()):
                target = dict(serialized[tKey])
                f.write(u'[{} {}]: {}\n'.format(target['type'], tKey, ', '.join(target.get('dependencies', []))))
                del target['dependencies']
                for depend in target.get('files', []):
                    f.write(u'> {}\n'.format(depend))
                del target['files']
                del target['type']
                if len(target.keys()) > 0:
                    yaml.dump(target, f, default_flow_style=False)
                f.write(u'\n')

    def loadRules(self, filename):
        REGEX_RULEHEADER = re.compile('\[([A-Za-z0-9]+) ([^:]+)\]:(.*)$')
        self.targets=[]
        self.alltargets=[]
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
                        'files': []
                    }
                elif line.startswith('>') and context is not None:
                    context['files'].append(line[1:].strip())
                else:
                    yamlbuf += oline
            if context is not None:
                self.addFromRules(context, yamlbuf)
        log.info('Loaded %d rules from %s', len(self.alltargets), filename)

    def addFromRules(self, context, yamlbuf):
        #print(repr(yamlbuf))
        if yamlbuf.strip() != '':
            yml = yaml.load(yamlbuf)
            for k, v in yml.items():
                context[k] = v
        cls = self.ALL_TYPES[context['type']]
        bt = cls()
        bt.deserialize(context)
        self.add(bt)

    def run(self):
        keys=[]
        for target in self.alltargets:
            keys += target.target
        for target in self.alltargets:
            for reqfile in target.files:
                if reqfile in keys and reqfile not in target.dependencies:
                    target.dependencies.append(reqfile)
        loop = 0
        while len(self.targets) > len(self.targetsCompleted) and loop < 1000:
            loop += 1
            for bt in self.alltargets:
                if bt.canBuild(self) and bt.target not in self.targetsCompleted:
                    with log.info('Building target %s...', bt.target):
                        bt.build()
                    self.targetsCompleted.append(bt.target)
            #log.info('%d > %d',len(self.targets), len(self.targetsCompleted))
        if loop >= 1000:
            with log.critical("Failed to resolve dependencies.  The following targets are left unresolved. Exiting."):
                for bt in self.alltargets:
                    if bt.target not in self.targetsCompleted:
                        log.critical(bt.target)
                        log.critical('%r',bt.serialize())
            sys.exit(1)
