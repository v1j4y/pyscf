#!/usr/bin/env python
#
# Author: Qiming Sun <osirpt.sun@gmail.com>
#

import numpy
from pyscf import gto, scf, mcscf

'''
A simple example to run CASSCF calculation.
'''

mol = gto.M(
    atom = 'O 0 0 0; O 0 0 1.2',
    basis = 'ccpvdz',
    spin = 2)

myhf = scf.RHF(mol)
myhf.kernel()

# 6 orbitals, 8 electrons
mycas = mcscf.CASSCF(myhf, 6, 8)
mycas.kernel()

# Natural occupancy in CAS space, Mulliken population etc.
mycas.verbose = 4
mycas.analyze()
