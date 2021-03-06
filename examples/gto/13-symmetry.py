#!/usr/bin/env python
#
# Author: Qiming Sun <osirpt.sun@gmail.com>
#

from pyscf import gto

'''
Specify symmetry.

Mole.symmetry can be True/False to turn on/off the symmetry (default is off),
or a string to specify the symmetry of molecule.

If symmetry is bool type, the atom coordinates might be changed.  The molecule
will be rotated to a propper orientation in which the highest rotation axis
is parallel to Z-axis.  Also, symmetry_subgroup keyword can be used to
generate a subgroup of the dectected symmetry.  symmetry_subgroup keyword has
no effect when symmetry symbol is explicitly given.

NOTE: to assign Mole.symmetry with a given symbol,  the molecule must be put
in a proper orientation.  The program will check the given symmetry to ensure
that the molecule has the required symmetry.  If the detected symmetry does
not match to the assigend symmetry, you will see a warning message on the
screen.

Symmetry adapted basis are stored in Mole object.
'''

mol = gto.M(
    atom = 'C 0 0 0; O 0 0 1.5',
    symmetry = True,
)
print('%-4s is a subgroup of %s' % (mol.groupname, mol.topgroup))

mol = gto.M(
    atom = 'C 0 0 0; O 0 0 1.5',
    symmetry = True,
    symmetry_subgroup = 'C2v',
)
print('%-4s is a subgroup of %s' % (mol.groupname, mol.topgroup))

mol = gto.M(
    atom = 'C 0 0 0; O 0 0 1.5',
    symmetry = 'C2v',
)
print('%-4s is a subgroup of %s' % (mol.groupname, mol.topgroup))

mol = gto.M(
    atom = 'C 0 0 0; O 0 1.5 0',
    symmetry = 'C2v',
)

for k, ir in enumerate(mol.irrep_name):
    print('Irrep name %s  (ID %d), symm-adapted-basis shape %s' %
          (ir, mol.irrep_id[k], mol.symm_orb[k].shape))
