import os
from buildtools.maestro.base_target import BuildTarget
from buildtools import os_utils, log
class SCSSBuildTarget(BuildTarget):
    BT_TYPE = 'SCSS'

    def __init__(self, target=None, files=[], dependencies=[], compass=False, import_paths=[]):
        super(SCSSBuildTarget, self).__init__(target, files, dependencies)
        self.compass = compass
        self.import_paths = import_paths

    def serialize(self):
        dat= super(SCSSBuildTarget,self).serialize()
        dat['compass']=self.compass
        dat['imports']=self.import_paths
        return dat

    def deserialize(self,data):
        super(SCSSBuildTarget,self).deserialize(data)
        self.compass=data.get('compass',False)
        self.import_paths=data.get('imports',[])

    def build(self):
        sass_cmd = []
        if SASS.endswith('.bat') or SASS.endswith('.BAT'):
            RUBYDIR = os.path.dirname(SASS)
            sass_cmd = [os.path.join(RUBYDIR, 'ruby.exe'), os.path.join(RUBYDIR, 'sass')]
        else:
            sass_cmd = [SASS]
        args = ['--scss', '--force', '-C', '-t', 'compact']
        if self.compass:
            args += ['--compass']
        for import_path in self.import_paths:
            args += ['-I=' + import_path]
        if self.checkMTimes(self.files, self.target, config=args):
            os_utils.ensureDirExists(os.path.join('tmp', os.path.dirname(self.target)))
            os_utils.ensureDirExists(os.path.dirname(self.target))
            #log.info("SASS %s", self.target)
            os_utils.cmd(sass_cmd + args + self.files + [self.target], critical=True, echo=True, show_output=True)


class SCSSConvertTarget(BuildTarget):
    BT_TYPE = 'SCSSConvert'

    def __init__(self, target=None, files=[], dependencies=[]):
        super(SCSSConvertTarget, self).__init__(target, files, dependencies)

    def build(self):
        sass_cmd = []
        if SASS_CONVERT.endswith('.bat') or SASS_CONVERT.endswith('.BAT'):
            RUBYDIR = os.path.dirname(SASS_CONVERT)
            sass_cmd = [os.path.join(RUBYDIR, 'ruby.exe'), os.path.join(RUBYDIR, 'sass-convert')]
        else:
            sass_cmd = [SASS_CONVERT]
        args = ['-F','css','-T','scss','-C']
        if self.checkMTimes(self.files, self.target, config=args):
            os_utils.ensureDirExists(os.path.join('tmp', os.path.dirname(self.target)))
            os_utils.ensureDirExists(os.path.dirname(self.target))
            #log.info("SASS %s", self.target)
            os_utils.cmd(sass_cmd + args + self.files + [self.target], critical=True, echo=True, show_output=True)


SASS = os_utils.which('sass')
if SASS is None:
    log.warn('Unable to find sass on this OS.  Is it in PATH?  Remember to run `gem install sass compass`!')

SASS_CONVERT = os_utils.which('sass-convert')
if SASS_CONVERT is None:
    log.warn('Unable to find sass-convert on this OS.  Is it in PATH?  Remember to run `gem install sass compass`!')
