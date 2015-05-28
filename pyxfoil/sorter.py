import os, sys

cwd = os.getcwd() + '/'

def parse_polar_name(polarname):
    airfoil = polarname[4:8]
    re = int(polarname[11:19])*1000
    return airfoil, re

def get_last_point(filename, filepath=cwd+'savedpolars/'):
    polar = open(filepath + filename, "r")
    lines = polar.readlines()
    return float(lines[-2].rstrip().split()[0])

def cutoff_generator(threshold):
    def f(dct):
        return dct['a'] < threshold
    return f

def startswith_generator(prefix, invert=False):
    def f(string):
        return invert != string.startswith(prefix)
    return f

def contains_generator(substring, invert=False):
    def f(string):
        return invert != substring in string
    return f

def dir_to_dict(polardir):
    polars = dict()
    savedpolars = os.listdir(polardir)
    for polarname in savedpolars:
        if polarname.startswith('NACA') and polarname.endswith('k.pol'):
            airfoil, re = parse_polar_name(polarname)
        else:
            continue
    
        if airfoil not in polars:
            polars[airfoil] = dict()
        if re not in polars[airfoil]:
            polars[airfoil][re] = list()
        try:
            if len(polars[airfoil][re]) == 0:
                polars[airfoil][re].append(float(get_last_point(polarname)))
            else:
                polars[airfoil][re][0] = max(polars[airfoil][re][0], float(get_last_point(polarname)))
        except ValueError:
            continue
    return polars

def file_to_dict(filepath, prefix=None, strip=False):
    polars = dict()
    contents = [line.rstrip() for line in file(filepath, 'r').readlines()]
    filtered = filter(startswith_generator(prefix), contents)
    for line in filtered:
        if strip:
            line = line.strip(prefix)
        literal = eval(line)

        if literal['airfoil'] not in polars:
            polars[literal['airfoil']] = dict()
        if literal['re'] not in polars[literal['airfoil']]:
            polars[literal['airfoil']][literal['re']] = list()
        if 'a' in literal:
            polars[literal['airfoil']][literal['re']].append(round(literal['a'], 3))
            polars[literal['airfoil']][literal['re']] = sorted(polars[literal['airfoil']][literal['re']])
    return polars

def dict_to_list(polardict):
    polar_list = [{'airfoil': af , 're': re, 'a': a} 
               for af in polardict.keys()
               for re in sorted(polardict[af].keys())
               for a in polardict[af][re]]
    return polar_list

#print '\n'.join(str(line) for line in earlies)
#print '\n'.join(str(line) for line in list(filter(cutoff_generator(5), dict_to_list(dir_to_dict(cwd + 'savedpolars')))))
