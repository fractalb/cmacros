#! /usr/bin/python3

from pathlib import Path
import sys
import re
import os
import readline

macro_start = re.compile(r'#[ \t]*define[ \t(]')
token_pattern = re.compile(r'([ \t]*)##([ \t]*)')
strip_chars = r"[()[\]{}.,?:;+\-=<>*^~|&%!/ \t\n\\]+"
macro_list = []
unique_filenames = set()

class Macro:
    def __init__(self, expr, params, body, filename, lineno):
        self.expr = expr
        self.params = [x.strip() for x in params] if params else []
        self.body = body
        self.filename = filename
        self.lineno = lineno
        self.regex_matchers = None

    def __str__(self):
        return "#define %s%s %s\n%s:%d\n" % (self.expr,
                ("(%s)" % ",".join(self.params)) if self.params is not None else "",
                self.body if self.body else "" , self.filename, self.lineno)

    def has_params(self):
        True if self.params else False
    
    def has_paste_tokens(self):
        True if "##" in self.body else False
   
    def get_regex_matchers(self):
        """replaces macro-parameters in the macro-body
        with regex pattern(r'\w*') and creates match object
        """
        if self.regex_matchers is not None:
            return self.regex_matchers
        if (not self.params) or (not self.body) or ("##" not in self.body):
            #no token-paste operators, no regex matchers
            self.regex_matchers = []
            return self.regex_matchers
        temp_value = self.body
        tlen = 0
        end_index = 0
        #search for token pasting operators and remove any white space on either side
        match = token_pattern.search(self.body)
        while match:
            mstr = match.group()
            tlen = len(mstr) #len("##") + possible extra spaces
            temp_value = temp_value[:end_index] + temp_value[end_index:].replace(mstr, "##")
            end_index += (match.end()-tlen+2)
            match = token_pattern.search(temp_value[end_index:])
        tokens = [x for x in re.split(strip_chars,temp_value)]
        pattern_string_list = []
        for x in tokens:
            if ("##" not in x) or x.startswith("##"):
                continue
            x = x.split("#")
            regex_pattern_string = "".join([r"\w*" if n in self.params else n for n in x])
            pattern_string_list.append(regex_pattern_string)
        self.regex_matchers = [re.compile(x) for x in pattern_string_list]
        return self.regex_matchers


def build_defs(p="."):
    file_pattern="*.[ch]"
    if not Path(p).exists(): 
        raise Exception("Path doesn't exist")
    global macro_list
    macro_list.clear()
    for fl in map(str, Path(p).rglob(file_pattern)):
        with open(fl, errors='ignore') as f:
            macrostr = None 
            lineno = None
            for (lno, line) in enumerate(f, start=1):
                line = line.strip()
                if macro_start.match(line):
                    assert macrostr is None
                    assert lineno is None
                    if line.endswith("\\"):
                        macrostr = line+"\n"
                        lineno = lno
                    else:
                        macro_obj = parse_macro(line, fl, lno)
                        if macro_obj:
                            macro_list.append(macro_obj)
                            unique_filenames.add(macro_obj.filename)
                        else:
                            print_err(line, fl, lno)
                elif macrostr:
                    assert isinstance(macrostr, str)
                    assert isinstance(lineno, int)
                    assert lineno is not None
                    macrostr += line
                    if line.endswith("\\"):
                        macrostr += "\n"
                    else:
                        macro_obj = parse_macro(macrostr, fl, lineno)
                        if macro_obj:
                            macro_list.append(macro_obj)
                            unique_filenames.add(macro_obj.filename)
                        else:
                            print_err(macrostr, fl, lineno)
                        macrostr = None
                        lineno = None
                else:
                    assert lineno is None


def print_err(macrostr, filename, lineno):
        print("%s:%d:Unable to parse\n%s" % (filename, lineno, macrostr))


def parse_macro(macrostr, filename, lineno):
    '''It expects no non-space characters between '#' and 'define'
    Not all valid strings are recognized.
    e.g # /*comments*/define AB BA
    The above string is not recognized even though it is
    valid in C. `#define` written in any exotic ways is not recognized
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
                    return Macro(macrostr[:par_index], macrostr[par_index+1:index].split(","),
                                                     macrostr[index+1:].lstrip(), filename, lineno)
        else:
            if c == "(":
                par_index = index
                paren = 1
            elif c == ")":
                #raise Exception("Cannot parse string: %s" % macrostr)
                return None
            elif c in " \t\n":
                return Macro(macrostr[:index], None,  macrostr[index+1:].lstrip(), filename, lineno)
    if paren > 0:
        #raise Exception("Malformed macro string: %s" % macrostr)
        return None
    else:
        return Macro(macrostr, None, None, filename, lineno)

def print_matching_macros(expr, fullmatch=True):
    i = 0
    if fullmatch:
        for x in macro_list:
            if expr == x.expr:
                print(x)
                i += 1
    elif expr:
        for x in macro_list:
            if expr in x.expr:
                print(x)
                i += 1
    else:
        for x in macro_list:
            print(x)
        i = len(macro_list)
    print("Total matching macros:%d" % i)

def main(source_path):
    build_defs(source_path)
    print("Total Macros:%d" % len(macro_list))
    while True:
        try:
            command_str = input('Def: ')
        except EOFError:
            break 

        if command_str == "":
            continue
        temp_list = command_str.split(None, 1)
        command = temp_list[0]
        args = temp_list[1] if len(temp_list) == 2 else None
        if command == "expr" and args:
            '''expr <text>
            lists macros which contain <text> in its expressions
            '''
            print_matching_macros(args)
        elif command == "body" and args:
            '''body <text>
            lists macros which contain the given <text> in their bodies OR
            lists macros which can expand to the given <text>
            '''
            n = 0
            for (i,x) in enumerate(macro_list):
                y = x.get_regex_matchers()
                for z in y:
                    match = z.search(args)
                    if match:
                        print("Macro:%d" % i)
                        print(x)
                        n += 1
                        break
            print("Total possible macros:%d" % n)
        elif command == "list":
            '''list <text>
            lists macros which contain the given <text> in its macro expression
            lists all macros if no <text>
            '''
            print_matching_macros(args, fullmatch=False)
        elif command == "from" and args:
            '''from <file>
            lists macros from the given <file>
            '''
            for x in macro_list:
                if  x.filename.endswith(os.sep+args):
                    print(x)
        elif command == "files":
            '''lists all the files which contain macros'''
            for x in unique_filenames:
                print(x)
            print("Total files with Macros: %d" % len(unique_filenames))
            

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("Source directory path is required as argument")
        exit()
    #can't handle if there are spaces in the path
    main(sys.argv[1])
