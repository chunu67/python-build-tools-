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
        inp = sys.stdin.read(1)
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
