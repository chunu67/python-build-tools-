'''
The script that generates all of these nice headers for my lazy ass.

Copyright (c) 2015 - 2020 Rob "N3X15" Nelson <nexisentertainment@gmail.com>

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

import os
import sys
import re
import jinja2
from datetime import date
import argparse

REG_COPYHOLDER = re.compile('copyright \(c\)\s*(?P<years>[0-9\- ]+) (?P<holder>.*)$', re.IGNORECASE)


class CopyrightChecker(object):

    def __init__(self, template, holder, origYear):
        template = os.path.abspath(template)
        if not os.path.isfile(template):
            print('E: {} does not exist.'.format(template))
            sys.exit(1)
        with open(template, 'r') as f:
            self.template = jinja2.Template(f.read(), autoescape=False)

        self.holder = holder
        self.currentYear = int(date.today().year)
        self.origYear = origYear

        self.begin_tag = "'''"
        self.end_tag = "'''"
        self.line_prefix = ''

    def formatYear(self):
        if self.origYear != self.currentYear:
            return '{} - {}'.format(self.origYear, self.currentYear)
        else:
            return '{}'.format(self.currentYear)

    def writeHeader(self, outf, blurb, docBuf, line, new_header):
        outf.write(self.begin_tag + '\n')

        lictext = self.template.render(HOLDER=self.holder, YEAR=self.formatYear(), BLURB=blurb)

        outf.write(''.join([self.line_prefix + x.rstrip() + '\n' for x in lictext.split('\n')]))

        outf.write('\n')
        outf.write(docBuf)
        outf.write(self.end_tag + "\n")
        if line[:-3].rstrip() != '' and not new_header:
            outf.write(line[:-3].rstrip() + "\n")

    def scanFile(self, infilename, outfilename):
        headerBuf = ''
        docBuf = ''
        hasReadHeader = ''
        inHeader = False
        inDoc = False
        enteredBody = False
        blurb = None

        with open(infilename, 'r') as inf:
            with open(outfilename, 'w') as outf:
                for line in inf:
                    line = line.rstrip()
                    line_s = line.strip()

                    if not inHeader:
                        if line_s.startswith(self.begin_tag) and not hasReadHeader and not enteredBody:
                            inHeader = True
                            hasReadHeader = True
                            firstline = line[3:]
                            if firstline.strip() != '':
                                headerBuf += firstline
                                blurb = firstline
                        else:
                            if line_s != '':
                                if not hasReadHeader and not enteredBody:
                                    blurb = 'BLURB GOES HERE.'
                                    self.writeHeader(outf, blurb, docBuf, line, True)
                                enteredBody = True
                            outf.write(line + '\n')
                    else:
                        if line_s.endswith(self.end_tag):
                            self.writeHeader(outf, blurb, docBuf, line, False)
                            inHeader = False
                            continue
                        if line_s.startswith('@') or line_s.startswith(':') or line_s.startswith('..'):
                            inDoc = True
                        if inDoc:
                            docBuf += line + '\n'
                        else:
                            if blurb is None:
                                blurb = line
                                continue
                            headerBuf += line + '\n'

    def scanFiles(self, path, exts=['.py']):
        for root, _, files in os.walk(path):
            for file in files:
                fullpath = os.path.join(root, file)
                relpath = os.path.relpath(fullpath)
                filename = os.path.basename(fullpath)
                _, ext = os.path.splitext(filename)

                if ext not in exts:
                    #print(' Skipping {} ({})'.format(relpath, ext))
                    continue

                relpathchunks = relpath.split(os.sep)
                # print(repr(relpathchunks))
                relpathchunks[0] += '-fixed'
                fixedpath = os.sep.join(relpathchunks)
                fixedpathdir = os.path.dirname(fixedpath)
                if not os.path.isdir(fixedpathdir):
                    os.makedirs(fixedpathdir)
                self.scanFile(fullpath, fixedpath)
                print('>>>', relpath)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Add/update license headers.')

    parser.add_argument('-L', '--license', type=str, help='License template. Jinja2 provides HOLDER, YEAR, and BLURB variables.')
    parser.add_argument('-H', '--holder', type=str, help='Name(s) of the copyright holder(s).')
    parser.add_argument('-Y', '--year', type=int, help='Year (can be a range)')
    parser.add_argument('-x', '--ext', dest='exts', nargs='*', default=['.py'], help='Extensions to scan.')
    parser.add_argument('-s', '--start-tag', type=str, nargs='?', default="'''", help='What the beginning of a block comment looks like.')
    parser.add_argument('-e', '--end-tag', type=str, nargs='?', default="'''", help='What the end of a block comment looks like.')

    parser.add_argument('path', type=str, nargs='+', help='Where to look for licensed files.')

    args = parser.parse_args()

    if not os.path.isfile(args.license):
        print('E: License file doesn\'t exist.')
        sys.exit(1)

    legal = CopyrightChecker(args.license, args.holder, args.year)
    legal.begin_tag = args.start_tag
    legal.end_tag = args.end_tag
    for path in args.path:
        if os.path.isdir(path):
            legal.scanFiles(path, exts=args.exts)
        elif os.path.isfile(path):
            legal.scanFile(path, path + '.fixed')
