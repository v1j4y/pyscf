#!/usr/bin/env python
#
# Author: Qiming Sun <osirpt.sun@gmail.com>
#

'''Non-relativistic DFT gradients'''

import time
import numpy
import scipy.linalg
import pyscf.lib
from pyscf.lib import logger
from pyscf.scf import _vhf
from pyscf.scf import rhf_grad
from pyscf.dft import numint


def get_veff_(ks_grad, mol=None, dm=None):
    '''Coulomb + XC functional
    '''
    if mol is None: mol = ks_grad.mol
    if dm is None: dm = ks_grad._scf.make_rdm1()
    t0 = (time.clock(), time.time())

    mf = ks_grad._scf
    if mf.grids.coords is None:
        mf.grids.build_()
    grids = mf.grids
    if mf._numint.non0tab is None:
        mf._numint.non0tab = mf._numint.make_mask(mol, mf.grids.coords)
    hyb = mf._numint.libxc.hybrid_coeff(mf.xc, spin=(mol.spin>0)+1)

    mem_now = pyscf.lib.current_memory()[0]
    max_memory = max(2000, ks_grad.max_memory*.9-mem_now)
    vxc = get_vxc(mf._numint, mol, mf.grids, mf.xc, dm,
                  max_memory=max_memory, verbose=ks_grad.verbose)
    nao = vxc.shape[-1]
    vxc = vxc.reshape(-1,nao,nao)
    t0 = logger.timer(ks_grad, 'vxc', *t0)

    if abs(hyb) < 1e-10:
        vj = ks_grad.get_j(mol, dm)
        vhf = vj
    else:
        vj, vk = ks_grad.get_jk(mol, dm)
        vhf = vj - vk * (hyb * .5)

    return vhf + vxc


def get_vxc(ni, mol, grids, xc_code, dms, relativity=0, hermi=1,
            max_memory=2000, verbose=None):
    if isinstance(relativity, (list, tuple, numpy.ndarray)):
        import warnings
        xc_code = '%s, %s' % (xc_code, dms)
        dms = relativity
        with warnings.catch_warnings():
            warnings.simplefilter("once")
            warnings.warn('API updates: the 5th argument c_id is decoreated '
                          'and will be removed in future release.\n')
    natocc = []
    natorb = []
    if isinstance(dms, numpy.ndarray) and dms.ndim == 2:
        e, c = scipy.linalg.eigh(dms)
        natocc.append(e)
        natorb.append(c)
        nao = dms.shape[0]
    else:
        for dm in dms:
            e, c = scipy.linalg.eigh(dm)
            natocc.append(e)
            natorb.append(c)
        nao = dms[0].shape[0]

    xctype = ni._xc_type(xc_code)
    make_rho, nset, nao = ni._gen_rho_evaluator(mol, dms, hermi)

    nset = len(natocc)
    vmat = numpy.zeros((nset,3,nao,nao))
    if xctype == 'LDA':
        ao_deriv = 1
        for ao, mask, weight, coords \
                in ni.block_loop(mol, grids, nao, ao_deriv, max_memory, ni.non0tab):
            for idm in range(nset):
                rho = make_rho(idm, ao[0], mask, 'LDA')
                vxc = ni.eval_xc(xc_code, rho, 0, relativity, 1, verbose)[1]
                vrho = vxc[0]
                aow = numpy.einsum('pi,p->pi', ao[0], weight*vrho)
                vmat[idm,0] += numint._dot_ao_ao(mol, ao[1], aow, nao, weight.size, mask)
                vmat[idm,1] += numint._dot_ao_ao(mol, ao[2], aow, nao, weight.size, mask)
                vmat[idm,2] += numint._dot_ao_ao(mol, ao[3], aow, nao, weight.size, mask)
                rho = vxc = vrho = aow = None
    elif xctype == 'GGA':
        XX, XY, XZ = 4, 5, 6
        YX, YY, YZ = 5, 7, 8
        ZX, ZY, ZZ = 6, 8, 9
        ao_deriv = 2
        for ao, mask, weight, coords \
                in ni.block_loop(mol, grids, nao, ao_deriv, max_memory, ni.non0tab):
            for idm in range(nset):
                rho = make_rho(idm, ao, mask, 'GGA')
                vxc = ni.eval_xc(xc_code, rho, 0, relativity, 1, verbose)[1]
                vrho, vsigma = vxc[:2]
                wv = numpy.empty_like(rho)
                wv[0]  = weight * vrho
                wv[1:] = rho[1:] * (weight * vsigma * 2)

                aow = numpy.einsum('npi,np->pi', ao[:4], wv)
                vmat[idm,0] += numint._dot_ao_ao(mol, ao[1], aow, nao, weight.size, mask)
                vmat[idm,1] += numint._dot_ao_ao(mol, ao[2], aow, nao, weight.size, mask)
                vmat[idm,2] += numint._dot_ao_ao(mol, ao[3], aow, nao, weight.size, mask)

                aow = numpy.einsum('pi,p->pi', ao[XX], wv[1])
                aow+= numpy.einsum('pi,p->pi', ao[XY], wv[2])
                aow+= numpy.einsum('pi,p->pi', ao[XZ], wv[3])
                vmat[idm,0] += numint._dot_ao_ao(mol, aow, ao[0], nao, weight.size, mask)
                aow = numpy.einsum('pi,p->pi', ao[YX], wv[1])
                aow+= numpy.einsum('pi,p->pi', ao[YY], wv[2])
                aow+= numpy.einsum('pi,p->pi', ao[YZ], wv[3])
                vmat[idm,1] += numint._dot_ao_ao(mol, aow, ao[0], nao, weight.size, mask)
                aow = numpy.einsum('pi,p->pi', ao[ZX], wv[1])
                aow+= numpy.einsum('pi,p->pi', ao[ZY], wv[2])
                aow+= numpy.einsum('pi,p->pi', ao[ZZ], wv[3])
                vmat[idm,2] += numint._dot_ao_ao(mol, aow, ao[0], nao, weight.size, mask)
                rho = vxc = vrho = vsigma = wv = aow = None
    else:
        raise NotImplementedError('meta-GGA')

    if nset == 1:
        vmat = vmat.reshape(3,nao,nao)
    # - sign because nabla_X = -nabla_x
    return -vmat


class Gradients(rhf_grad.Gradients):
    def dump_flags(self):
        rhf_grad.Gradients.dump_flags(self)
        if callable(self._scf.grids.prune):
            logger.info(self, 'Grid pruning %s may affect DFT gradients accuracy.'
                        'Call mf.grids.run(prune=False) to mute grid pruning',
                        self._scf.grids.prune)
        return self

    get_veff = get_veff_


if __name__ == '__main__':
    from pyscf import gto
    from pyscf import dft

    h2o = gto.Mole()
    h2o.verbose = 0
    h2o.output = None#'out_h2o'
    h2o.atom = [
        ['O' , (0. , 0.     , 0)],
        [1   , (0. , -0.757 , 0.587)],
        [1   , (0. ,  0.757 , 0.587)] ]
    h2o.basis = {'H': '631g',
                 'O': '631g',}
    h2o.build()
    mf = dft.RKS(h2o)
    mf.conv_tol = 1e-15
    print(mf.scf())
    g = Gradients(mf)
    print(g.grad())
#[[ -4.20040265e-16  -6.59462771e-16   2.10150467e-02]
# [  1.42178271e-16   2.81979579e-02  -1.05137653e-02]
# [  6.34069238e-17  -2.81979579e-02  -1.05137653e-02]]

    #mf.grids.level = 6
    mf.xc = 'b88,p86'
    print(mf.scf())
    g = Gradients(mf)
    print(g.grad())
#[[ -8.20194970e-16  -2.04319288e-15   2.44405835e-02]
# [  4.36709255e-18   2.73690416e-02  -1.22232039e-02]
# [  3.44483899e-17  -2.73690416e-02  -1.22232039e-02]]

    mf.xc = 'b3lypg'
    print(mf.scf())
    g = Gradients(mf)
    print(g.grad())
#[[ -3.59411142e-16  -2.68753987e-16   1.21557501e-02]
# [  4.04977877e-17   2.11112794e-02  -6.08181640e-03]
# [  1.52600378e-16  -2.11112794e-02  -6.08181640e-03]]


    mol = gto.Mole()
    mol.atom = [
        ['H' , (0. , 0. , 1.804)],
        ['F' , (0. , 0. , 0.   )], ]
    mol.unit = 'B'
    mol.basis = '631g'
    mol.build()

    mf = dft.RKS(mol)
    mf.conv_tol = 1e-15
    mf.kernel()
    print(Gradients(mf).grad())
# sum over z direction non-zero, due to meshgrid response?
#[[ 0  0  -2.68934738e-03]
# [ 0  0   2.69333577e-03]]
    mf = dft.RKS(mol)
    mf.grids.prune = None
    mf.grids.level = 6
    mf.conv_tol = 1e-15
    mf.kernel()
    print(Gradients(mf).grad())
#[[ 0  0  -2.68931547e-03]
# [ 0  0   2.68911282e-03]]

