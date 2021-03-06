#!/usr/bin/env python
# -*- coding: utf-8
# Author: Qiming Sun <osirpt.sun@gmail.com>

import numpy
import h5py
from pyscf.ao2mo import incore
from pyscf.ao2mo import outcore
from pyscf.ao2mo import r_outcore

from pyscf.ao2mo.addons import load, restore

def full(eri_or_mol, mo_coeff, *args, **kwargs):
    r'''MO integral transformation. The four indices (ij|kl) are transformed
    with the same set of orbitals.

    Args:
        eri_or_mol : ndarray or Mole object
            If AO integrals are given as ndarray, it can be either 8-fold or
            4-fold symmetry.  The integral transformation are computed incore
            (ie all intermediate are held in memory).
            If Mole object is given, AO integrals are generated on the fly and
            outcore algorithm is used (ie intermediate data are held on disk).
        mo_coeff : ndarray
            Orbital coefficients in 2D array
        erifile : str or h5py File or h5py Group object
            *Note* this argument is effective when eri_or_mol is Mole object.
            The file to store the transformed integrals.  If not given, the
            transformed integrals are held in memory.

    Kwargs:
        dataname : str
            *Note* this argument is effective when eri_or_mol is Mole object.
            The dataset name in the erifile (ref the hierarchy of HDF5 format
            http://www.hdfgroup.org/HDF5/doc1.6/UG/09_Groups.html).  By assigning
            different dataname, the existed integral file can be reused.  If
            the erifile contains the dataname, the new integrals data will
            overwrite the old one.
        tmpdir : str
            *Note* this argument is effective when eri_or_mol is Mole object.
            The directory where to temporarily store the intermediate data
            (the half-transformed integrals).  By default, it's controlled by
            shell environment variable ``TMPDIR``.  The disk space requirement
            is about  comp*mo_coeffs[0].shape[1]*mo_coeffs[1].shape[1]*nao**2
        intor : str
            *Note* this argument is effective when eri_or_mol is Mole object.
            Name of the 2-electron integral.  Ref to :func:`getints_by_shell`
            for the complete list of available 2-electron integral names
        aosym : int or str
            *Note* this argument is effective when eri_or_mol is Mole object.
            Permutation symmetry for the AO integrals

            | 4 or '4' or 's4': 4-fold symmetry (default)
            | '2ij' or 's2ij' : symmetry between i, j in (ij|kl)
            | '2kl' or 's2kl' : symmetry between k, l in (ij|kl)
            | 1 or '1' or 's1': no symmetry
            | 'a4ij' : 4-fold symmetry with anti-symmetry between i, j in (ij|kl) (TODO)
            | 'a4kl' : 4-fold symmetry with anti-symmetry between k, l in (ij|kl) (TODO)
            | 'a2ij' : anti-symmetry between i, j in (ij|kl) (TODO)
            | 'a2kl' : anti-symmetry between k, l in (ij|kl) (TODO)

        comp : int
            *Note* this argument is effective when eri_or_mol is Mole object.
            Components of the integrals, e.g. cint2e_ip_sph has 3 components.
        max_memory : float or int
            *Note* this argument is effective when eri_or_mol is Mole object.
            The maximum size of cache to use (in MB), large cache may **not**
            improve performance.
        ioblk_size : float or int
            *Note* this argument is effective when eri_or_mol is Mole object.
            The block size for IO, large block size may **not** improve performance
        verbose : int
            Print level
        compact : bool
            When compact is True, depending on the four oribital sets, the
            returned MO integrals has (up to 4-fold) permutation symmetry.
            If it's False, the function will abandon any permutation symmetry,
            and return the "plain" MO integrals

    Returns:
        If eri_or_mol is array or erifile is not give,  the function returns 2D
        array (or 3D array if comp > 1) of transformed MO integrals.  The MO
        integrals may or may not have the permutation symmetry (controlled by
        the kwargs compact).
        Otherwise, return the file/fileobject where the MO integrals are saved.


    Examples:

    >>> from pyscf import gto, ao2mo
    >>> import h5py
    >>> def view(h5file, dataname='eri_mo'):
    ...     with h5py.File(h5file) as f5:
    ...         print('dataset %s, shape %s' % (str(f5.keys()), str(f5[dataname].shape)))
    >>> mol = gto.M(atom='O 0 0 0; H 0 1 0; H 0 0 1', basis='sto3g')
    >>> mo1 = numpy.random.random((mol.nao_nr(), 10))

    >>> eri1 = ao2mo.full(mol, mo1)
    >>> print(eri1.shape)
    (55, 55)

    >>> eri = mol.intor('cint2e_sph', aosym='s8')
    >>> eri1 = ao2mo.full(eri, mo1, compact=False)
    >>> print(eri1.shape)
    (100, 100)

    >>> ao2mo.full(mol, mo1, 'full.h5')
    >>> view('full.h5')
    dataset ['eri_mo'], shape (55, 55)

    >>> ao2mo.full(mol, mo1, 'full.h5', dataname='new', compact=False)
    >>> view('full.h5', 'new')
    dataset ['eri_mo', 'new'], shape (100, 100)

    >>> ao2mo.full(mol, mo1, 'full.h5', intor='cint2e_ip1_sph', aosym='s1', comp=3)
    >>> view('full.h5')
    dataset ['eri_mo', 'new'], shape (3, 100, 100)

    >>> ao2mo.full(mol, mo1, 'full.h5', intor='cint2e_ip1_sph', aosym='s2kl', comp=3)
    >>> view('full.h5')
    dataset ['eri_mo', 'new'], shape (3, 100, 55)
    '''
    if isinstance(eri_or_mol, numpy.ndarray):
        return incore.full(eri_or_mol, mo_coeff, *args, **kwargs)
    else:
        if 'intor' in kwargs and ('_sph' not in kwargs['intor']):
            mod = r_outcore
        else:
            mod = outcore
        if len(args) > 0 and isinstance(args[0], (str, h5py.Group)): # args[0] is erifile
            fn = getattr(mod, 'full')
        else:
            fn = getattr(mod, 'full_iofree')
        return fn(eri_or_mol, mo_coeff, *args, **kwargs)

def general(eri_or_mol, mo_coeffs, *args, **kwargs):
    r'''Given four sets of orbitals corresponding to the four MO indices,
    transfer arbitrary spherical AO integrals to MO integrals.

    Args:
        eri_or_mol : ndarray or Mole object
            If AO integrals are given as ndarray, it can be either 8-fold or
            4-fold symmetry.  The integral transformation are computed incore
            (ie all intermediate are held in memory).
            If Mole object is given, AO integrals are generated on the fly and
            outcore algorithm is used (ie intermediate data are held on disk).
        mo_coeffs : 4-item list of ndarray
            Four sets of orbital coefficients, corresponding to the four
            indices of (ij|kl)
        erifile : str or h5py File or h5py Group object
            *Note* this argument is effective when eri_or_mol is Mole object.
            The file to store the transformed integrals.  If not given, the
            transformed integrals are held in memory.

    Kwargs:
        dataname : str
            *Note* this argument is effective when eri_or_mol is Mole object.
            The dataset name in the erifile (ref the hierarchy of HDF5 format
            http://www.hdfgroup.org/HDF5/doc1.6/UG/09_Groups.html).  By assigning
            different dataname, the existed integral file can be reused.  If
            the erifile contains the dataname, the new integrals data will
            overwrite the old one.
        tmpdir : str
            *Note* this argument is effective when eri_or_mol is Mole object.
            The directory where to temporarily store the intermediate data
            (the half-transformed integrals).  By default, it's controlled by
            shell environment variable ``TMPDIR``.  The disk space requirement
            is about  comp*mo_coeffs[0].shape[1]*mo_coeffs[1].shape[1]*nao**2
        intor : str
            *Note* this argument is effective when eri_or_mol is Mole object.
            Name of the 2-electron integral.  Ref to :func:`getints_by_shell`
            for the complete list of available 2-electron integral names
        aosym : int or str
            *Note* this argument is effective when eri_or_mol is Mole object.
            Permutation symmetry for the AO integrals

            | 4 or '4' or 's4': 4-fold symmetry (default)
            | '2ij' or 's2ij' : symmetry between i, j in (ij|kl)
            | '2kl' or 's2kl' : symmetry between k, l in (ij|kl)
            | 1 or '1' or 's1': no symmetry
            | 'a4ij' : 4-fold symmetry with anti-symmetry between i, j in (ij|kl) (TODO)
            | 'a4kl' : 4-fold symmetry with anti-symmetry between k, l in (ij|kl) (TODO)
            | 'a2ij' : anti-symmetry between i, j in (ij|kl) (TODO)
            | 'a2kl' : anti-symmetry between k, l in (ij|kl) (TODO)

        comp : int
            *Note* this argument is effective when eri_or_mol is Mole object.
            Components of the integrals, e.g. cint2e_ip_sph has 3 components.
        max_memory : float or int
            *Note* this argument is effective when eri_or_mol is Mole object.
            The maximum size of cache to use (in MB), large cache may **not**
            improve performance.
        ioblk_size : float or int
            *Note* this argument is effective when eri_or_mol is Mole object.
            The block size for IO, large block size may **not** improve performance
        verbose : int
            Print level
        compact : bool
            When compact is True, depending on the four oribital sets, the
            returned MO integrals has (up to 4-fold) permutation symmetry.
            If it's False, the function will abandon any permutation symmetry,
            and return the "plain" MO integrals

    Returns:
        If eri_or_mol is array or erifile is not give,  the function returns 2D
        array (or 3D array, if comp > 1) of transformed MO integrals.  The MO
        integrals may at most have 4-fold symmetry (if the four sets of orbitals
        are identical) or may not have the permutation symmetry (controlled by
        the kwargs compact).
        Otherwise, return the file/fileobject where the MO integrals are saved.


    Examples:

    >>> from pyscf import gto, ao2mo
    >>> import h5py
    >>> def view(h5file, dataname='eri_mo'):
    ...     with h5py.File(h5file) as f5:
    ...         print('dataset %s, shape %s' % (str(f5.keys()), str(f5[dataname].shape)))
    >>> mol = gto.M(atom='O 0 0 0; H 0 1 0; H 0 0 1', basis='sto3g')
    >>> mo1 = numpy.random.random((mol.nao_nr(), 10))
    >>> mo2 = numpy.random.random((mol.nao_nr(), 8))
    >>> mo3 = numpy.random.random((mol.nao_nr(), 6))
    >>> mo4 = numpy.random.random((mol.nao_nr(), 4))

    >>> eri1 = ao2mo.general(eri, (mo1,mo2,mo3,mo4))
    >>> print(eri1.shape)
    (80, 24)

    >>> eri1 = ao2mo.general(eri, (mo1,mo2,mo3,mo3))
    >>> print(eri1.shape)
    (80, 21)

    >>> eri1 = ao2mo.general(eri, (mo1,mo2,mo3,mo3), compact=False)
    >>> print(eri1.shape)
    (80, 36)

    >>> eri1 = ao2mo.general(eri, (mo1,mo1,mo2,mo2))
    >>> print(eri1.shape)
    (55, 36)

    >>> eri1 = ao2mo.general(eri, (mo1,mo2,mo1,mo2))
    >>> print(eri1.shape)
    (80, 80)

    >>> ao2mo.general(mol, (mo1,mo2,mo3,mo4), 'oh2.h5')
    >>> view('oh2.h5')
    dataset ['eri_mo'], shape (80, 24)

    >>> ao2mo.general(mol, (mo1,mo2,mo3,mo3), 'oh2.h5')
    >>> view('oh2.h5')
    dataset ['eri_mo'], shape (80, 21)

    >>> ao2mo.general(mol, (mo1,mo2,mo3,mo3), 'oh2.h5', compact=False)
    >>> view('oh2.h5')
    dataset ['eri_mo'], shape (80, 36)

    >>> ao2mo.general(mol, (mo1,mo1,mo2,mo2), 'oh2.h5')
    >>> view('oh2.h5')
    dataset ['eri_mo'], shape (55, 36)

    >>> ao2mo.general(mol, (mo1,mo1,mo1,mo1), 'oh2.h5', dataname='new')
    >>> view('oh2.h5', 'new')
    dataset ['eri_mo', 'new'], shape (55, 55)

    >>> ao2mo.general(mol, (mo1,mo1,mo1,mo1), 'oh2.h5', intor='cint2e_ip1_sph', aosym='s1', comp=3)
    >>> view('oh2.h5')
    dataset ['eri_mo', 'new'], shape (3, 100, 100)

    >>> ao2mo.general(mol, (mo1,mo1,mo1,mo1), 'oh2.h5', intor='cint2e_ip1_sph', aosym='s2kl', comp=3)
    >>> view('oh2.h5')
    dataset ['eri_mo', 'new'], shape (3, 100, 55)
    '''
    if isinstance(eri_or_mol, numpy.ndarray):
        return incore.general(eri_or_mol, mo_coeffs, *args, **kwargs)
    else:
        if 'intor' in kwargs and ('_sph' not in kwargs['intor']):
            mod = r_outcore
        else:
            mod = outcore
        if len(args) > 0 and isinstance(args[0], (str, h5py.Group)): # args[0] is erifile
            fn = getattr(mod, 'general')
        else:
            fn = getattr(mod, 'general_iofree')
        return fn(eri_or_mol, mo_coeffs, *args, **kwargs)

def kernel(eri_or_mol, mo_coeffs, *args, **kwargs):
    r'''Transfer arbitrary spherical AO integrals to MO integrals, for given
    orbitals or four sets of orbitals.  See also :func:`full` and :func:`kernel`.
    '''
    if isinstance(mo_coeffs, numpy.ndarray) and mo_coeffs.ndim == 2:
        return full(eri_or_mol, mo_coeffs, *args, **kwargs)
    else:
        return general(eri_or_mol, mo_coeffs, *args, **kwargs)


if __name__ == '__main__':
    from pyscf import scf
    from pyscf import gto
    from pyscf.ao2mo import addons
    mol = gto.M(
        verbose = 0,
        atom = [
            ["O" , (0. , 0.     , 0.)],
            [1   , (0. , -0.757 , 0.587)],
            [1   , (0. , 0.757  , 0.587)]],
        basis = 'ccpvdz')

    mf = scf.RHF(mol)
    mf.scf()

    eri0 = full(mf._eri, mf.mo_coeff)
    mos = (mf.mo_coeff,)*4
    print(numpy.allclose(eri0, full(mol, mf.mo_coeff)))
    print(numpy.allclose(eri0, general(mf._eri, mos)))
    print(numpy.allclose(eri0, general(mol, mos)))
    with load(full(mol, mf.mo_coeff, 'h2oeri.h5', dataname='dat1'), 'dat1') as eri1:
        print(numpy.allclose(eri0, eri1))
    with load(general(mol, mos, 'h2oeri.h5', dataname='dat1'), 'dat1') as eri1:
        print(numpy.allclose(eri0, eri1))

