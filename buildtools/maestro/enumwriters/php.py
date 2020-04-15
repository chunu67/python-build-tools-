'''
BLURB GOES HERE.

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
from .enumwriter import EnumWriter
class PHPEnumWriter(EnumWriter):
    def __init__(self, compressed):
        super().__init__()
        self.compressed = compressed

    def get_config(self):
        return {'compressed':self.compressed}

    def write(self, w, definition):
        name = definition['name']
        phpdef = definition.get('php',{})
        extends = phpdef.get('extends','SplEnum')
        namespace = phpdef.get('namespace',None)

        w.write('<?php /* @generated by BUILD.py */')
        if not self.compressed: w.write('\n')
        if namespace is not None:
            w.write('namespace {};'.format(namespace))
            if not self.compressed: w.write('\n')
        w.write('class {} extends {} {{'.format(name, extends))
        if not self.compressed: w.write('\n  ')
        w.write('const __default = {};'.format(definition.get('default',0)))
        if definition.get('flags', False):
            if not self.compressed: w.write('\n  ')
            w.write('const NONE = 0;')

        if not definition.get('flags', False):
            if not self.compressed: w.write('\n  ')
            w.write('const MIN = {!r};'.format(min([self.parent._get_value_for(x) for x in definition['values'].values()])))
            if not self.compressed: w.write('\n  ')
            w.write('const MAX = {!r};'.format(max([self.parent._get_value_for(x) for x in definition['values'].values()])))
            if not self.compressed: w.write('\n\n')
        else:
            allofem=0
            for x in definition['values'].values():
                allofem |= self.parent._get_value_for(x)
            if not self.compressed:
                w.write('\n  //  b{0:032b}'.format(allofem))
                w.write('\n  // 0x{0:0X}'.format(allofem))
                w.write('\n  ')
            w.write('const ALL = {};'.format(allofem))

        for k,vpak in definition['values'].items():
            v=self.parent._get_value_for(vpak)
            meaning=self.parent._get_meaning_for(vpak)
            padding = '' if self.compressed else '\n  '
            if meaning == '':
                if not self.compressed: w.write(padding)
            else:
                if not self.compressed:
                    w.write('{PAD}/**{PAD} * {MEANING}{PAD} */{PAD}'.format(PAD=padding, MEANING=meaning))
                else:
                    w.write('/* {} */'.format(meaning))
            w.write('const {} = {};'.format(k,repr(v)))

        if definition.get('flags',False):
            if not self.compressed: w.write('\n  ')
            w.write('public static function ValueToStrings(int $val){')
            if not self.compressed: w.write('\n    ')
            w.write('$o=[];')
            if not self.compressed: w.write('\n    ')
            w.write('for($bitidx=0;$bitidx<32;$bitidx++){')
            if not self.compressed: w.write('\n      ')
            w.write('switch($val&(1<<$bitidx)){')
            for k,vpak in definition['values'].items():
                v=self.parent._get_value_for(vpak)
                if not self.compressed: w.write('\n        ')
                w.write('case {}:'.format(repr(v)))
                if not self.compressed: w.write('\n          ')
                w.write('$o[]={};'.format(repr(k)))
                if not self.compressed: w.write('\n          ')
                w.write('break;')
            if not self.compressed: w.write('\n        ')
            w.write('}') # switch($val)
            if not self.compressed: w.write('\n    ')
            w.write('}') # for($bitidx=1;$i<32;$i++)
            if not self.compressed: w.write('\n    ')
            w.write('return $o;')
            if not self.compressed: w.write('\n  ')
            w.write('}')

        if not self.compressed: w.write('\n  ')
        w.write('public static function ValueToString(int $val, string $sep=",", string $start_end=""){')
        if not definition.get('flags', False):
            if not self.compressed: w.write('\n    ')
            w.write('$o=null;')
            if not self.compressed: w.write('\n    ')
            w.write('switch($val){')
            for k,vpak in definition['values'].items():
                v=self.parent._get_value_for(vpak)
                if not self.compressed: w.write('\n      ')
                w.write('case {}:'.format(repr(v)))
                if not self.compressed: w.write('\n        ')
                w.write('$o={};'.format(repr(k)))
                if not self.compressed: w.write('\n        ')
                w.write('break;')
            if not self.compressed: w.write('\n      ')
            w.write('}') # switch($val)
        else:
            if not self.compressed: w.write('\n    ')
            w.write('$o=implode($sep,self::ValueToStrings($val));')

        if not self.compressed: w.write('\n    ')
        w.write('if (strlen($start_end)==2){')
        if not self.compressed: w.write('\n      ')
        w.write('$o=substr($start_end,0,1).$o.substr($start_end,1,1);')
        if not self.compressed: w.write('\n    ')
        w.write('}')
        if not self.compressed: w.write('\n    ')
        w.write('return $o;')
        if not self.compressed: w.write('\n  ')
        w.write('}') # ValueToString

        if not self.compressed: w.write('\n  ')
        w.write('public static function StringToValue(string $key){')
        if not self.compressed: w.write('\n    ')
        w.write('switch($key) {')
        for k,vpak in definition['values'].items():
            v=self.parent._get_value_for(vpak)
            if not self.compressed: w.write('\n      ')
            w.write('case {}:'.format(repr(k)))
            if not self.compressed: w.write('\n        ')
            w.write('return {};'.format(repr(v)))
        if not self.compressed: w.write('\n    ')
        w.write('}') # switch($val)
        if not self.compressed: w.write('\n    ')
        w.write('return -1;')
        if not self.compressed: w.write('\n  ')
        w.write('}') # StringToValue

        if not self.compressed: w.write('\n  ')
        w.write('public static function Keys(){')
        if not self.compressed: w.write('\n    ')
        w.write('return [{}];'.format(', '.join([repr(x) for x in definition['values'].keys()])))
        if not self.compressed: w.write('\n  ')
        w.write('}') # Keys()

        if not self.compressed: w.write('\n  ')
        w.write('public static function Values(){')
        if not self.compressed: w.write('\n    ')
        w.write('return [{}];'.format(', '.join([repr(self.parent._get_value_for(x)) for x in definition['values'].values()])))
        if not self.compressed: w.write('\n  ')
        w.write('}') # Values()

        if not self.compressed: w.write('\n  ')
        w.write('public static function Count(){')
        if not self.compressed: w.write('\n    ')
        w.write('return {};'.format(len(definition['values'].keys())))
        if not self.compressed: w.write('\n  ')
        w.write('}') # Count()


        if not self.compressed: w.write('\n')
        w.write('}') # class