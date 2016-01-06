'''
Commandline things.

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

'''
import os
import sys


def _formatChoices(choices, default):
    choice_list = []
    for choice in choices:
        if choice == default:
            choice = '[{}]'.format(choice)
        choice_list.append(choice)
    return ' ({})'.format('/'.join(choice_list))


def getInputChar(prompt, valid, default):
    '''
    Get a char from the user.
    '''
    prompt += _formatChoices(valid, default)
    while True:
        print(prompt)
        print(' > ')
        inp = sys.stdin.read(1).lower()
        print()
        if inp == '' and default is not None:
            return default
        if inp in valid:
            return inp


def getInputLine(prompt, choices=None, default=None):
    '''
    Get a line from the user.
    '''
    if choices is not None:
        prompt += _formatChoices(choices, default)
    else:
        if default is not None:
            prompt += ' [{}]'.format(default)
    while True:
        print(prompt)
        inp= raw_input(' > ')
        #inp = sys.stdin.readline()
        #print()
        #inp = raw_input()
        if inp == '' and default is not None:
            return default
        if choices is None or inp in choices:
            return inp
