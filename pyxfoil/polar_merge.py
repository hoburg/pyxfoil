import os, sys

os.chdir(os.getcwd() + '/savedpolars')
def interleave(lst1, lst2):
    final = ""
    while len(lst1) > 0 and len(lst2) > 0:
        line1 = lst1[0]
        line2 = lst2[0]
        if line1[0] > line2[0]:
            final += lst2.pop(0)
        elif line1[0] == line2[0]:
            final += lst1.pop(0)
            lst2.pop(0)
        else:
            final += lst1.pop(0)

    if len(lst1) > 0:
        final += ''.join(l for l in lst1)
    if len(lst2) > 0:
        final += ''.join(l for l in lst2)
    return final

try:
    os.popen('mkdir mergedump')
except OSError:
    None

ls = os.popen("ls").readlines()
polar_list = [l.rstrip()[:-9] for l in os.popen("ls").readlines() if l[:4]=="NACA" and "aug" in l]

for pol in polar_list:
    polar_default = file(pol + '.pol', 'r').readlines()[:12]
    polar_original = file(pol + '.pol', 'r').readlines()
    polar_augment = file(pol + '_aug1.pol', 'r').readlines()
    os.popen('mv ' + pol + '.pol mergedump')
    os.popen('mv ' + pol + '_aug1.pol mergedump')
    file(pol + '.pol', 'w').write(''.join(l for l in polar_default) + interleave(polar_original[12:], polar_augment[12:]))

def merge_filled(polardir):
    os.chdir(polardir)
    
