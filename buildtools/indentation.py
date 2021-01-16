'''
File indentation stuff for my OCD :V

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
from buildtools.bt_logging import log
class IndentWriter(object):

    def __init__(self, fh, indent_level=0, indent_chars='\t', variables={}):
        self._f = fh
        self.indent_level = indent_level
        self.indent_chars = indent_chars
        self.variables = variables

    def writeline(self, string=''):
        if string == '':
            self._f.write('\n')
        else:
            self._f.write('{}{}\n'.format((self.indent_chars * self.indent_level), self.format(string)))
        return self

    def format(self, string):
        for key, value in self.variables.items():
            string = string.replace('{{{}}}'.format(key), str(value))
        return string

    def __enter__(self):
        self.indent_level += 1

    def __exit__(self, type, value, traceback):
        self.indent_level -= 1


def countIndents(line, div=1):
    i = 0
    for c in line:
        if c == ' ':
            i += 1
        elif c == '\t':
            i += 4
        else:
            return i
    return i/div


def getIndentChars(line):
    buf = ''
    for c in line:
        if c == ' ' or c == '\t':
            buf += c
        else:
            return buf
    return buf


def GenIndentDeltas(lines):
    lastIndent = 0
    currentIndent = 0
    diff = 0
    lineInfo = []
    for ln in range(len(lines)):
        line = lines[ln]
        currentIndent = countIndents(line)
        if ln == 0:
            lastIndent = currentIndent
        if line.startswith('\b'):
            currentIndent = lastIndent
            line = line[1:]
        line = line.strip()
        if line.startswith('#'):
            lineInfo += [(None, 0, line)]
            continue
        diff = 0
        if currentIndent < lastIndent:
            diff = -1
        if currentIndent > lastIndent:
            diff = 1
        lineInfo += [(diff, currentIndent, line)]
        lastIndent = currentIndent
    return lineInfo


def writeGivenIndentData(writefunc, lines, writeIndentedLine, offsets=0, override_writeindented=None):
    indent = 0
    indentOffsets = ['manuallyoffset'] * offsets

    def innerwriteindented(curindent, line):
        writefunc(' ' * (curindent * 4) + line + '\n')

    def writeindented(line, indentOffset, offset=0):
        innerwriteindented((indent + indentOffset), line)
    if override_writeindented:
        innerwriteindented = override_writeindented
    nLines = len(lines)
    lastLineIndented = False
    for i in range(nLines):
        diff, currentIndent, line = lines[i]
        ndiff = None
        ndiffidx = 1
        while ndiff is None:
            if i + ndiffidx < nLines:
                ndiff, _, _ = lines[i + ndiffidx]
                ndiffidx += 1
            else:
                break
        if diff is None:
            line = line.strip()
            if line.startswith('#comment'):
                continue
            if line.startswith('#startblock'):
                statement = line[12:].strip()
                if ndiff == 1:
                    indentOffsets.append(statement)
                writeindented(statement, len(indentOffsets))
                if ndiff < 1:
                    indentOffsets.append(statement)
                continue
            if line == '#endblock':
                statement = indentOffsets.pop()
                writeindented('# END {}'.format(statement), len(indentOffsets))
                continue
            log.error('UNKNOWN TEMPLATE ENGINE COMMAND: ' + line.strip())
            continue
        indent = max(indent + diff, 0)
        lastLineIndented = writeIndentedLine(indent, diff, ndiff, line, len(indentOffsets), writeindented)


def escapePython(line):
    return line.replace("'", "\\'").replace('\\', '\\\\')


def _writePythonIndentWriterLine(indent, diff, ndiff, line, indentOffset, writeindented):
    if ndiff > 0:  # If next line indents:
        writeindented('with w.writeline(\'{}\'):'.format(escapePython(line)), indentOffset, offset=-1)
        # writeindented(line)
        #indent += 1
        return True
    else:
        if line == '':
            writeindented('w.writeline()', indentOffset)
        else:
            writeindented('w.writeline(\'{}\')'.format(escapePython(line)), indentOffset)
        # writeindented(line)
        return False


def _writeBasicCorrectedIndent(indent, diff, ndiff, line, indentOffset, writeindented):
    # linedbg=/*{} {}*/'.format(diff, ndiff)
    # writeindented(linedbg+line,indentOffset)
    writeindented(line, indentOffset)
    return ndiff > 0


def writeIndentWriterTemplate(writefunc, lines, offset=0):
    writeGivenIndentData(writefunc, GenIndentDeltas(lines), _writePythonIndentWriterLine, offset)


def writeReindentedViaIndentWriter(w, lines, offset=0):
    oldil = w.indent_level

    def _mywriteindented(indent, line):
        w.indent_level = indent
        w.writeline(line)
    writeGivenIndentData(None, GenIndentDeltas(lines), _writeBasicCorrectedIndent, offset, override_writeindented=_mywriteindented)
    w.indent_level = oldil


def writeReindented(writefunc, lines, offset=0):
    writeGivenIndentData(writefunc, GenIndentDeltas(lines), _writeBasicCorrectedIndent, offset)


def test_deltas():
    TestData = [
        '0',
        '0',
        '    1',
        '    0',
        '-1'
    ]
    i = 0
    for diff, currentIndent, line in GenIndentDeltas(TestData):
        i += 1
        realdiff = int(line.strip())
        if realdiff != diff:
            print(i, '{} != {}'.format(realdiff, diff))
