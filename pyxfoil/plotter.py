import os, sys

cwd = os.getcwd() + '/'

def get_polar_info(filename):
    os.chdir(cwd)
    polarcontents = file(cwd + 'savedpolars/' + filename, 'r').readlines()
    naca = polarcontents[3].rstrip()[-4:]
    re = eval(polarcontents[8][24:43].strip().replace(' ', ''))
    lastalfa = polarcontents[-1].lstrip().split()[0]

    os.chdir(cwd)
    if '---' not in lastalfa:
        return naca, re, eval(lastalfa)
    return naca, re, None

def histogram(filename='divplot', threshold=5.0):
    os.chdir(cwd)
    plotfile = file(filename + '.txt', 'w')
    printables = [f for f in os.listdir(cwd + 'savedpolars/') if f.endswith('.pol')]
    plotfile.write('Threshold at ' + str(threshold))

    plotdict = dict()
    for filename in printables:
        n, r, a = get_polar_info(filename)
        
        if n not in plotdict:
            plotdict[n] = dict()
        plotdict[n][r] = a

    maxdigits = len(str(max(map(int, plotdict[plotdict.keys()[0]].keys()))))

    for naca in sorted(plotdict.keys()):
        plotfile.write('\n\n ' + '#'*15 + ' Airfoil: ' + naca + ' ' + '#'*15)
        plotfile.write('\n ' + 'Reynolds Number'.center(maxdigits + 1))
        for re in sorted(plotdict[naca].keys()):
            plotline = '\n' + str(int(re)).rjust(maxdigits + 1)
            plotline += (' *' * min(max(0, int(threshold)-1), int(plotdict[naca][re]))).ljust(2* max(0, int(threshold)-1)) + '|'
            if plotdict[naca][re] > threshold:
                plotline += (' *' * (1 + int(plotdict[naca][re])-int(threshold)))[1:]
            plotfile.write(plotline + ' (' + str(plotdict[naca][re]) + ') ')
    plotfile.close()
