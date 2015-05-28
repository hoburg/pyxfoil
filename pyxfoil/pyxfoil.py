import pexpect 
import os
import re as regexp
import StringIO
from datetime import datetime as dt
from decimal import *

class session:
    """ DO NOT CHANGE ORDER """
    varlist = ['iter', 'rms', 'max', 'a', 'CL', 'Cm', 'CD', 'CDf', 'CDp']

    def __init__(self, logfile=None,
                 div_filename='diverged_raw.txt',
                 xfoil_start_cmd='xfoil', 
                 output_dir='./savedpolars/',
                 airfoil=None,
                 re=None,
                 plots=False,
                 force_zero=False):

        self.airfoil= None
        self.re = None
        self.iters = 20
        self.bpacc = False
        self.plots = plots
        self.force_zero = force_zero
        self.cwd = os.getcwd()
        self.logs_on = False

        try: #make ./savedpolars/
            os.chdir(output_dir)
            self.output_dir = os.getcwd()
        except OSError:
            self.error("Invalid directory " + output_dir)

        if(logfile != None): #logging data to text file
            self.logs_on = True
            self.logdir = self.cwd + '/logs/'
            nowstr = dt.strftime(dt.now(), '%Y_%m_%d_%H%M%S')
            if(logfile != ''):
                logfile = '_' + logfile
            logfile = file(self.logdir + 'XFOILsession' + nowstr + logfile + '.txt', 'w')
            self.divfile = file(self.logdir + div_filename, 'a')
        self.proc = pexpect.spawn(xfoil_start_cmd, logfile=logfile) 
        self.proc.expect('c>')

        if not self.plots:
            self.send("PLOP")
            self.send("G")

        if airfoil:
            self.naca(airfoil)
            if re:
                self.set_re(re)

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
        menu = menu.upper()

        if menu == "XFOIL":
            for _ in range(11):
                if self.current_menu() == menu:
                    break
                self.send("")
        elif "OPER" in menu:
            if 'OPER' not in self.current_menu():
                self.force_menu("XFOIL")
                self.send("OPER")
        else:
            self.error('Could not get to '+menu+' menu' + 
                       ' Current menu: '+self.current_menu() + ';')

    def plots_off(self):
        if self.plots:
            menu = self.current_menu()
            if menu != "XFOIL":
                self.force_menu("XFOIL")
            self.send("PLOP")
            self.send("G")
            self.plots = False
            self.force_menu(menu)

    def plots_on(self):
        if not self.plots:
            self.plots = True
            self.plots_off()
            self.plots = True

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
        re = round(float(re), -3)
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
        self.iters = n

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
            print 'Polar file ' + savefile + ' exists; XFOIL will append'
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
            os.remove(self.polar_savefile)

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

    def alfa(self, a, retry=0):
        """Run a single angle of attack and return output

        :param a: angle of attack (degrees)
        :type a: float
        :returns: An :py:class:`output` object
        """
        self.force_menu('oper')
        self.send('alfa ' + str(a))

        for count in range(retry + 1):
            out = output(self.proc.before)
            if out.converged:
                if count > 0:
                    print "a = " + str(a) + " converged after " + str(count) + " tries"
                break
            #if "to continue iterating" in self.proc.before:
                #self.send("!")

        return out

    def cl(self, c):
        """Run a single CL value and return output

        :param c: lift coefficient
        :type c: float

        :returns: An :py:class:`output` object
        """
        self.force_menu('oper')
        self.send('cl ' + str(c))
        return output(self.proc.before)

    def error(self, text):
        """:raises: an :py:class:`XfoilError`, with airfoil and Re info added to the error text
        """
        errtext = text + ' Airfoil: ' + str(self.airfoil)
        errtext += '; Re = ' + str(self.re)
        raise XfoilError(errtext)

    def zero_cl(self, tries=10):
        """Attempt to find angle of zero lift
        """
        epsilon = 0
        angle = self.cl(epsilon)
        for _ in range(tries):
            if angle.converged:
                break
            epsilon += .01
            angle = self.cl(epsilon)
            #if angle.lookup('CD') > 100:
            #    self.init()
        
        if not angle.converged:
            self.error("Could not zero CL")
        return angle.lookup('a')

    def step_zero(self, step_size=.25, tries=20):
        angle = 0
        self.init()
        output = self.alfa(angle)
        for _ in range(tries):
            if output.converged:
                if output.lookup('CL') < 0:
                    break
            else:
                self.init()
            angle -= step_size
            output = self.alfa(angle)
        if output.converged and output.lookup('CL') < 0:
            return output.lookup('a')
        return self.error("Could not zero CL")

    def make_file(self, naca=None, reynolds=None):
        """
        Makes a pseudo polar
        """

        if type(naca) != str:
            naca = self.airfoil
        if type(reynolds) != str:
            reynolds = self.re

        polarname = naca + '_Re' + Decimal(reynolds/1000).to_eng_string().zfill(8) + 'k.pol'
        print polarname
        return open(polarname, 'w')        

    def parse(self, output):
        """
        Seeks and obtains polar data from output object
        Returns a string form of dictionary of form (var: value)
        """
        data = dict()
        for var in self.varlist:
            data[var] = output.lookup(var)

        return str(data)

    def generate_polar(self, alfa_step=.5, min_alfa=4, min_cl=0.4, filename='default', writefile=True, start_value=None):
        """
        1. set airfoil, reynolds number
        2. obtain zero for cl
        3. run alfas from zero to stall
        4. write .pol
        """

        os.chdir(self.output_dir)
        print "***\nAirfoil = " + self.airfoil + " Re = " + str(self.re)

        if start_value == None:
            try:
                #attemp to zero by calling cl with small values
                angle = self.zero_cl()
                print "CL successfully zeroed: a = " + str(angle)
            except XfoilError:
                if self.force_zero:
                    #step angle backwards until cl goes negative
        	    try:
                        angle = self.step_zero(step_size=.2, tries=35)
                    except XfoilError:
                        print "CL step-zeroing failed, recording failure and aborting."
                        if self.logs_on:
                            self.divfile.write('\n&' + str({'airfoil':self.airfoil, 're':self.re}))
                        return None 
                    print "CL step-zeroed to: a = " +  str(angle) + " by stepping back from a=0"
                else:
                    print "CL zeroing failed, recording faiure and aborting."
                    if self.logs_on:
                        self.divfile.write('\n@' + str({'airfoil':self.airfoil, 're':self.re}))
                    return None
        else:
            angle = start_value
            print "Beginning simulation at a = " + str(angle)

        if writefile and not self.bpacc:
            self.pacc_on(savefile=filename)
        if not writefile and self.bpacc:
            self.pacc_off()

        cl_max_angle = 90 
        cl_max = -100
        cl_peaked = False
        last_converged = angle
        last_cl = -100
        skips = 0

        while True:
            current_output = self.alfa(angle)
            if current_output.converged:
                skips = 0
                #update cl_max_angle
                last_converged = angle
                last_cl = current_output.lookup('CL')
            
                if writefile and not current_output.point_added:
                    if self.logs_on:
                        self.divfile.write('\n+' + str({'airfoil':self.airfoil, 're':self.re, 'a':angle}))
                    print "failed to record to polar: a = " + str(angle)
                    angle += alfa_step
                    continue

                if last_cl > cl_max:
                    cl_max = last_cl
                    cl_max_angle = angle
                elif (last_cl > min_cl or angle > min_alfa) and last_cl < cl_max - .05:
                    print "aborting at cl = " + str(last_cl) + ", a = " + str(angle) + ": past peak " + str(cl_max) + ", " + str(cl_max_angle)
                    break
                elif (last_cl > min_cl or angle > min_alfa) and angle > 1 + cl_max_angle:
                    print "aborting at cl = " + str(last_cl) + ", a = " + str(angle) + ": past peak " + str(cl_max) + ", " + str(cl_max_angle)
                    break

            else:
                if writefile and current_output.point_added:
                    #point written but not converged
                    self.pacc_off(bdelete=True)
                    self.pacc_on(savefile=filename)

                if last_cl < cl_max and (last_cl > min_cl or angle > min_alfa):
                    #passed minimum alfa or cl and dipped lower in cl indicates stall
                    print "aborting at a = " + str(angle) + ": failed to converge after peaking"
                    break

                elif (last_cl > min_cl or angle > min_alfa):
                    if skips < 2: #skips measures skipping after passing minimum alfa or cl
                        if self.logs_on:
                            self.divfile.write('\n' + str({'airfoil':self.airfoil, 're':self.re, 'a': angle}))
                        skips += 1
                        print "skipping a = " + str(angle) + ": skips so far: " + str(skips)
                    else:
                        print "Aborting at a = " + str(last_converged) + ": failed to converge after two skips"
                        break

                else:
                    print "skipping a = " + str(angle) + ": failed to converge"
                    self.divfile.write('\n' + str({'airfoil':self.airfoil, 're':self.re, 'a': angle}))

            angle += alfa_step
        
        print "Exiting simulation at a = " + str(last_converged)
        if self.bpacc:
            self.pacc_off()
        self.init()
             
    def quit(self):
        """Stops the xfoil process associated with this session."""
        self.force_menu('xfoil')
        self.proc.sendline('quit')
        self.proc.close() 
        os.chdir(self.cwd)
        if self.logs_on:
            self.divfile.close()

    def force_quit(self):
        """Force closes the session without sending quit command"""
        self.proc.close()
        os.chdir(self.cwd)
        if self.logs_on:
            self.divfile.close()
 
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
                raise XfoilError('Could not find data in output.')
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
        #if(not self.converged):
        #    raise XfoilError('Attempt to look up '+var+' on unconverged output')
        if(var == 'iter'):
            return int(regexp.search(' *\d+ ', self.data).group())
        else:
            res = regexp.search(var+' ?[=:] +-?\d*[.]\d*E?-?\d*', self.data).group()
            return float(res.split(' ')[-1])

class XfoilError(Exception):
    """An exception raised by pyxfoil"""
    def __init__(self, value): #, arf='Unknown', re='Unknown'):
        self.text = value

    def __str__(self):
        return self.text

