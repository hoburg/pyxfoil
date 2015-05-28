import sys, os
from decimal import *
import pexpect, time, shutil, code, numpy

########################################
# Initiation block                     # 
########################################
package_files = ['pyxfoil', 'sorter', 'div_sort', '__init__', 'runlog', 'plotter']

input_args = sys.argv[1:]
homedir = os.getcwd() + '/'

if len(input_args) == 0:
    print "No directory specified:"
    run_dir = raw_input("Enter a run directory >> " ).rstrip('/')
else:
    run_dir = input_args[0].rstrip('/')

try:
    os.chdir(run_dir)
    cwd = os.getcwd() + '/'
    runlogfile = file(cwd + 'logs/sessionlog.txt', 'a')
    print "Existing run loaded: " + run_dir
except OSError:
    try:
        os.mkdir(run_dir)
        os.chdir(run_dir)
        os.mkdir('src')
        os.mkdir('logs')
        os.mkdir('mergedump')
        os.mkdir('savedpolars')
        cwd = os.getcwd() + '/'
        for filename in package_files:
            shutil.copyfile(homedir + 'pyxfoil/' + filename + '.py', 
                            cwd + 'src/' + filename + '.py')
        runlogfile = file(cwd + 'logs/sessionlog.txt', 'w')
        print "New run created: " + run_dir

    except OSError:
        print "Fatal error: directory " + run_dir + " not found and could not be created."
        sys.exit(0)
finally:
    sys.path.append(cwd)
    from src import pyxfoil, sorter, runlog, plotter
    sessionlog = runlog.runlog(runlogfile)

########################################
# Function definitions                 #
########################################

def get_existing(dir='savedpolars'):
    """
    Looks through output directory for polars already created
    Returns a list of existing polars
    """
    existing_polars = dict()
    try: #check for complete polars
        os.chdir(cwd + dir)
        existing_polars = [p for p in os.listdir(os.getcwd()) if '.pol' in p]
        os.chdir(cwd)
    except OSError:
        pass
    return existing_polars

def sweep(airfoils, res, min_alfa=4, write_file=True, plots_on=False, panels=200):
    """
    Runs a large sweep over airfoil and re range

    @param airfoils   iterable of NACA numbers to sweep over
    @param res        iterable reynolds numbers to sweep over
    @param write_file boolean indicating whether or not to create polars
    @param plots_on   boolean indicating whether or not to simulate with plots on
    @param panels     included as per original genpolar file
    """
    os.chdir(cwd)

    sessionlog.comment("Beginning sweep with minimum alfa of " + str(min_alfa))
    xf = pyxfoil.session(logfile='sweep', plots=plots_on, force_zero=True)
    xf.naca('0010')
    xf.set_panels(panels)
    timeouts = 0

    start_time = time.time()
    last_time = start_time
    airfoils, res = list(airfoils), list(res)    
    for naca in airfoils:
        xf.naca(naca)
        for re in res:
            percentage = 100*round((airfoils.index(naca)*len(res)+res.index(re)+1.)/(len(airfoils)*len(res)), 5)
            polarname = "NACA" + naca + "_Re" + str(int(round(re/1000))).zfill(8) + "k.pol"
            if polarname in get_existing():
                print "NACA " + naca + " Re " + (str(int(re/1000)) + 'k').rjust(8) + " has already been run: skipping (" + str(percentage) + "%)"
                continue
    
            xf.set_re(re)
            try:
                xf.generate_polar(filename=polarname, min_alfa=min_alfa, writefile=write_file)
                sessionlog.comment("NACA " + naca + ", re=" + str(re) + " simulation complete.")
                this_time = time.time()
                print str(percentage) + "% complete, " + str(round(this_time-last_time, 3)) + " seconds"
                last_time = this_time
            except pexpect.TIMEOUT:
                xf.force_quit()
                print "XFOIL timed out at NACA=" + naca + " Re=" + str(re)
                sessionlog.timeout(naca, re)
                timeouts += 1
                print "Attempting to restarting at current set."
                xf = pyxfoil.session(airfoil=naca, re=re, logfile='sweep', plots=plots_on, force_zero=True)
                try:
                    xf.generate_polar(filename=polarname, min_alfa=min_alfa, writefile=write_file)
                    sessionlog.comment("NACA " + naca + ", Re=" + str(re) + " recovered on second try.")
                    this_time = time.time()
                    print str(percentage) + "% complete, " + str(round(this_time-last_time, 3)) + " seconds"
                    last_time = this_time
                except pexpect.TIMEOUT:
                    xf.force_quit()
                    sessionlog.comment("NACA " + naca + ", Re=" + str(re) + " failed to recover on second try.  Continuing at next set.")
                    print "NACA " + naca + ", Re=" + str(re) + " failed to recover on second try.  Continuing at next set."
                    xf = pyxfoil.session(logfile='sweep', plots=plots_on, force_zero=True, airfoil=naca)

    xf.quit()
    total_seconds = time.time()-start_time
    average_time = round(total_seconds/(len(res)*len(airfoils)), 3)
    m, s = divmod(total_seconds, 60)
    h, m = divmod(m, 60)
        
    timeout_count = "Number of xfoil timeouts: " + str(timeouts)
    completion_time = "Time to complete: " + str(h) + " hours " + str(m) + " minutes " + str(round(s, 3)) + " seconds."
    simulation_count = "Number of simulations: " + str(len(airfoils) * len(res))
    average_time = "Average simulation length: " + str(average_time) + ' seconds.'
    sessionlog.comment(timeout_count)
    sessionlog.comment(completion_time)
    sessionlog.comment(simulation_count)
    sessionlog.comment(average_time)
    sessionlog.sweep_param(airfoils, res)

    print timeout_count + '\n' + completion_time + '\n' + simulation_count + '\n' + average_time
    os.chdir(cwd)

def fill(threshold=4.0, stepsize=0.25, write_file=True, plots_on=False, panels=200):
    """
    Sifts through existing polars and reruns simulations with smaller step size
    This should be run after sweep()

    @param threshold  float minimum alfa value to be included in fill()
    @param stepsize   float alfa step size to simulate with
    @param write_file boolean indicating whether polar is created
    @param plots_on   boolean indicating whether plots are shown
    @param panels     included as per original genpolar file
    """
    os.chdir(cwd)
    sessionlog.comment("Beginning fill with threshold " + str(threshold))

    fillable = get_early_div(threshold)
    if len(fillable) == 0:
        print "Nothing to fill."
        return None

    xf = pyxfoil.session(div_filename='aug.txt', logfile='fill', plots=plots_on, force_zero=True)
    xf.naca('0010')
    xf.set_panels(panels)
    timeouts = 0

    start_time = time.time()
    last_time = start_time
 
    for early in fillable:
        xf.naca(early['airfoil'])
        xf.set_re(early['re'])
        percentage = 100*(list(fillable).index(early)+1.)/len(fillable)
        polarname = "NACA" + early['airfoil'] + "_Re" + str(int(round(early['re']/1000))).zfill(8) + "k_aug1.pol"
        if polarname in get_existing():
            print "NACA " + early['airfoil'] + " Re " + (str(int(early['re']/1000)) + 'k').rjust(8) + " has already been run: skipping (" + str(percentage) + "%)"
            continue
        try:
            xf.generate_polar(filename=polarname, writefile=write_file, min_alfa=threshold, start_value=early['a'] + stepsize, alfa_step=stepsize)
            sessionlog.comment("NACA " + early['airfoil'] + ", re=" + str(early['re']) + " simulation complete.")
            this_time = time.time()
            print str(percentage) + "% complete, " + str(round(this_time-last_time, 3)) + " seconds"
            last_time = this_time
        except pexpect.TIMEOUT:
            xf.force_quit()
            print "XFOIL timed out at NACA=" + early['airfoil'] + " Re=" + str(early['re'])
            sessionlog.timeout(early['airfoil'], early['re'])
            timeouts += 1
            print "Restarting at next set."
            xf = pyxfoil.session(div_filename='aug.txt', logfile='fill', plots=plots_on, force_zero=True)
    
    xf.quit()
    total_seconds = time.time()-start_time
    average_time = round(total_seconds/len(fillable), 3)
    m, s = divmod(total_seconds, 60)
    h, m = divmod(m, 60)
        
    timeout_count = "Number of xfoil timeouts: " + str(timeouts)
    completion_time = "Time to complete: " + str(h) + " hours " + str(m) + " minutes " + str(round(s, 3)) + " seconds."
    simulation_count = "Number of simulations: " + str(len(fillable))
    average_time = "Average simulation length: " + str(average_time) + ' seconds.'
    sessionlog.comment(timeout_count)
    sessionlog.comment(completion_time)
    sessionlog.comment(simulation_count)
    sessionlog.comment(average_time)
    sessionlog.fill_param(fillable)

    print timeout_count + '\n' + completion_time + '\n' + simulation_count + '\n' + average_time
    merge()
    plotter.histogram(filename='histogram', threshold=threshold)
    os.chdir(cwd)

def get_early_div(threshold=5.0):
    """
    Extracts polars which end at alfa lower than threshold
    Returns a list of dictionaries
    """
    os.chdir(cwd)
    earlies = list(filter(sorter.cutoff_generator(threshold), sorter.dict_to_list(sorter.dir_to_dict(cwd + 'savedpolars'))))
    os.chdir(cwd)
    return earlies

def interleave(lst1, lst2):
    """
    Helper function for merge().  Merges two lists of comparable items together in increasing order.
    Returns a the merged list of lst1 and lst2 in sorted ascending order.

    @param lst1, lst2 lists to merge together
    """
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

def merge():
    """
    Merges .pol files with _aug.pol files
    Dumps the original files in cwd/mergedump/
    New merged files with more complete alfas replace old ones in cwd/savedpolars/
    """
    os.chdir(cwd + 'savedpolars')
    augfiles = [f for f in os.listdir(os.getcwd()) if 'aug' in f]
    files_merged = 0
    for aug in augfiles:
        polar_header = file(aug, 'r').readlines()[:12]
        polar_original = file(aug[:20] + '.pol', 'r').readlines()
        polar_augment = file(aug, 'r').readlines()
        try:
            shutil.move(aug[:20] + '.pol', cwd + 'mergedump')
            shutil.move(aug, cwd + 'mergedump')
        except shutil.Error:
            os.remove(cwd + 'mergedump/' + aug[:20] + '.pol')
            os.remove(cwd + 'mergedump/' + aug)
            shutil.move(aug[:20] + '.pol', cwd + 'mergedump')
            shutil.move(aug, cwd + 'mergedump')
        file(aug[:20] + '.pol', 'w').write(''.join(l for l in polar_header) + interleave(polar_original[12:], polar_augment[12:]))
        files_merged += 1
    sessionlog.comment(str(files_merged) + " files merged with their filler files.")
    print str(files_merged) + " files merged with their filler files."
    os.chdir(cwd)
     
########################################
# Runtime code                         #
########################################

Nacas = [a + str(b).zfill(2) for a in ['00','14','24','34','44'] for b in range(8,17)]
Res = [1000*int(r/1000) for r in numpy.logspace(4,8,41)]

smallnacas = Nacas[12:13]
smallres = Res[20:24]
smallnacas2 = Nacas[15:16]
smallres2 = Res[8:12]

inputline = raw_input("Genpolar >> ")
while (inputline.lower() != "quit"):
    try:
        compiled = code.compile_command(inputline, "<stdin>", "exec") 
        if compiled:
            exec(compiled)
    except Exception as e:
        print e
        print "Invalid command: " + inputline + " try again."

    inputline = raw_input("Genpolar >> ")

sessionlog.close()
os.chdir(homedir)
