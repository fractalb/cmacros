#! /usr/bin/python3

from pathlib import Path
import re
#import pdb

defstart = re.compile(r'#[ \t]*define[ \t(]')
tokentest = re.compile(r'([ \t]*)##([ \t]*)')
stripchars = r"[()[\]{}.,?:;+\-=<>*^~|&%!/ \t\n\\]+"
defs = []

class Defline:
    def __init__(self, expr, params, value, filename, lno):
        self.expr = expr
        self.params = [x.strip() for x in params] if params else []
        self.value = value
        self.filename = filename
        self.lno = lno
        self.regex_matchers = None

    def __str__(self):
        return "#define %s%s %s\n%s:%d\n" % (self.expr,
                ("(%s)" % ",".join(self.params)) if self.params is not None else "",
                self.value if self.value else "" , self.filename, self.lno)

    def has_params(self):
        True if self.params else False
    
    def has_paste_tokens(self):
        True if "##" in value else False
   
    def get_regex_matchers(self):
        if self.regex_matchers is not None:
            return self.regex_matchers
        if (not self.params) or (not self.value) or ("##" not in self.value):
            self.regex_matchers = []
            return self.regex_matchers
        temp_value = self.value

        tlen = 0
        end_index = 0
        match = tokentest.search(self.value)
        while match:
            mstr = match.group()
            tlen = len(mstr)
            temp_value = temp_value[:end_index] + temp_value[end_index:].replace(mstr, "##")
            end_index += (match.end()-tlen+2)
            match = tokentest.search(temp_value[end_index:])
        tokens = [x for x in re.split(stripchars,temp_value)]
        newtokens = []
        #pdb.set_trace()
        for x in tokens:
            if "##" not in x:
                continue
            x = x.split("#")
            _tmp = "".join([r"\w*" if n in self.params else n for n in x])
            newtokens.append(_tmp)
        self.regex_matchers = [re.compile(x) for x in newtokens]
        return self.regex_matchers


def build_defs(p="."):
    file_pattern="*.[ch]"
    if not Path(p).exists(): 
        raise Exception("Path doesn't exist")
    global defs
    defs.clear()
    for fl in map(str, Path(p).rglob(file_pattern)):
        with open(fl, errors='ignore') as f:
            defline = None 
            lineno = None
            for (lno, line) in enumerate(f, start=1):
                line = line.strip()
                if defstart.match(line):
                    assert defline is None
                    assert lineno is None
                    if line.endswith("\\"):
                        defline = line+"\n"
                        lineno = lno
                    else:
                        obj = split_n_save_macro(line, fl, lno)
                        if obj:
                            defs.append(obj)
                        else:
                            print_err(line, fl, lno)
                elif defline:
                    assert isinstance(defline, str)
                    assert isinstance(lineno, int)
                    assert lineno is not None
                    defline += line
                    if line.endswith("\\"):
                        defline += "\n"
                    else:
                        obj = split_n_save_macro(defline, fl, lineno)
                        if obj:
                            defs.append(obj)
                        else:
                            print_err(defline, fl, lineno)
                        defline = None
                        lineno = None
                else:
                    assert lineno is None

def print_err(macrostr, filename, lno):
        print("%s:%d:Unable to parse\n%s" % (filename, lno, macrostr))

def split_n_save_macro(macrostr, filename, lno):
    '''The macro string should not be written in exotic ways
    Not all valid strings are recognized.
    e.g /* */# /**/define AB BA
    The above string is not recognized even though it is
    valid in C. `#define` should not be written in exotic ways.
    Some valid examples:
    #define <something>
    #define <something> <otherthing>
    #    define <something> <otherthing>
    #define <something(x,y..)> <expansion>
    '''
    assert (isinstance(macrostr, str))
    (defstr, macrostr) = macrostr.split(None, 1)
    if not macrostr:
        #raise Exception("Invalid string given")
        return None
    elif defstr == "#define":
        pass
    elif defstr == "#":
        (defstr, macrostr) =  macrostr.split(None, 1)
        if defstr != "define":
            #raise Exception("Invalid string given")
            return None
        else: pass
    else:
        #raise Exception("Invalid string given")
        return None

    paren = 0
    for (index, c) in enumerate(macrostr):
        if paren > 0:
            if c == "(":
                paren += 1
                continue
            elif c == ")":
                paren -= 1
                if paren == 0:
                    return Defline(macrostr[:par_index], macrostr[par_index+1:index].split(","),
                                                     macrostr[index+1:].lstrip(), filename, lno)
        else:
            if c == "(":
                par_index = index
                paren = 1
            elif c == ")":
                #raise Exception("Cannot parse string: %s" % macrostr)
                return None
            elif c in " \t\n":
                return Defline(macrostr[:index], None,  macrostr[index+1:].lstrip(), filename, lno)
    if paren > 0:
        #raise Exception("Malformed macro string: %s" % macrostr)
        return None
    else:
        return Defline(macrostr, None, None, filename, lno)

def get_def(defstr):
    deflist = []
    for x in defs:
        if defstr == x.expr:
            deflist.append(x)
    return deflist


def main(source_path):
    build_defs(source_path)
    print("total deflines:%d" % len(defs))
    history = History()
    while True:
        try:
            answer = get_input('Def: ', history=history).lstrip()
        except EOFError:
            break 
        if answer == "":
            continue

        temp_list = answer.split(None, 1)
        command = temp_list[0]
        args = temp_list[1] if len(temp_list) == 2 else None
        if command == "head" and args:
            x = get_def(args)
            for y in x:
                print(y)
        elif command == "tail" and args:
            for (i,x) in enumerate(defs):
                y = x.get_regex_matchers()
                for z in y:
                    match = z.search(args)
                    if match:
                        print("Defline:%d" % i)
                        print(x)
                        break
            

#from prompt_toolkit.contrib.completers import PathCompleter
#from prompt_toolkit.contrib.completers import WordCompleter
from prompt_toolkit.shortcuts import get_input
from prompt_toolkit.history import History
import sys

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Source directory path is required as argument")
        exit()
    #can't handle if there are spaces in the path
    main(sys.argv[1])
