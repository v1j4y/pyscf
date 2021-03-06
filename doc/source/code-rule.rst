.. _code_stand:


Code standard
*************

* New features first being placed in pyscf/future.

* Code at least should work under python-2.7, gcc-4.8.

* 90/10 functional/OOP, unless performance critical, functions are pure.

* 90/10 Python/C, only computational hot spots were written in C.

* To extend python function with C/Fortran:

  - Following C89 standard for C code.  (complex? variable length array?)
    http://flash-gordon.me.uk/ansi.c.txt

  - Following Fortran 95 standard for Fortran code.
    http://j3-fortran.org/doc/standing/archive/007/97-007r2/pdf/97-007r2.pdf

  - Do **not** use other program languages (to keep the package light-weight).

* Loose-coupling principle

  - Reinventing-wheel is accepted (to reduce the entanglement to the
    rest of the package).

* Not enforced but recommended
  - Compatibile with Python 2.6, 2.7, 3.2, 3.3, 3.4;
  - Following C89 standard for C code;
  - Using ctypes to bridge C/python functions, (to keep minimal dependence on third-party tools)


Name rules
----------

* The prefix or suffix underscore in the function names have special meanings

  - functions with prefix-underscore like ``_fn`` are private functions.
    They are typically not documented, and not recommended to use.

  - functions with suffix-underscore like ``fn_`` means that they have side
    effects.  The side effects include the change of the input argument,
    the runtime modification of the class definitions (attributes or
    members), or module definitions (global variables or functions) etc.

  - regular (pure) functions do not have underscore as the prefix or suffix.

API rules
---------

* :class:`gto.Mole` holds all global parameters, like the log level, the
  max memory usage etc.  They are used as the default value for all
  other classes.

* Method class.

  - Most QC method classes (like HF, CASSCF, FCI, ...) directly take
    three attributes ``verbose``, ``stdout`` and ``max_memory`` from
    :class:`gto.Mole`.  Overwriting them only affects the behavior of the
    local instance for that method class.  In the following example,
    ``mf.verbose`` screens out the noises produced by :class:`RHF`
    method, and the output of :class:`MP2` is written in the log file
    ``example.log``::

    >>> from pyscf import gto, scf, mp
    >>> mol = gto.M(atom='H 0 0 0; H 0 0 1', verbose=5)
    >>> mf = scf.RHF(mol)
    >>> mf.verbose = 0
    >>> mf.kernel()
    >>> mp2 = mp.MP2(mf)
    >>> mp2.stdout = open('example.log', 'w')
    >>> mp2.kernel()

  - Method class are only to hold the options or enviroments (like
    convergence threshold, max iterations, ...) to control the
    behavior/convergence of the method.  The intermediate status are
    **not** supposed to be saved in the method class (during the
    computation).  However, the final results or solutions are kept in
    the method object for convenience.  Once the results are stored in
    the particular method class, they are assumed to be read only, since
    many class member functions take them as the default arguments if the
    caller didn't provide enough parameters.

  - In __init__ function, initialize/define the problem size.  The
    problem size parameters (like num orbitals etc) can be considered as
    enviroments.  They are not supposed to be changed by other functions.

  - Kernel functions
    Although the method classes have various entrance/main funtion, many
    of them provide an entrance function called ``kernel``.  You can
    simply call the ``kernel`` function and it will guide the program
    flow to the right main function.

  - Default value of the class member functions' arguments.  Many member
    functions can take the results of their class as the default arguments.

* Function arguments

  - First argument is handler.  The handler is one of :class:`gto.Mole`
    object, a mean-field object, or a post-Hartree-Fock object.

..  - When any of the three parmeters ``mo_energy``, ``mo_coeff`` and
      ``mo_occ`` are appeared in the argument lists,  they are always put
      in this order: ``mo_energy, mo_coeff, mo_occ``.


