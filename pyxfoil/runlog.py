import datetime

def getnowstr():
    now = datetime.datetime.now()
    return str(now.month) + '/' + str(now.day) + '/' + str(now.year) + '-' + str(now.hour).zfill(2) + ':' + str(now.minute).zfill(2) + ':' + str(now.second).zfill(2)

class runlog():
    def __init__(self, logfile):
        self.logfile = logfile
        self.logfile.write('#'*50 + '\n')
        self.logfile.write('Log opened ' + getnowstr() + '\n')
        self.logfile.write('-'*50 + '\nComments\n\n')
        self.airfoils = []
        self.res = []
        self.fills = dict()

    def comment(self, line):
        now = datetime.datetime.now()
        nowstr = str(now.hour).zfill(2) + ':' + str(now.minute).zfill(2) + ':' + str(now.second).zfill(2)
        self.logfile.write(nowstr + '> ' + line + '\n')

    def timeout(self, airfoil, re):
        self.comment("XFOIL timed out at airfoil=" + str(airfoil) + " Re=" + str(re))

    def sweep_param(self, airfoils=[], res=[]):
        self.airfoils += airfoils
        self.res += res
        self.airfoils = list(sorted(set(self.airfoils)))
        self.res = list(sorted(set(self.res)))

    def fill_param(self, fills):
        for entry in fills:
            if entry['airfoil'] not in self.fills:
                self.fills[entry['airfoil']] = []
            self.fills[entry['airfoil']].append(entry['re'])

    def close(self):
        s = '\n' + '-'*50 + '\nSession swept through:\n'
        s += '\nAirfoils:\n'
        try:
            prefix = self.airfoils[0][:2]
            for a in self.airfoils:
                if a[:2] != prefix:
                    s += '\n'
                    prefix = a[:2]
                s += a.rjust(5)
            s += '\n'
        except IndexError:
            pass

        self.logfile.write(s)

        s = '\nReynolds Numbers:\n'
        maxdigits = 9
        try:
            currentdigits = len(str(self.res[0]))
            if len(self.res) > 0:
                maxdigits = len(str(max(self.res)))
            for r in self.res:
                if len(str(r)) != currentdigits:
                    s += '\n'
                    currentdigits = len(str(r))
                s += str(r).rjust(maxdigits + 1)
            s += '\n'
        except IndexError:
            pass

        self.logfile.write(s)

        s = '\n' + '-'*50 + '\nSession filled in:\n'
        for airfoil in sorted(self.fills.keys()):
            s += '\n Airfoil: ' + airfoil + '\n'
            currentdigits = len(str(self.fills[airfoil][0]))
            if len(self.res) > 0:
                maxdigits = len(str(max(self.res)))
            for re in self.fills[airfoil]:
                if len(str(re)) != currentdigits:
                    s += '\n'
                    currentdigits = len(str(re))
                s += str(re).rjust(maxdigits +1)
            s += '\n'

        self.logfile.write(s)

        self.logfile.write('\n' + '-'*50 + '\nLog closed at ' + getnowstr() + '\n')
        self.logfile.close()

#import numpy
#Nacas = [a + str(b).zfill(2) for a in ['00','14','24','34','44'] for b in range(8,17)]
#Res = [1000*int(r/1000) for r in numpy.logspace(4,8,41)]
#Fills = [{'airfoil': naca, 're': re} for naca in Nacas for re in Res]
#
#f = file('dummy.txt', 'w')
#
#a = runlog(f)
#a.sweep_param(Nacas, Res)
#
#a.fill_param(Fills)
#
#a.close()
#
