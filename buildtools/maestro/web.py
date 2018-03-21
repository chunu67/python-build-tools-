'''
BLURB GOES HERE.

Copyright (c) 2015 - 2018 Rob "N3X15" Nelson <nexisentertainment@gmail.com>

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
import os
import re
from buildtools import log, os_utils, utils
from buildtools.maestro.base_target import SingleBuildTarget


class SCSSBuildTarget(SingleBuildTarget):
    BT_TYPE = 'SCSS'
    BT_LABEL = 'SCSS'

    def __init__(self, target=None, files=[], dependencies=[], compass=False, import_paths=[], output_style='compact', sass_path=None, imported=[]):
        super(SCSSBuildTarget, self).__init__(target, files, dependencies)
        self.compass = compass
        self.import_paths = import_paths
        self.output_style = output_style
        self.imported = imported

        if sass_path is None:
            sass_path = os_utils.which('sass')
            if sass_path is None:
                log.warn('Unable to find sass on this OS.  Is it in PATH?  Remember to run `gem install sass compass`!')
        self.sass_path = sass_path

    def is_stale(self):
        return self.checkMTimes(self.files+self.dependencies+self.imported, self.provides(), config=self.get_config())

    def serialize(self):
        dat = super(SCSSBuildTarget, self).serialize()
        dat['compass'] = self.compass
        dat['imports'] = self.import_paths
        dat['style'] = self.output_style
        dat['imported'] = self.imported
        return dat

    def deserialize(self, data):
        super(SCSSBuildTarget, self).deserialize(data)
        self.compass = data.get('compass', False)
        self.import_paths = data.get('imports', [])
        self.output_style = data.get('style', 'compact')
        self.imported = data.get('imported', [])

    def get_config(self):
        return {'compass': self.compass, 'import-paths': self.import_paths, 'output-style': self.output_style}

    def build(self):
        sass_cmd = []

        if self.sass_path.endswith('.bat') or self.sass_path.endswith('.BAT'):
            RUBYDIR = os.path.dirname(self.sass_path)
            sass_cmd = [os.path.join(RUBYDIR, 'ruby.exe'),
                        os.path.join(RUBYDIR, 'sass')]
        else:
            sass_cmd = [self.sass_path]
        args = ['--scss', '--force', '-C', '-t', self.output_style]
        if self.compass:
            args += ['--compass']
        for import_path in self.import_paths:
            args += ['-I=' + import_path]

        #os_utils.ensureDirExists(os.path.join('tmp', os.path.dirname(self.target)))
        os_utils.ensureDirExists(os.path.dirname(self.target))
        os_utils.cmd(sass_cmd + args + self.files + [self.target], critical=True, echo=False, show_output=True)


class SCSSConvertTarget(SingleBuildTarget):
    BT_TYPE = 'SCSSConvert'
    BT_LABEL = 'SCSSCONVERT'

    def __init__(self, target=None, files=[], dependencies=[], sass_convert_path=None):
        super(SCSSConvertTarget, self).__init__(target, files, dependencies)
        if sass_convert_path is None:
            sass_convert_path = os_utils.which('sass-convert')
            if sass_convert_path is None:
                log.warn('Unable to find sass-convert on this OS.  Is it in PATH?  Remember to run `gem install sass compass`!')
        self.sass_convert_path = sass_convert_path

    def get_config(self):
        return [self.sass_convert_path]

    def build(self):
        sass_cmd = []
        if self.sass_convert_path.endswith('.bat') or self.sass_convert_path.endswith('.BAT'):
            RUBYDIR = os.path.dirname(self.sass_convert_path)
            sass_cmd = [os.path.join(RUBYDIR, 'ruby.exe'), os.path.join(RUBYDIR, 'sass-convert')]
        else:
            sass_cmd = [self.sass_convert_path]
        args = ['-F', 'css', '-T', 'scss', '-C']
        #os_utils.ensureDirExists(os.path.join('tmp', os.path.dirname(self.target)))
        os_utils.ensureDirExists(os.path.dirname(self.target))
        os_utils.cmd(sass_cmd + args + self.files + [self.target], critical=True, echo=False, show_output=True)


class SVG2PNGBuildTarget(SingleBuildTarget):
    BT_TYPE = 'SVG2PNG'
    BT_LABEL = 'SVG2PNG'

    def __init__(self, target, inputfile, height, width, dependencies=[], inkscape=None):
        self.height = height
        self.width = width

        self.inkscape = inkscape
        if self.inkscape is None:
            # Last-ditch for Windows.
            self.inkscape = os_utils.which('inkscape') or 'C:\\Program Files\\Inkscape\\inkscape.exe'

        super(SVG2PNGBuildTarget, self).__init__(target, files=[inputfile], dependencies=dependencies)

    def get_config(self):
        return {'height': self.height, 'width': self.width, 'path': self.inkscape}

    def build(self):
        os_utils.ensureDirExists(os.path.dirname(self.target))
        os_utils.cmd([self.inkscape, '-z', '-e', self.target, '-h', str(self.height), '-w', str(self.width), self.files[0]], critical=True, echo=False, show_output=True)


class ICOBuildTarget(SingleBuildTarget):
    BT_TYPE = 'ICO'
    BT_LABEL = 'ICO'

    def __init__(self, target, inputfiles, dependencies=[], convert_executable=None):
        self.convert_executable = convert_executable
        if self.convert_executable is None:
            self.convert_executable = os_utils.which('convert')
        super(ICOBuildTarget, self).__init__(target, files=inputfiles, dependencies=dependencies)

    def get_config(self):
        return {'path': self.convert_executable}

    def build(self):
        os_utils.ensureDirExists(os.path.dirname(self.target))
        command_line = [self.convert_executable]
        command_line += [os.path.relpath(x, os.getcwd()) for x in self.files]
        command_line += [os.path.relpath(self.target, os.getcwd())]
        os_utils.cmd(command_line, critical=True, echo=False, show_output=True)


class UglifyJSTarget(SingleBuildTarget):
    BT_TYPE = 'UglifyJS'
    BT_LABEL = 'UGLIFYJS'

    def __init__(self, target, inputfile, dependencies=[], compress=True, mangle=True, options=[], compress_opts=[], mangle_opts=[], uglify_executable=None):
        self.uglifyjs_executable = uglify_executable
        if self.uglifyjs_executable is None:
            self.uglifyjs_executable = os_utils.which('uglifyjs')

        self.options = []
        if compress:
            self.options += ['-c'] + compress_opts
        if mangle:
            self.options += ['-m'] + mangle_opts

        self.options += options
        super(UglifyJSTarget, self).__init__(target, files=[inputfile], dependencies=dependencies)

    def get_config(self):
        return {'path': self.uglifyjs_executable, 'opts':self.options}

    def build(self):
        cmdline = [self.uglifyjs_executable] + self.options + ['-o', self.target, self.files[0]]
        os_utils.cmd(cmdline, critical=True, echo=False)


class MinifySVGTarget(SingleBuildTarget):
    BT_TYPE = 'MinifySVG'
    BT_LABEL = 'SVGO'

    def __init__(self, target, source, dependencies=[], svgo_opts=['-q']):
        self.source = source
        self.svgo_opts = svgo_opts
        self.svgo_cmd = os_utils.which('svgo')
        if self.svgo_cmd is None:
            log.warn('Unable to find svgo on this OS.  Is it in PATH?  Remember to run `npm install -g svgo`!')

        super(MinifySVGTarget, self).__init__(target, dependencies=dependencies, files=[
            self.source, os.path.abspath(__file__)])

    def build(self):
        os_utils.ensureDirExists(os.path.dirname(self.target))
        os_utils.cmd([self.svgo_cmd, '-i', self.source, '-o', self.target] + self.svgo_opts, echo=False, show_output=True, critical=True)


REG_IMAGEURL = re.compile(r'url\("([^"]+)"\)')
def convert_imgurls_to_dataurls(infile, outfile, basedir):
    def _convert_img2data(m):
        # log.info(m.group(0))
        url = m.group(1)
        if url.startswith('data:'):
            return m.group(0)
        return 'url("{}")'.format(utils.img2blob(os.path.join(basedir, url)).strip())
    with codecs.open(infile, 'r') as inf:
        with codecs.open(outfile, 'w') as outf:
            for line in inf:
                outf.write(REG_IMAGEURL.sub(_convert_img2data, line))


class DatafyImagesTarget(SingleBuildTarget):
    BT_TYPE = 'DatafyImages'
    BT_LABEL = 'DATAFYIMAGES'

    def __init__(self, target, infile, basedir, dependencies=[]):
        self.infile = infile
        self.basedir = basedir
        super(DatafyImagesTarget, self).__init__(target, dependencies=dependencies, files=[infile, os.path.abspath(__file__)])

    def build(self):
        convert_imgurls_to_dataurls(self.infile, self.target, self.basedir)
