'''
ActionScript3-related shit

Copyright (c) 2015 - 2021 Rob "N3X15" Nelson <nexisentertainment@gmail.com>

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
import re
import shutil

from .indentation import getIndentChars

def calculateNewImports(readImports, requiredImports):
    # print(repr(readImports))
    newImports = []
    for imp in requiredImports:
        chunks = imp.split('.')
        chunks[-1] = '*'
        genimport = '.'.join(chunks)
        if genimport in readImports or imp in readImports:
            continue
        else:
            newImports += [imp]
    return newImports


def ensureConditionalImports(filename, matchToImports, sort=False):
    requires = []
    with open(filename, 'r') as f:
        for line in f:
            line = line.strip()
            for match, imports in matchToImports.items():
                if re.search(match, line) is not None:
                    requires += [i for i in imports if i not in requires]
    if len(requires) > 0:
        ensureImportsExist(filename, requires, sort=sort)


def ensureImportsExist(filename, requiredImports, sort=False):
    REG_IMPORT_STOP_A = re.compile(r'(public|private) (class|function)')
    REG_IMPORT_STOP_B = re.compile(r'/\*\*')
    REG_IMPORT = re.compile(r'import ([a-zA-Z0-9_\.\*]+);')

    def matches(line, regex, action=None):
        m = regex.search(line)
        if m is not None:
            if action is not None:
                action(line, m)
            return True
        return False
    readImports = []
    with open(filename, 'r') as f:
        with open(filename + '.tmp', 'w') as w:
            ln = 0
            #lastIndent = ''
            writingImports = True
            for line in f:
                ln += 1
                oline = line
                currentLine = line.lstrip().strip('\r\n')
                indent = getIndentChars(oline)
                line = line.strip()
                if writingImports:
                    m = REG_IMPORT.search(line)
                    if m is not None:
                        readImports += [m.group(1)]
                        #lastIndent = indent
                        if sort:
                            continue
                    if matches(line, REG_IMPORT_STOP_A) or matches(line, REG_IMPORT_STOP_B):
                        added = calculateNewImports(readImports, requiredImports)
                        if sort:
                            added += readImports
                            added.sort()
                        if added:
                            for newImport in sorted(added):
                                w.write(u'{}import {};\n'.format(indent, newImport))
                            w.write('\n')
                        writingImports = False
                w.write(indent + currentLine + '\n')
    shutil.copy(filename + '.tmp', filename)
    os.remove(filename + '.tmp')
