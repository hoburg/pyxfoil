import os, sys

path = os.getcwd()
polars = os.listdir(path + '/savedpolars/')
logpath = path + '/logs/'
polarpath = path + '/savedpolars/'
os.chdir(logpath)

def get_last_point(filename, filepath=polarpath):
    polar = open(filepath + filename, "r")
    lines = polar.readlines()
    return lines[-1].rstrip().split()[0]

def polarname(naca, re):
    return "NACA" + naca + "_Re" + str(int(float(re)/1000)).zfill(8) + "k.pol" 

def clean_line(line):
    print line.rstrip().split('//')[0]
    return line.rstrip().split('//')[0]

if len(sys.argv) == 2:
    raw_file = open(sys.argv[1], 'r')
else:
    raw_file = open("diverged_raw.txt", 'r')

raws = [clean_line(l) for l in raw_file.readlines() if (len(clean_line(l))>0 and '+' not in l)]
print "number of points: " + str(len(raws))
print raws[0]

failed_zeros = ['// airfoil, re pairs where xfoil failed to converge by cl and step zero']
div_processed = ['\n// last points where xfoil converged']
div_early = []
processed = dict()

for line in raws:
    if line.startswith('@') or line.startswith('&'):
        #fail to zero
        literal = eval(line[1:])
        if polarname(naca=literal['airfoil'], re=literal['re']) not in polars:
            failed_zeros.append(line[1:])
    elif 'a' not in eval(line):
        failed_zeros.append(line)
    else:
        literal = eval(line)
        literal['a'] = round(literal['a'], 3)
        pair = (literal['airfoil'], literal['re'])
        if pair in processed:
            if processed[pair] < literal['a']:
                processed[pair] = literal['a']
        else:
            processed[pair] = literal['a']

for key in sorted(processed.keys()):
    if processed[key] < 5: #a < 5
        file_name = key[0] + '_Re' + str(int(round(key[1]/1000))).zfill(8)
        try:
            last = get_last_point(file_name + 'k.pol')
            if type(last) is float and last < 5:
                try:
                    aug_last = get_last_point(filename=file_name + 'k_aug1.pol')
                    if type(aug_last) is float and aug_last < 5:
                        div_early.append('{' + "'airfoil': '" + str(key[0]) + "', 're': " + str(key[1]) + ", 'a': " + str(processed[key]) + '}')
                except IOError:
                    div_early.append('{' + "'airfoil': '" + str(key[0]) + "', 're': " + str(key[1]) + ", 'a': " + str(processed[key]) + '}')
        except IOError:
            print "file " + file_name + " does not exist"
            div_early.append('{' + "'airfoil': '" + str(key[0]) + "', 're': " + str(key[1]) + ", 'a': " + str(processed[key]) + '}')
    div_processed.append('{' + "'airfoil': '" + str(key[0]) + "', 're': " + str(key[1]) + ", 'a': " + str(processed[key]) + '}')

file("failed_zeros.txt", "w").write('\n'.join(failed_zeros))
file("diverged.txt", "w").write('\n'.join(failed_zeros))
file("diverged.txt", "a").write('\n'.join(div_processed))
file("early_diverged.txt", "w").write('\n'.join(div_early))
print str(len(raws)).rjust(6) + " points sorted (including duplicates)"
print str(len(failed_zeros)).rjust(6) + " unique points written to failed_zeros.txt"
print str(len(div_early)).rjust(6) + " unique points written to early_diverged.txt"
print str(len(div_processed)).rjust(6) + " total unique points of non-convergence"
