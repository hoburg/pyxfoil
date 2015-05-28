# /usr/bin/env python

"""pyxfoil - Python XFOIL
"""

import pexpect
import re as regexp #avoid confusion with Reynold's Number
from datetime import datetime as dt
from os import remove as rm
import numpy as np

class session:
    """A python interface to an xfoil command line session.
    
    :param logfile: text to append to name of logfile.  If logfile != None, a logfile containing all xfoil input/output will be generated.  The logfile text is prepended by a date/time string.
    :type logfile: str 
    :param xfoil_start_cmd: command used to launch xfoil
    :type xfoil_start_cmd: str
    """

    def __init__(self, logfile=None, xfoil_start_cmd='xfoil'):
        if(logfile != None): #logging data to text file
            nowstr = dt.strftime(dt.now(), '%Y_%m_%d_%H%M%S')
            if(logfile != ''):
                logfile = '_' + logfile
            logfile = file('XFOILsession' + nowstr + logfile + '.txt', 'w')
        self.proc = pexpect.spawn(xfoil_start_cmd, logfile=logfile) 
        self.proc.expect('c>')
        #initializations
        self.airfoil = None
        self.re = None    
        self.bpacc = False #boolean telling whether polar accumulation is on

    def send(self, cmd, resulting_prompt='c>'):
        """Internal function used to send a command to xfoil.

        .. warning::
           This function should generally not be used except internally.
           If some functionality needs to be implemented, let us know 
           instead of simply using :py:func:`send`.

        :param cmd: the command to send, eg 'ALFA' or 'oper'
        :type cmd: str
        :param resulting_prompt: prompt we expect xfoil to display after cmd is sent
        :type resulting_prompt: str
        """

        self.proc.sendline(cmd)
        self.proc.expect(resulting_prompt)

    def current_menu(self):
        """Return the line of text before xfoil's current prompt

        :returns: str -- xfoil's current menu text, eg 'XFOIL' or '.OPERv'
        """
        newline_ind = self.proc.before.rindex('\n') 
        return self.proc.before[newline_ind:].strip()

    def force_menu(self,menu):
        """Ensure xfoil is in a certain menu.

        :param menu: The menu to force.  Currently, only 'OPER' and 'XFOIL' are implemented.
        :type menu: str
        """
        if(menu.upper() == 'XFOIL'):
            iters = 0
            while(self.current_menu() != 'XFOIL'):
                if(iters >= 10):
                    self.error('Could not get to XFOIL prompt.' +  
                               ' Current menu: ' + self.current_menu() + ';')
                self.send('')
                iters += 1
        elif((menu.upper() == 'OPER') & ('OPER' in self.current_menu())):
            pass #already in oper menu
        elif((menu.upper() == 'OPER') & ('OPER' not in self.current_menu())):
            self.force_menu('xfoil')
            self.send('oper')
            if('OPER' not in self.current_menu()):
                self.error('Could not get to OPER prompt.' + 
                           ' Current menu: ' + self.current_menu() + ';')
        else:
            self.error('Could not get to '+menu+' menu' + 
                       ' Current menu: '+self.current_menu() + ';')

    def naca(self, code):
        """Load a naca airfoil


        :param code: naca code, eg '0012'
        :type code: str

        .. note::
           The implementation requires string NACA codes as opposed to integers because python evaluates ``int(0015)`` as ``13`` due to octal conversion.

        :raises: :py:class:`XfoilError` if the NACA code is not implemented by XFOIL.
        """
        if(type(code) != str):
            raise XfoilError('NACA code must be a string.  I got: '
                             + repr(code))
        self.force_menu('xfoil')
        self.send('naca ' + code, '>')
        notimplemented = 'not implemented' in self.proc.before
        notimplemented |= 'Enter NACA' in self.proc.before
        if(notimplemented):
            raise XfoilError('NACA designation ' + code + 
                             ' not implemented by XFOIL.')
        self.airfoil = 'NACA' + code

    def load(self, filename, relpath='./'):
        """Load airfoil from file
        
        An error is raised if the load fails.

        :param filename: name of file to load, including any extension
        :type filename: str
        :param relpath: relative path to filename, eg. ``../airfoils/``
        :type relpath: str

        .. note::
           filenames with more than 1 dot '.' will cause problems.
        """
        if(type(filename) != str):
            raise XfoilError('load: filename should be a string')
        if(type(relpath) != str):
            raise XfoilError('load: relpath should be a string')
        self.force_menu('xfoil')
        self.send('load ' + relpath + filename)
        if('LOAD NOT COMPLETED' in self.proc.before):
            raise XfoilError(self.proc.before)
        self.airfoil = filename.split('.')[0]

    def save(self, relpath='./', name_ext='fine'):
        """Save airfoil coordinates to file

        :param relpath: relative path to save dir, eg. ``../airfoils/``
        :type relpath: str
        :param name_ext: the filename is a concatenation of the airfoil name and name_ext, separated by an underscore.
        :type name_ext: str
        """
        if(self.airfoil == None):
            raise XfoilError('No airfoil loaded; cannot save')
        savefile = relpath + self.airfoil
        if(savefile != ''):
            savefile += '_'
        savefile += str(name_ext) + '.dat'
        self.force_menu('xfoil')
        self.send('save ' + savefile, '[>?]')
        if('Overwrite?' in self.proc.before):
            self.send('')

    def set_re(self, re):
        """Go to viscous mode and set Reynold's Number to re

        .. note::
           re is rounded to the nearest 1000 before being sent to xfoil, since XFOIL's Re resolution when saving polar files is only 1e3.
        """
        re = round(re, -3)
        self.force_menu('oper')
        menu = self.current_menu()
        if('i' in menu):
            self.send('visc ' + str(re))
        elif('v' in menu):
            self.send('re ' + str(re))
        else:
            self.error('Unexpected menu: ' + menu)
        self.re = re

    def iter(self, n=20):
        """Set maximum number of xfoil iterations to n"""
        self.force_menu('oper')
        self.send('iter ' + str(n))

    def pacc_on(self, savefile='default', dumpfile=''):
        """Turn on polar accumulation

        :param savefile: file to write polar to.  Use 'default' to auto-name based on airfoil and Reynold's number.
        :type savefile: str
        :param dumpfile: dumpfile name as requested by XFOIL.  The empty string '' implies none.
        :type dumpfile: str
        """
        if(self.bpacc):
            self.error('PACC is already on')
        if(savefile == 'default'):
            if(self.re == None):
                self.error('Re must be set to use default polar file naming')
            savefile = self.airfoil + '_Re'
            savefile += '%08d' % (round(self.re,-3)/1000) + 'k.pol'
        if(savefile == None):
            savefile = ''
        if(dumpfile == None):
            dumpfile = ''
        self.force_menu('oper')
        self.send('pacc', 's>') #turn on polar accumulation
        self.send(savefile, 's>') #xfoil will print polar to this file
        if('Old polar save file available for appending' in self.proc.before):
            self.prnt('Polar file ' + savefile + ' exists; XFOIL will append')
        self.send(dumpfile)   #prompt returns to default after this (c>)
        self.bpacc = True
        self.polar_savefile = savefile

    def pacc_off(self, bdelete=False):
        """Turn off polar accumulation and delete internal xfoil polar.  The saved polar file is *not* deleted, unless bdelete=True.
        """
        if(not self.bpacc):
            self.error('PACC is already off')
        self.force_menu('oper')
        self.send('pacc')
        self.bpacc = False
        self.send('pdel 1') #delete internal polar
        if(bdelete):
            rm(self.polar_savefile)

    def init(self):
        """Initialize BL on next point.
    
        Useful after non-convergence or large steps in ALFA
        """
        self.force_menu('oper')
        self.send('init')

    def set_panels(self, n):
        """Set the number of airfoil panels (N in PPAR menu)"""
        if(self.airfoil == None):
            raise XfoilError('No airfoil loaded; cannot set_panels.')
        self.force_menu('xfoil')
        self.send('ppar')
        self.send('n ' + str(n))
        self.send('')
        self.send('')

    def alfa(self, a):
        """Run a single angle of attack and return output

        :param a: angle of attack (degrees)
        :type a: float
        :returns: An :py:class:`output` object
        """
        self.force_menu('oper')
        self.send('alfa ' + str(a))
        return output(self.proc.before)

    def cl(self, c):
        """Run a single CL value and return output

        :param c: lift coefficient
        :type c: float

        :returns: An :py:class:`output` object
        """
        self.force_menu('oper')
        self.send('cl ' + str(c))
        return output(self.proc.before)

    def generate_polar(self, alfa_step=0.25, maxiter=25, maxiterinit=50):
        """Create polar from zero-lift to stall

        Automatically adjusts alfa_step to encourage convergence

        :param alfa_step: suggested step size between points in polar.  This value will be altered adaptively when convergence fails.
        :type alfa_step: float
        :param maxiter: xfoil parameter - number of iterations to allow before declaring not converged (for each point in polar).  Making value too large will result in noticeably slower polar generation.
        :type maxiter: int
        :param maxiterinit: same as ``maxiter``, but for zero-lift angle initialization
        :type maxiterinit: int

        Nothing is returned, but a polar file is generated.  Text is printed to the screen when anything out of the ordinary occurs.

        .. note::
           :py:func:`generate_polar` currently supports type 1 polar generation only.  Type 1 is the standard type of lift-drag polar seen in aero texts.

        .. note::
           Use for viscous analysis only.  Airfoils do not stall in inviscid flows; hence stall detection and adaptive step-sizing are not needed.  Use ASEQ instead.
        """
        #make sure airfoil and re are set
        if(self.airfoil == None):
            self.error('Airfoil is not set.')
        if(self.re == None):
            self.error('Re is not set.')
        #try to get 0 lift angle using CL call
        self.iter(maxiterinit)
        self.pacc_on()
        for cltry in np.arange(0.0, 0.06, .01):
            out = self.cl(cltry)
            if(out.converged):
#                if(cltry > 0.0):
#                    self.prnt('Converged at CL = ' + str(cltry))
                break
            self.init()
        if(not out.converged):
            self.prnt('CL' + str(cltry) + ' did not converge')
#        self.init()
            if(out.point_added):
                self.prnt('Unconverged CL point added to polar; deleting')
                self.pacc_off(bdelete=True)
                self.pacc_on()
#            self.send('init') 
#        if(not out.converged):
#            #unable to find CL~0; try using alfa to find first CL < 0
#            #self.prnt('CL 0 fail')
#            self.pacc_off(bdelete=True)
#            for alfatry in [x*alfa_step for x in range(0,int(-5/alfa_step),-1)]:
#                out = self.alfa(alfatry)
#                if(out.converged and out.lookup('CL') <= 0.0):
#                    #self.prnt('alfa converged at a=' + str(alfatry) + ', CL='+str(out.lookup('CL')))
#                    self.pacc_on() #place first point on polar
#                    out = self.alfa(alfatry)
#                    break
#                if(not out.converged):
#                    self.prnt('alfa = '+str(alfatry) + ' failed to converge')
#                    self.send('init')
        done = not out.converged
        if(done):
            self.prnt('Failed to obtain initial convergence. Aborting.')
        else:
            #initializations for actual polar creation
            CLmax = 0.0
            LoDmax = 0.0
            alfa_last_converged = out.lookup('a')
            dalfa = alfa_step
            self.iter(maxiter)
            nbelow = 0
        while(not done):
            last_converged = out.converged #boolean - whether last run converged
            out = self.alfa(alfa_last_converged + dalfa)
            if((not out.converged) and last_converged):
            #if this is first convergence fail, try skipping
                self.send('init')
                out = self.alfa(alfa_last_converged + 2*dalfa)
                if(not out.converged):
                    self.send('init')
            if(not out.converged):
                if(out.point_added):
                    self.prnt('Not-converged point added to polar; aborting. Alfa='+str(out.lookup('a')))
                    done = True
                    continue
                if(dalfa < 0.05):
                    self.prnt('dalfa below cutoff. last converged a=' + str(alfa_last_converged) + '; cl=' + str(cl))
                    done = True
                    continue
                else:
                    dalfa *= 0.5
                    continue
            #if we get here in while loop, convergence succeeded
            if(not out.point_added):
                self.error('Point not added to polar; should have been.')
            dalfa = min(dalfa*1.2, alfa_step)
            cl = out.lookup('CL')
            cd = out.lookup('CD')
            a = out.lookup('a')
            alfa_last_converged = a
            if(cl/cd > LoDmax):
                LoDmax = cl/cd
            if(cl > CLmax):
                CLmax = cl
                nbelow = 0
            elif((cl > 0.0) & (nbelow <= 1)):
                nbelow += 1
            elif(cl > 0.0):
                done = True  #stall detected
        if(cl/cd/LoDmax > .75):
            self.prnt('stall occurred at cl/cd=' + str(cl/cd) + ', but max L/D was only ' + str(LoDmax))
        if(self.bpacc):
            self.pacc_off()
        self.send('init')

    def quit(self):
        """Stops the xfoil process associated with this session."""
        self.force_menu('xfoil')
        self.proc.sendline('quit')
        self.proc.close()

    def prnt(self, msg):
        """Like print, but prepends airfoil and Re info to the message"""
        print self.airfoil + ' @ Re=' + '%8d' % (self.re/1000) + 'k: ' + msg

    def error(self, text):
        """:raises: an :py:class:`XfoilError`, with airfoil and Re info added to the error text
        """
        errtext = text + ' Airfoil: ' + str(self.airfoil)
        errtext += '; Re = ' + str(self.re)
        raise XfoilError(errtext)

class output:
    """A class for processing and parsing xfoil output

    Instances of :py:class:`output` are obtained as return values from the :py:class:`session` methods :py:func:`alfa` and :py:func:`cl`.
    """
    def __init__(self, str):
        self.raw = str
        splitstr = '\r\n\r\n'
        last3 = []
        for i in range(0,3,1):
            parts = str.rpartition(splitstr)
            last3.append(parts[2])
            str = parts[0] 
        self.menu = last3[0].strip()
        if('rms:' in last3[1]):
            self.point_added = False
            self.data = last3[1]
        elif('Point added' in last3[1]):
            self.point_added = True
            self.data = last3[2]
            if('rms:' not in self.data):
                print self.raw
                raise XFoilError('Could not find data in output.')
        else:
            print last3
            raise XfoilError('Unexpected last3 in output.  Printed Above.')
        #we now have data in self.data
        self.converged = 'Convergence failed' not in self.data

    def __str__(self):
        return self.raw

    def converged(self):
        """:returns: bool telling whether or not xfoil converged"""
        return self.converged 

    def lookup(self, var):
        """Look up the value of a variable in xfoil's output
        
        :param var: the variable to look up.  Should be one of the following::

           - 'iter'
           - 'rms'
           - 'max'
           - 'a'
           - 'CL'
           - 'Cm'
           - 'CD'
           - 'CDf'
           - 'CDp'

        :type var: str
        :returns: float -- the value of the variable.
        :raises: :py:class:`XfoilError`, if xfoil did not converge.
        """
        if(not self.converged):
            raise XFoilError('Attempt to look up '+var+' on unconverged output')
        if(var == 'iter'):
            return int(regexp.search(' *\d+ ', self.data).group())
        else:
            res = regexp.search(var+' ?[=:] +-?\d*[.]\d*E?-?\d*', self.data).group()
            return float(res.split(' ')[-1])

class XfoilError(Exception):
    """An exception raised by pyxfoil"""
    def __init__(self, value): #, arf='Unknown', re='Unknown'):
        self.text = value
#        self.arf = arf
#        self.re = re
    def __str__(self):
        return self.text# + ' Airfoil: ' + str(self.arf) + '; Re = ' + str(self.re)

def nacacode4(tau, maxthickpt, camb):
    """Converts airfoil parameters to 4-digit naca code

    :param tau: maximum thickness as percent of chord
    :type tau: float
    :param maxthickpt: Location of maximum thickness as percent of chord
    :type maxthickpt: float
    :param camb: max camber as a percentage of chord
    :type camb: float

    :returns: string 4 digit naca code
    .. note::
       Non-integer values will be rounded to the nearest percent.  maxthick is rounded to the nearest tens of percent.
    """
    nc = round(tau)
    if(camb > 0):
        nc += 100*round(maxthickpt, -1)/10
    nc += 1000*round(camb)
    return '%04d' % int(nc)

