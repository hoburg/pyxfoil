#! /usr/bin/env python

import pyxfoil as px
import numpy as np

xf = px.session(logfile='sweeptest')
Res = np.logspace(5,7,21)
#Res = np.logspace(4.5,5,5)
nacacodes = range(8,17,1)
adders = [0, 2400]
xf.naca('0010')
xf.set_panels(200)
for a in adders:
    for nacacode in nacacodes:
        xf.naca('%04d' % (nacacode + a))
        for re in Res:
            xf.set_re(re)
            xf.generate_polar()
xf.quit()


#s = px.session()
#s.naca(2416)
#s.set_panels(200)
#s.set_re(32000)
#s.generate_polar()
#s.quit()

#import numpy as np
#
#xf = px.session(blog=True)
#xf.naca(2412) #needed to set panels in next line
#xf.set_panels(200)
#Res = [32000, 56000]
##Res = np.logspace(4.5,7,21)
#nacacodes = range(8,17,1)
##nacacodes = [11]
##nacacodes = [x + 2400 for x in nacacodes]
##nacacodes = [15]
#adders = [0, 1400, 2400, 3400, 4400]
#for a in adders:
#    for nacacode in nacacodes:
#        xf.naca(nacacode + a)
#        for re in Res:
#            xf.set_re(re)
#            xf.generate_polar(alfa_step=0.2)
#xf.quit()


