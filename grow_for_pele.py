# General imports
import sys
import argparse
import os
import logging
from logging.config import fileConfig
import shutil
import subprocess
# Local imports
import Growing.template_selector
import Growing.template_fragmenter
import Growing.simulations_linker
import Growing.add_fragment_from_pdbs
import Growing.AddingFragHelpers
import constants as c

# Calling configuration file for log system
fileConfig(c.CONFIG_PATH)

# Getting the name of the module for the log system
logger = logging.getLogger(__name__)

# Get current path
curr_dir = os.path.abspath(os.path.curdir)


def parse_arguments():
    """
        Parse user arguments

        Output: list with all the user arguments
    """
    # All the docstrings are very provisional and some of them are old, they would be changed in further steps!!
    parser = argparse.ArgumentParser(description="""From an input file, correspondent to the template of the initial 
    structure of the ligand,this function will generate "x_fragments" intermediate templates until reach the final 
    template,modifying Vann Der Waals, bond lengths and deleting charges.""")
    required_named = parser.add_argument_group('required named arguments')
    # Growing related arguments
    required_named.add_argument("-cp", "--complex_pdb", required=True,
                        help="""PDB file which contains a protein-ligand complex that we will use as 
                        core for growing (name the chain of the ligand "L")""")
    required_named.add_argument("-fp", "--fragment_pdb", required=True,
                        help="""PDB file which contains the fragment that will be added to the core structure (name the 
                        chain of the fragment "L")""")
    required_named.add_argument("-ca", "--core_atom", required=True,
                        help="""String with the PDB atom name of the heavy atom of the core (the ligand contained in 
                        the complex) where you would like to start the growing and create a new bond with the fragment.
                        """)
    required_named.add_argument("-fa", "--fragment_atom", required=True,
                        help="""String with the PDB atom name of the heavy atom of the fragment that will be used to 
                        perform the bonding with the core.""")

    parser.add_argument("-x", "--iterations", type=int, default=c.ITERATIONS,
                        help="""Number of intermediate templates that you want to generate""")
    parser.add_argument("-cr", "--criteria", default=c.SELECTION_CRITERIA,
                        help="""Name of the column used as criteria in order to select the template used as input for 
                                 successive simulations.""")
    # Plop related arguments
    parser.add_argument("-pl", "--plop_path", default=c.PLOP_PATH,
                        help="Absolute path to PlopRotTemp.py.")
    parser.add_argument("-sp", "--sch_python", default=c.SCHRODINGER_PY_PATH,
                        help="Absolute path to Schrödinger's python.")
    # PELE configuration arguments
    parser.add_argument("-d", "--pele_dir", default=c.PATH_TO_PELE,
                        help="Complete path to Pele_serial")
    parser.add_argument("-c", "--contrl", default=c.CONTROL_TEMPLATE,
                        help="Control file templatized.")
    parser.add_argument("-r", "--resfold", default=c.RESULTS_FOLDER,
                        help="Name for results folder")
    parser.add_argument("-rp", "--report", default=c.REPORT_NAME,
                        help="Suffix name of the report file from PELE.")
    parser.add_argument("-tj", "--traject", default=c.TRAJECTORY_NAME,
                        help="Suffix name of the trajectory file from PELE.")
    parser.add_argument("-pdbf", "--pdbout", default=c.PDBS_OUTPUT_FOLDER,
                        help="PDBs output folder")
    args = parser.parse_args()

    return args.complex_pdb, args.fragment_pdb, args.core_atom, args.fragment_atom, args.iterations, args.criteria, args.plop_path, args.sch_python, args.pele_dir, args.contrl, args.resfold, args.report, args.traject, args.pdbout


def main(complex_pdb, fragment_pdb, core_atom, fragment_atom, iterations, criteria, plop_path, sch_python,
         pele_dir, contrl, resfold, report, traject, pdbout):
    """
        Description: This function is the main core of the program. It creates N intermediate templates
        and control files for PELE. Then, it perform N successive simulations automatically.

        Input:

        :param: template_initial: Name of the input file correspondent to the initial template for the ligand that you
        want to grow.
        :param template_final: Name of the input file correspondent to the final template for the ligand that you want
        to get.
        :param n_files: Number of intermediate templates that you want to generate
        :param original_atom: When an atom is transformed into another one we want to conserve the properties.
        The PDB atom name of the initial template that we want to transform into another of the final template has to be
        specified here.
       :param final_atom: When an atom is transformed into another one we want to conserve the properties.
        The PDB atom name of the final template that will be used as target to be transformed into the original atom.
        :param control_template: Template control file used to generate intermediates control files.
        :param pdb: Initial pdb file which already contain the ligand with the fragment that we want to grow
        but with bond lengths correspondent to the initial ligand (dummy-like).
        :param results_f_name: Name for results folder.
        :param criteria: Name of the column of the report file used as criteria in order to select the template
        used as input for successive simulations.
        :param path_pele: Complete path to Pele_serial.
        :param report: Name of the report file of PELE simulation's results.
        :param traject: Name of the trajectory file of PELE simulation's results.
        :return The algorithm is formed by two main parts:
        First, it prepare the files needed in a PELE simulation: control file and ligand templates.
        Second, after analyzing the report file it selects the best structure in the trajectory file in order to be used
        as input for the next growing step.
        This process will be repeated until get the final grown ligand (protein + ligand).
        """
    # MAIN LOOP

    # Pre-growing part - Preparation

    fragment_names_dict, hydrogen_atoms, pdb_to_initial_template, pdb_to_final_template, pdb_initialize = Growing.\
        add_fragment_from_pdbs.main(complex_pdb, fragment_pdb, core_atom, fragment_atom, iterations)
    # Create the templates for the initial and final structures
    template_resnames = []
    for pdb_to_template in [pdb_to_initial_template, pdb_to_final_template]:
        cmd = "{} {} {}".format(sch_python, plop_path, os.path.join(curr_dir,
                                Growing.add_fragment_from_pdbs.PRE_WORKING_DIR, pdb_to_template))
        subprocess.call(cmd.split())
        template_resname = Growing.add_fragment_from_pdbs.extract_heteroatoms_pdbs(os.path.join(
                                                                                   Growing.add_fragment_from_pdbs.
                                                                                   PRE_WORKING_DIR, pdb_to_template),
                                                                                   False)
        template_resnames.append(template_resname)
    # Now, move the templates to their respective folders
    template_names = []
    for resname in template_resnames:
        template_name = "{}z".format(resname.lower())
        template_names.append(template_name)
        shutil.copy(template_name, os.path.join(curr_dir, c.TEMPLATES_PATH))
        shutil.copy("{}.rot.assign".format(resname), os.path.join(curr_dir, c.ROTAMERS_PATH))
    template_initial, template_final = template_names

    # Growing part

    templates = ["{}_{}".format(template_final, n) for n in range(0, iterations+1)]

    results = ["{}{}_{}".format(c.OUTPUT_FOLDER, resfold, n) for n in range(0, iterations+1)]

    pdbs = [pdb_initialize if n == 0 else "{}_{}".format(n, pdb_initialize) for n in range(0, iterations+1)]

    # Create a copy of the original templates in growing_templates folder
    shutil.copy(os.path.join(curr_dir, c.TEMPLATES_PATH, template_initial),
                os.path.join(os.path.join(curr_dir, c.TEMPLATES_PATH, c.TEMPLATES_FOLDER), template_initial))

    shutil.copy(os.path.join(curr_dir, c.TEMPLATES_PATH, template_final),
                os.path.join(os.path.join(curr_dir, c.TEMPLATES_PATH, c.TEMPLATES_FOLDER), template_final))

    original_atom = hydrogen_atoms[0].get_name()  # Hydrogen of the core that we will use as growing point
    # Generate starting templates
    Growing.template_fragmenter.create_initial_template(template_initial, template_final, [original_atom], core_atom,
                                                        "{}_0".format(template_final),
                                                        os.path.join(curr_dir, c.TEMPLATES_PATH),
                                                        iterations)
    Growing.template_fragmenter.generate_starting_template(template_initial, template_final, [original_atom],
                                                           core_atom, "{}_ref".format(template_final),
                                                           os.path.join(curr_dir, c.TEMPLATES_PATH),
                                                           iterations)

    # Make a copy in the main folder of Templates in order to use it as template for the simulation
    shutil.copy(os.path.join(curr_dir, c.TEMPLATES_PATH, "{}_0".format(template_final)),
                os.path.join(curr_dir, c.TEMPLATES_PATH, template_final))  # Replace the original template in the folder

    # Simulation loop
    for i, (template, pdb_file, result) in enumerate(zip(templates, pdbs, results)):

        # Control file modification
        logger.info(c.SELECTED_MESSAGE.format(contrl, pdb_initialize, result, i))
        Growing.simulations_linker.control_file_modifier(contrl, pdb_initialize, i, pele_dir, result)

        if i != 0 and i != iterations:
            Growing.template_fragmenter.grow_parameters_in_template("{}_ref".format(template_final),
                                                                    os.path.join(curr_dir, c.TEMPLATES_PATH
                                                                    , c.TEMPLATES_FOLDER, template_initial),
                                                                    os.path.join(curr_dir, c.TEMPLATES_PATH
                                                                    , c.TEMPLATES_FOLDER, template_final),
                                                                    [original_atom], core_atom, template_final,
                                                                    os.path.join(curr_dir, c.TEMPLATES_PATH),
                                                                    i)
        elif i == iterations:
            shutil.copy(os.path.join(os.path.join(curr_dir, c.TEMPLATES_PATH, c.TEMPLATES_FOLDER), template_final),
                        os.path.join(os.path.join(curr_dir, c.TEMPLATES_PATH, template_final)))

        # Make a copy of the template file in growing_templates folder
        shutil.copy(os.path.join(curr_dir, c.TEMPLATES_PATH, template_final),
                    os.path.join(os.path.join(curr_dir, c.TEMPLATES_PATH, c.TEMPLATES_FOLDER), template))

        # Running PELE simulation
        if not os.path.exists(result):
            os.chdir("growing_results")
            os.mkdir(result)
            os.chdir("../")

        logger.info(c.FINISH_SIM_MESSAGE.format(result))
        Growing.simulations_linker.simulation_runner(pele_dir, contrl)

        # Before selecting a step from a trajectory we will save the input PDB file in a folder
        shutil.copy(pdb_initialize, os.path.join(pdbout, pdb_file))

        # Selection of the trajectory used as new input
        Growing.template_selector.trajectory_selector(pdb_initialize, result, report, traject, criteria)


if __name__ == '__main__':
    complex_pdb, fragment_pdb, core_atom, fragment_atom, iterations, criteria, plop_path, sch_python, pele_dir, contrl, resfold, report, traject, pdbout = parse_arguments()
    main(complex_pdb, fragment_pdb, core_atom, fragment_atom, iterations, criteria, plop_path, sch_python, pele_dir,
         contrl, resfold, report, traject, pdbout)
