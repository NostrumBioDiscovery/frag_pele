import prody
#import pybel
import logging
import sys

# Getting the name of the module for the log system
logger = logging.getLogger(__name__)


def pdb_parser_ligand(pdb_file, ligand_chain="L"):
    """
    :param pdb_file: input PDB file of the complex that we want to get their ligand
    :param ligand_chain: chain where the ligand is placed
    :return: PRODY object with the atoms of the ligand of the input PDB
    """
    pdb = prody.parsePDB(pdb_file)
    ligand = pdb.select("chain {}".format(ligand_chain))
    if ligand is None:
        logger.critical("Wrong chain selected!")
    elif ligand.ishetero:
        return ligand
    else:
       logger.critical("The selected chain does not contain heteroatoms!")


def pdb_parser_residue(pdb_file, res_chain, res_num):
    """
    :param pdb_file: input PDB file of the complex that we want to get their residue
    :param res_chain: chain where the residue is placed
    :return: PRODY object with the atoms of the residue of the input PDB
    """
    pdb = prody.parsePDB(pdb_file)
    residue = pdb.select("chain {} and resnum {}".format(res_chain, res_num))
    if residue is None:
        logger.critical("Wrong selection!")
    else:
        return residue

def read_residue_string(string):
    if not ":" in string:
        raise ("Wrong style. Please, follow the style of the example: 'A:145'")
    split = string.split(":")
    if len(split) != 2:
        raise("Too many arguments. Please, follow the style of the example: 'A:145'")
    chain, resnum = string.split(":")
    return chain, resnum

def selection_to_pdb(selection):
    """
    :param selection: prody selection
    :return: writes a PDB file containing the selection, named using the residue name of the first atom of the selection.
    """
    prody.writePDB(selection.getResnames()[0], selection)
    return "{}.pdb".format(selection.getResnames()[0])


def check_protonation(selection):
    """
    Check if the structure is protonated or not. In case that is not protonated we will rise a critical logger.
    :param selection: prody molecule
    :return: if not hydrogens detected, prints a message.
    """
    try:
        if not selection.select("hydrogen"):
            logger.critical("We have not detected Hydrogens in your ligand. Please, add them before starting.")
    except AttributeError:
        raise AttributeError("Check ligand and core are in the L chain. Otherwise specify their chain using the flags \
-cc chain_core -fc chain_frag. Fragment & Core must always be in the same chain.")


