'''
The Comets module serves as a Python user interface to COMETS.
For more information see https://segrelab.github.io/comets-manual/
'''

import re
import subprocess as sp
import pandas as pd
import os
import numpy as np
from cometspy import layout
from cometspy import params

__author__ = "Djordje Bajic, Jean Vila, Jeremy Chacon"
__copyright__ = "Copyright 2019, The COMETS Consortium"
__credits__ = ["Djordje Bajic", "Jean Vila", "Jeremy Chacon"]
__license__ = "MIT"
__version__ = "0.3.0"
__maintainer__ = "Djordje Bajic"
__email__ = "djordje.bajic@yale.edu"
__status__ = "Beta"


class CorruptLine(Exception):
    pass


class OutOfGrid(Exception):
    pass


class UnallocatedMetabolite(Exception):
    pass


def isfloat(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


def read_file(filename):
    f = open(filename, 'r')
    f_lines = f.read()
    f.close()
    return f_lines


def readlines_file(filename):
    f = open(filename, 'r')
    f_lines = f.readlines()
    f.close()
    return f_lines


def chemostat(models, reservoir_media, dilution_rate):
    """ Builds typical layout and parameters for a chemostat simulation

    Returns a layout object and a parameters object with the given
    models, reservoir_media, and dilution_rate in a chemostat-like
    experiment. The layout and parameters can be then further modified
    to adress specific needs.

    Args:
      models:  a list of comets models, with initial_pop pre-assigned
      reservoir_media: a dictionary where keys are extracellular
        metabolite names and the values are their concentration in the media
      dilution_rate: a float between zero and 1 specifying the per-hour
        dilution rate

    Returns:
      layout
      parameters

    """
    mylayout = layout(models)

    for key, value in reservoir_media.items():
        mylayout.set_specific_metabolite(key, value)
        mylayout.set_specific_refresh(key, value * dilution_rate)

    parameters = params()
    parameters.all_params['metaboliteDilutionRate'] = dilution_rate
    parameters.all_params['deathRate'] = dilution_rate

    return(mylayout, parameters)


class comets:
    '''
    This class sets up an environment with all necessary for
    a comets simulation to run, runs the simulation, and stores the output
    data from it.
    '''
    def __init__(self, layout, parameters, working_dir=''):

        # define instance variables
        self.working_dir = os.getcwd() + '/' + working_dir
        self.GUROBI_HOME = os.environ['GUROBI_HOME']
        self.COMETS_HOME = os.environ['COMETS_HOME']

        self.VERSION = 'comets_evo'

        # set default classpaths, which users may change
        self.build_default_classpath_pieces()
        self.build_and_set_classpath()
        self.test_classpath_pieces()

        # check to see if user has the libraries where expected

        self.layout = layout
        self.parameters = parameters

        # dealing with output files
        self.parameters.all_params['useLogNameTimeStamp'] = False
        self.parameters.all_params['TotalBiomassLogName'] = (
            'total_biomass_log_' + hex(id(self)))
        self.parameters.all_params['BiomassLogName'] = (
            'biomass_log_' + hex(id(self)))
        self.parameters.all_params['FluxLogName'] = (
            'flux_log_' + hex(id(self)))
        self.parameters.all_params['MediaLogName'] = (
            'media_log_' + hex(id(self)))

    def build_default_classpath_pieces(self):
        self.classpath_pieces = {}
        self.classpath_pieces['gurobi'] = (self.GUROBI_HOME +
                                           '/gurobi.jar')
        self.classpath_pieces['junit'] = (self.COMETS_HOME +
                                          '/lib/junit/junit-4.12.jar')
        self.classpath_pieces['hamcrest'] = (self.COMETS_HOME +
                                             '/lib/junit/hamcrest-core-1.3.jar')
        self.classpath_pieces['jogl_all'] = (self.COMETS_HOME +
                                             '/lib/jogl/jogamp-all-' +
                                             'platforms/jar/jogl-all.jar')
        self.classpath_pieces['gluegen_rt'] = (self.COMETS_HOME +
                                               '/lib/jogl/jogamp-all-' +
                                               'platforms/jar/gluegen-rt.jar')
        self.classpath_pieces['gluegen'] = (self.COMETS_HOME +
                                            '/lib/jogl/jogamp-all-' +
                                            'platforms/jar/gluegen.jar')
        self.classpath_pieces['gluegen_rt_natives'] = (self.COMETS_HOME +
                                                       '/lib/jogl/jogamp-' +
                                                       'all-platforms/jar/' +
                                                       'gluegen-rt-natives-' +
                                                       'linux-amd64.jar')
        self.classpath_pieces['jogl_all_natives'] = (self.COMETS_HOME +
                                                     '/lib/jogl/' +
                                                     'jogamp-all-platforms/' +
                                                     'jar/jogl-all-natives-' +
                                                     'linux-amd64.jar')
        self.classpath_pieces['jmatio'] = (self.COMETS_HOME +
                                           '/lib/JMatIO/lib/jamtio.jar')
        self.classpath_pieces['jmat'] = (self.COMETS_HOME +
                                         '/lib/JMatIO/JMatIO-041212/' +
                                         'lib/jmatio.jar')
        self.classpath_pieces['concurrent'] = (self.COMETS_HOME +
                                               '/lib/colt/lib/concurrent.jar')
        self.classpath_pieces['colt'] = (self.COMETS_HOME +
                                         '/lib/colt/lib/colt.jar')
        self.classpath_pieces['lang3'] = (self.COMETS_HOME +
                                          '/lib/commons-lang3-3.7/' +
                                          'commons-lang3-3.7.jar')
        self.classpath_pieces['math3'] = (self.COMETS_HOME +
                                          '/lib/commons-math3-3.6.1/' +
                                          'commons-math3-3.6.1.jar')
        self.classpath_pieces['bin'] = (self.COMETS_HOME +
                                        '/bin/' + self.VERSION + '.jar')

    def build_and_set_classpath(self):
        ''' builds the JAVA_CLASSPATH from the pieces currently in
        self.classpath_pieces '''
        paths = list(self.classpath_pieces.values())
        classpath = ':'.join(paths)
        self.JAVA_CLASSPATH = classpath

    def test_classpath_pieces(self):
        ''' checks to see if there is a file at each location in classpath
        pieces. If not, warns the user that comets will not work without the
        libraries. Tells the user to either edit those pieces (if in linux)
        or just set the classpath directly'''
        broken_pieces = self.get_broken_classpath_pieces()
        if len(broken_pieces) == 0:
            pass  # yay! class files are where we hoped
        else:
            print('Warning: java class libraries cannot be found')
            print('These are the expected locations for dependencies:')

            print('Dependency \t\t\t expected path')
            print('__________ \t\t\t _____________')
            for key, value in broken_pieces.items():
                print('{}\t\t\t{}'.format(key, value))
            print('\n  You have two options to fix this problem:')
            print('1.  set each class path correctly by doing:')
            print('    comets.set_classpath(libraryname, path)')
            print('    e.g.   comets.set_classpath(\'hamcrest\', ' +
                  '\'/home/chaco001/comets/junit/hamcrest-core-1.3.' +
                  'jar\')\n')
            print('    note that versions dont always have to ' +
                  'exactly match, but you\'re on your own if they ' +
                  'don\'t\n')
            print('2.  fully define the classpath yourself by ' +
                  'overwriting comets.JAVA_CLASSPATH')
            print('       look at the current comets.JAVA_CLASSPATH ' +
                  'to see how this should look.')

    def get_broken_classpath_pieces(self):
        ''' checks to see if there is a file at each location in classpath
        pieces. Saves the pieces where there is no file and returns them as a
        dictionary, where the key is the common name of the class library and
        the value is the path '''  #
        broken_pieces = {}         #
        for key, value in self.classpath_pieces.items():
            if not os.path.isfile(value):  #
                broken_pieces[key] = value
        return(broken_pieces)

    def set_classpath(self, libraryname, path):
        ''' tells comets where to find required java libraries
        e.g. comets.set_classpath(\'hamcrest\', \'/home/chaco001/
        comets/junit/hamcrest-core-1.3.jar\')
        Then re-builds the path'''
        self.classpath_pieces[libraryname] = path
        self.build_and_set_classpath()

    def run(self, delete_files=True):
        print('\nRunning COMETS simulation ...')

        # If evolution is true, write the biomass but not the total biomass log
        if self.parameters.all_params['evolution']:
            self.parameters.all_params['writeTotalBiomassLog'] = False
            self.parameters.all_params['writeBiomassLog'] = True

        # write the files for comets in working_dir
        c_global = self.working_dir + '.current_global'
        c_package = self.working_dir + '.current_package'
        c_script = self.working_dir + '.current_script'

        self.layout.write_necessary_files(self.working_dir)
        # self.layout.write_layout(self.working_dir + '.current_layout')
        self.parameters.write_params(c_global, c_package)

        if os.path.isfile(c_script):
            os.remove(c_script)
        with open(c_script, 'a') as f:
            f.write('load_comets_parameters ' + c_global + '\n')
            f.writelines('load_package_parameters ' + c_package + '\n')
            f.writelines('load_layout ' + self.working_dir +
                         '.current_layout')

        # simulate
        self.cmd = ('java -classpath ' + self.JAVA_CLASSPATH +
                    # ' -Djava.library.path=' + self.D_JAVA_LIB_PATH +
                    ' edu.bu.segrelab.comets.Comets -loader' +
                    ' edu.bu.segrelab.comets.fba.FBACometsLoader' +
                    ' -script ' + c_script)

        p = sp.Popen(self.cmd, shell=True, stdout=sp.PIPE, stderr=sp.STDOUT)

        self.run_output, self.run_errors = p.communicate()
        self.run_output = self.run_output.decode()

        if self.run_errors is not None:
            self.run_errors = self.run_errors.decode()
        else:
            self.run_errors = "STDERR empty."

        # Give warning if simulation had nonzero exit
        if ('Error' in self.run_output):
            print(self.run_output)
        else:
            
            # '''----------- READ OUTPUT ---------------------------------------'''
            # Read total biomass output
            if self.parameters.all_params['writeTotalBiomassLog']:
                tbmf = readlines_file(
                    self.parameters.all_params['TotalBiomassLogName'])
                self.total_biomass = pd.DataFrame([re.split(r'\t+', x.strip())
                                                   for x in tbmf],
                                                  columns=['cycle'] +
                                                  self.layout.get_model_ids())
                self.total_biomass = self.total_biomass.astype('float')
                if delete_files:
                    os.remove(self.parameters.all_params['TotalBiomassLogName'])

            # Read flux
            if self.parameters.all_params['writeFluxLog']:

                max_rows = 4 + max([len(m.reactions) for m in self.layout.models])

                self.fluxes = pd.read_csv(self.parameters.all_params['FluxLogName'],
                                          delim_whitespace=True,
                                          header=None, names=range(max_rows))
                if delete_files:
                    os.remove(self.parameters.all_params['FluxLogName'])
                self.build_readable_flux_object()

            # Read media logs
            if self.parameters.all_params['writeMediaLog']:
                self.media = pd.read_csv(self.parameters.all_params[
                    'MediaLogName'], delim_whitespace=True, names=('metabolite',
                                                                   'cycle', 'x',
                                                                   'y',
                                                                   'conc_mmol'))

                if delete_files:
                    os.remove(self.parameters.all_params['MediaLogName'])

            # Read spatial biomass log
            if self.parameters.all_params['writeBiomassLog']:
                biomass_out_file = 'biomass_log_' + hex(id(self))
                self.biomass = pd.read_csv(biomass_out_file,
                                           header=None, delimiter=r'\s+',
                                           names=['cycle', 'x', 'y',
                                                  'species', 'biomass'])
                if delete_files:
                    os.remove(biomass_out_file)

            # Read evolution-related logs
            if 'evolution' in list(self.parameters.all_params.keys()):
                if self.parameters.all_params['evolution']:
                    genotypes_out_file = 'GENOTYPES_biomass_log_' + hex(id(self))
                    self.genotypes = pd.read_csv(genotypes_out_file,
                                                 header=None, delimiter=r'\s+',
                                                 names=['Ancestor',
                                                        'Mutation',
                                                        'Species'])
                    if delete_files:
                        os.remove(genotypes_out_file)

            # Read specific media output
            if self.parameters.all_params['writeSpecificMediaLog']:
                spec_med_file = self.parameters.all_params['SpecificMediaLogName']
                self.specific_media = pd.read_csv(spec_med_file, delimiter=r'\s+')
                if delete_files:
                    os.remove(self.parameters.all_params['SpecificMediaLogName'])

            # clean workspace
            if delete_files:
                os.remove(c_global)
                os.remove(c_package)
                os.remove(c_script)
                os.remove('.current_layout')
                os.remove('COMETS_manifest.txt')  # todo: stop writing this in java
            print('Done!')

    def build_readable_flux_object(self):
        """ comets.fluxes is an odd beast, where the column position has a
        different meaning depending on what model the row is about. Therefore,
        this function creates separate dataframes, stored in a dictionary with
        model_id as a key, that are much more human-readable."""

        self.fluxes_by_species = {}
        for i in range(len(self.layout.models)):
            model_num = i + 1

            model_id = self.layout.models[model_num - 1].id
            model_rxn_names = list(self.layout.models[
                model_num - 1].reactions.REACTION_NAMES)
            model_rxn_len = len(model_rxn_names)

            sub_df = self.fluxes.loc[self.fluxes[3] == model_num]
            
            # this tosses extraneous columns and the model num column
            sub_df = sub_df.drop(sub_df.columns[model_rxn_len+4: len(sub_df.columns)],
                                 axis=1)
            sub_df = sub_df.drop(sub_df.columns[3], axis=1)
            sub_df.columns = ["cycle", "x", "y"] + model_rxn_names
            self.fluxes_by_species[model_id] = sub_df

    def get_metabolite_image(self, met, cycle):
        if not self.parameters.all_params['writeMediaLog']:
            raise ValueError("media log was not recorded during simulation")
        if met not in list(self.layout.media.metabolite):
            raise NameError("met " + met + " is not in layout.media.metabolite")
        if cycle not in list(np.unique(self.media['cycle'])):
            raise ValueError('media was not saved at the desired cycle. try another.')
        im = np.zeros((self.layout.grid[0], self.layout.grid[1]))
        aux = self.media.loc[np.logical_and(self.media['cycle'] == cycle,
                                            self.media['metabolite'] == met)]
        for index, row in aux.iterrows():
            im[int(row['x']-1), int(row['y']-1)] = row['conc_mmol']
        return(im)

    def get_biomass_image(self, model_id, cycle):
        if not self.parameters.all_params['writeBiomassLog']:
            raise ValueError("biomass log was not recorded during simulation")
        if model_id not in [m.id for m in self.layout.models]:
            raise NameError("model " + model_id + " is not one of the model ids")
        if cycle not in list(np.unique(self.biomass['cycle'])):
            raise ValueError('biomass was not saved at the desired cycle. try another.')
        im = np.zeros((self.layout.grid[0], self.layout.grid[1]))
        aux = self.biomass.loc[self.biomass['cycle'] == cycle, :]
        for index, row in aux.iterrows():
            im[int(row['x']-1), int(row['y']-1)] = row[model_id]
        return(im)

    def get_flux_image(self, model_id, reaction_id, cycle):
        if not self.parameters.all_params['writeFluxLog']:
            raise ValueError("flux log was not recorded during simulation")
        if model_id not in [m.id for m in self.layout.models]:
            raise NameError("model " + model_id + " is not one of the model ids")
        im = np.zeros((self.layout.grid[0], self.layout.grid[1]))
        temp_fluxes = self.fluxes_by_species[model_id]
        if cycle not in list(np.unique(temp_fluxes['cycle'])):
            raise ValueError('flux was not saved at the desired cycle. try another.')
        if reaction_id not in list(temp_fluxes.columns):
            raise NameError("reaction_id " + reaction_id +
                            " is not a reaction in the desired model")
        aux = temp_fluxes.loc[temp_fluxes['cycle'] == cycle, :]
        for index, row in aux.iterrows():
            im[int(row['x']-1), int(row['y']-1)] = row[reaction_id]
        return(im)



    
# TODO: fix read_comets_layout to always expect text addresses of comets model files
# TODO: read spatial biomass logs
# TODO: remove comets manifest (preferably, dont write it)
# TODO: find quicker reading solution than the pd.read_csv stringIO hack
# TODO: add units when printing params
# TODO: solve weird rounding errors when reading from comets model
# TODO: update media with all exchangeable metabolites from all models
# TODO: give warning when unknown parameter is set 
# TODO: write parameters in single file
# TODO: model biomass should be added in the layout "add_model" method, and not as a model class field
# TODO: adding models seems to remove media that has been previously set up
# TODO: write documentation properly for all functions and classes
