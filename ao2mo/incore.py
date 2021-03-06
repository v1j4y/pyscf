#!/usr/bin/env python
#
# Author: Qiming Sun <osirpt.sun@gmail.com>
#

import sys
import numpy
import ctypes
from pyscf.lib import logger
from pyscf.ao2mo import _ao2mo

BLOCK = 56

def full(eri_ao, mo_coeff, verbose=0, compact=True):
    r'''MO integral transformation for the given orbital.

    Args:
        eri_ao : ndarray
            AO integrals, can be either 8-fold or 4-fold symmetry.
        mo_coeff : ndarray
            Transform (ij|kl) with the same set of orbitals.

    Kwargs:
        verbose : int
            Print level
        compact : bool
            When compact is True, the returned MO integrals have 4-fold
            symmetry.  Otherwise, return the "plain" MO integrals.

    Returns:
        2D array of transformed MO integrals.  The MO integrals may or may not
        have the permutation symmetry (controlled by the kwargs compact)


    Examples:

    >>> from pyscf import gto
    >>> from pyscf.scf import _vhf
    >>> from pyscf import ao2mo
    >>> mol = gto.M(atom='O 0 0 0; H 0 1 0; H 0 0 1', basis='sto3g')
    >>> eri = _vhf.int2e_sph(mol._atm, mol._bas, mol._env)
    >>> mo1 = numpy.random.random((mol.nao_nr(), 10))
    >>> eri1 = ao2mo.incore.full(eri, mo1)
    >>> print(eri1.shape)
    (55, 55)
    >>> eri1 = ao2mo.incore.full(eri, mo1, compact=False)
    >>> print(eri1.shape)
    (100, 100)

    '''
    return general(eri_ao, (mo_coeff,)*4, verbose, compact)

# It consumes two times of the memory needed by MO integrals
def general(eri_ao, mo_coeffs, verbose=0, compact=True):
    r'''For the given four sets of orbitals, transfer the 8-fold or 4-fold 2e
    AO integrals to MO integrals.

    Args:
        eri_ao : ndarray
            AO integrals, can be either 8-fold or 4-fold symmetry.
        mo_coeffs : 4-item list of ndarray
            Four sets of orbital coefficients, corresponding to the four
            indices of (ij|kl)

    Kwargs:
        verbose : int
            Print level
        compact : bool
            When compact is True, depending on the four oribital sets, the
            returned MO integrals has (up to 4-fold) permutation symmetry.
            If it's False, the function will abandon any permutation symmetry,
            and return the "plain" MO integrals

    Returns:
        2D array of transformed MO integrals.  The MO integrals may or may not
        have the permutation symmetry, depending on the given orbitals, and
        the kwargs compact.  If the four sets of orbitals are identical, the
        MO integrals will at most have 4-fold symmetry.


    Examples:

    >>> from pyscf import gto
    >>> from pyscf.scf import _vhf
    >>> from pyscf import ao2mo
    >>> mol = gto.M(atom='O 0 0 0; H 0 1 0; H 0 0 1', basis='sto3g')
    >>> eri = _vhf.int2e_sph(mol._atm, mol._bas, mol._env)
    >>> mo1 = numpy.random.random((mol.nao_nr(), 10))
    >>> mo2 = numpy.random.random((mol.nao_nr(), 8))
    >>> mo3 = numpy.random.random((mol.nao_nr(), 6))
    >>> mo4 = numpy.random.random((mol.nao_nr(), 4))
    >>> eri1 = ao2mo.incore.general(eri, (mo1,mo2,mo3,mo4))
    >>> print(eri1.shape)
    (80, 24)
    >>> eri1 = ao2mo.incore.general(eri, (mo1,mo2,mo3,mo3))
    >>> print(eri1.shape)
    (80, 21)
    >>> eri1 = ao2mo.incore.general(eri, (mo1,mo2,mo3,mo3), compact=False)
    >>> print(eri1.shape)
    (80, 36)
    >>> eri1 = ao2mo.incore.general(eri, (mo1,mo1,mo2,mo2))
    >>> print(eri1.shape)
    (55, 36)
    >>> eri1 = ao2mo.incore.general(eri, (mo1,mo2,mo1,mo2))
    >>> print(eri1.shape)
    (80, 80)

    '''
    if isinstance(verbose, logger.Logger):
        log = verbose
    else:
        log = logger.Logger(sys.stdout, verbose)

    ijsame = compact and iden_coeffs(mo_coeffs[0], mo_coeffs[1])
    klsame = compact and iden_coeffs(mo_coeffs[2], mo_coeffs[3])

    nmoi = mo_coeffs[0].shape[1]
    nmoj = mo_coeffs[1].shape[1]
    nmok = mo_coeffs[2].shape[1]
    nmol = mo_coeffs[3].shape[1]

    nao = mo_coeffs[0].shape[0]
    nao_pair = nao*(nao+1)//2
    assert(eri_ao.size in (nao_pair**2, nao_pair*(nao_pair+1)//2))

    if compact and ijsame:
        nij_pair = nmoi*(nmoi+1) // 2
    else:
        nij_pair = nmoi*nmoj

    if compact and klsame:
        klmosym = 's2'
        nkl_pair = nmok*(nmok+1) // 2
        mokl = numpy.array(mo_coeffs[2], order='F', copy=False)
        klshape = (0, nmok, 0, nmok)
    else:
        klmosym = 's1'
        nkl_pair = nmok*nmol
        mokl = numpy.array(numpy.hstack((mo_coeffs[2],mo_coeffs[3])), \
                           order='F', copy=False)
        klshape = (0, nmok, nmok, nmol)

    if nij_pair == 0 or nkl_pair == 0:
        # 0 dimension sometimes causes blas problem
        return numpy.zeros((nij_pair,nkl_pair))

#    if nij_pair > nkl_pair:
#        log.warn('low efficiency for AO to MO trans!')

# transform e1
    eri1 = half_e1(eri_ao, mo_coeffs, compact)

# transform e2
    eri1 = _ao2mo.nr_e2_(eri1, mokl, klshape, aosym='s4', mosym=klmosym)
    return eri1

def half_e1(eri_ao, mo_coeffs, compact=True):
    r'''Given two set of orbitals, half transform the (ij| pair of 8-fold or
    4-fold AO integrals (ij|kl)

    Args:
        eri_ao : ndarray
            AO integrals, can be either 8-fold or 4-fold symmetry.
        mo_coeffs : list of ndarray
            Two sets of orbital coefficients, corresponding to the i, j
            indices of (ij|kl)

    Kwargs:
        compact : bool
            When compact is True, the returned MO integrals uses the highest
            possible permutation symmetry.  If it's False, the function will
            abandon any permutation symmetry, and return the "plain" MO
            integrals

    Returns:
        ndarray of transformed MO integrals.  The MO integrals may or may not
        have the permutation symmetry, depending on the given orbitals, and
        the kwargs compact.

    Examples:

    >>> from pyscf import gto
    >>> from pyscf import ao2mo
    >>> mol = gto.M(atom='O 0 0 0; H 0 1 0; H 0 0 1', basis='sto3g')
    >>> eri = _vhf.int2e_sph(mol._atm, mol._bas, mol._env)
    >>> mo1 = numpy.random.random((mol.nao_nr(), 10))
    >>> mo2 = numpy.random.random((mol.nao_nr(), 8))
    >>> eri1 = ao2mo.incore.half_e1(eri, (mo1,mo2))
    >>> eri1 = ao2mo.incore.half_e1(eri, (mo1,mo2))
    >>> print(eri1.shape)
    (80, 28)
    >>> eri1 = ao2mo.incore.half_e1(eri, (mo1,mo2), compact=False)
    >>> print(eri1.shape)
    (80, 28)
    >>> eri1 = ao2mo.incore.half_e1(eri, (mo1,mo1))
    >>> print(eri1.shape)
    (55, 28)
    '''
    eri_ao = numpy.asarray(eri_ao, order='C')
    ijsame = compact and iden_coeffs(mo_coeffs[0], mo_coeffs[1])

    nmoi = mo_coeffs[0].shape[1]
    nmoj = mo_coeffs[1].shape[1]

    nao = mo_coeffs[0].shape[0]
    nao_pair = nao*(nao+1)//2

    if compact and ijsame:
        ijmosym = 's2'
        nij_pair = nmoi*(nmoi+1) // 2
        moij = numpy.array(mo_coeffs[0], order='F', copy=False)
        ijshape = (0, nmoi, 0, nmoi)
    else:
        ijmosym = 's1'
        nij_pair = nmoi*nmoj
        moij = numpy.array(numpy.hstack((mo_coeffs[0],mo_coeffs[1])), \
                           order='F', copy=False)
        ijshape = (0, nmoi, nmoi, nmoj)

    if eri_ao.size == nao_pair**2: # 4-fold symmetry
        ftrans = _ao2mo._fpointer('AO2MOtranse1_incore_s4')
    else:
        ftrans = _ao2mo._fpointer('AO2MOtranse1_incore_s8')
    if ijmosym == 's2':
        fmmm = _ao2mo._fpointer('AO2MOmmm_nr_s2_s2')
    elif nmoi <= nmoj:
        fmmm = _ao2mo._fpointer('AO2MOmmm_nr_s2_iltj')
    else:
        fmmm = _ao2mo._fpointer('AO2MOmmm_nr_s2_igtj')
    fdrv = getattr(_ao2mo.libao2mo, 'AO2MOnr_e1incore_drv')
    eri1 = numpy.empty((nij_pair,nao_pair))

    bufs = numpy.empty((BLOCK, nij_pair))
    for blk0 in range(0, nao_pair, BLOCK):
        blk1 = min(blk0+BLOCK, nao_pair)
        buf = bufs[:blk1-blk0]
        fdrv(ftrans, fmmm,
             buf.ctypes.data_as(ctypes.c_void_p),
             eri_ao.ctypes.data_as(ctypes.c_void_p),
             moij.ctypes.data_as(ctypes.c_void_p),
             ctypes.c_int(blk0), ctypes.c_int(blk1-blk0),
             ctypes.c_int(nao),
             ctypes.c_int(ijshape[0]), ctypes.c_int(ijshape[1]),
             ctypes.c_int(ijshape[2]), ctypes.c_int(ijshape[3]))
        eri1[:,blk0:blk1] = buf.T
    return eri1

def iden_coeffs(mo1, mo2):
    return (id(mo1) == id(mo2)) or \
            (mo1.shape==mo2.shape and numpy.allclose(mo1,mo2))


if __name__ == '__main__':
    from pyscf import scf
    from pyscf import gto
    mol = gto.Mole()
    mol.verbose = 5
    mol.output = 'out_h2o'
    mol.atom = [
        ["O" , (0. , 0.     , 0.)],
        [1   , (0. , -0.757 , 0.587)],
        [1   , (0. , 0.757  , 0.587)]]

    mol.basis = {'H': 'cc-pvtz',
                 'O': 'cc-pvtz',}
    mol.build()
    rhf = scf.RHF(mol)
    rhf.scf()
    import time
    print(time.clock())
    eri0 = full(rhf._eri, rhf.mo_coeff)
    print(abs(eri0).sum()-5384.460843787659) # should = 0
    eri0 = general(rhf._eri, (rhf.mo_coeff,)*4)
    print(abs(eri0).sum()-5384.460843787659)
    print(time.clock())

