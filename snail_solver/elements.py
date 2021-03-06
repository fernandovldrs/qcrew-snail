import numpy as np
from scipy.interpolate import approximate_taylor_polynomial
from scipy.optimize import minimize
from snail_solver.helper_functions import *


class SNAIL:
    """
    The SNAIL element is defined as having two nodes connected by two parallel
    branches. One branch has ::n:: josephson junctions with characteristic energies
    :Ej: and the other branch has one junction with energy ::Ej:: scaled by ::alpha::.
    The branches form a loop threaded by a reduced external flux ::phi_ext::.

    Reference: 3-Wave Mixing Josephson Dipole Element (doi: 10.1063/1.4984142)
    """

    def __init__(self, n, alpha, phi_ext, Lj):

        self.Lj = Lj  # Hz
        self.n = n
        self.alpha = alpha
        self.phi_ext = phi_ext  # reduced flux

    def potential(self, phi):
        """
        Normalized potential energy of the josephson junction as a function of the
        reduced flux ::phi:: over the element. Assumes Ej = 1.
        """

        pot_branch1 = -self.alpha * np.cos(phi)
        pot_branch2 = -self.n * np.cos((self.phi_ext - phi) / self.n)

        return pot_branch1 + pot_branch2

    def solve_expansion(self, degree=40, scale=9 * np.pi, order=None):
        """
        Returns the flux of minimum potential and the coefficients of the truncated
        Taylor expansion around the minimum.
        scale is the width of the interval used in the Taylor fit.
        """

        order = order if order else degree + 10

        # Initial guess for potential minimum
        phi_array = np.arange(-np.pi * self.n, np.pi * self.n, 0.01)
        phi_min_0 = min(self.potential(phi) for phi in phi_array)

        # find flux of minimum potential
        phi_min = minimize(self.potential, phi_min_0).x[0]

        # Fit Taylor expansion around minimum
        taylor_potential = approximate_taylor_polynomial(
            self.potential, phi_min, degree, scale, order=order
        )

        # return phi_min, taylor_potential
        a2 = taylor_potential[2]

        Ej = 1 / 2 / (2 * np.pi * hbar * self.Lj * a2) * (flux_quantum / 2 / np.pi) ** 2
        print(Ej)
        print(taylor_potential[3])
        return phi_min, Ej, taylor_potential

    def truncated_potential(
        self,
        degree=40,
        scale=9 * np.pi,
        order=None,
        norm=True,
        shift=True,
        nonlinear=False,
    ):
        """
        Calculates the potential Taylor expansion and reconstructs the potential
        function from the coefficients.
        degree is the order of the cosine expasion.
        norm = True returns potential in units of Ej.
        nonlinear = True returns only the nonlinear part of the potential.
        element scale the (i+3)th term of the taylor expansion of the potential.
        """

        phi_0, Ej, taylor_potential = self.solve_expansion(
            degree=degree, scale=scale, order=order
        )
        phi_0 = phi_0 if shift else 0
        limit = 3 if nonlinear else 0

        a3 = taylor_potential[3]
        a4 = taylor_potential[4]

        def potential(x):
            return sum(
                (1 if norm else Ej)
                * taylor_potential[degree - k]
                * (x - phi_0) ** (degree - k)
                for k in range(len(taylor_potential) + 1 - limit)
            )

        return potential, a3, a4

    def potential_derivative(self, phi):
        """
        Derivative of the snail potential with respect to ::phi::. This function is
        used to analyze if the potential has multiple wells in self.has_multiple_wells
        () method.
        """

        pot_branch1_derivative = self.alpha * np.sin(phi)
        pot_branch2_derivative = -np.sin((self.phi_ext - phi) / self.n)

        return pot_branch1_derivative + pot_branch2_derivative

    @property
    def has_multiple_wells(self):
        """
        Analyzes if the potential has more than one local minimum per period.
        """

        return more_than_2_roots(self.potential_derivative, 0, self.n * 2 * np.pi)


class SNAIL2:
    """
    The SNAIL element is defined as having two nodes connected by two parallel
    branches. One branch has ::n:: josephson junctions with characteristic energies
    :Ej: and the other branch has one junction with energy ::Ej:: scaled by ::alpha::.
    The branches form a loop threaded by a reduced external flux ::phi_ext::.

    Reference: 3-Wave Mixing Josephson Dipole Element (doi: 10.1063/1.4984142)
    """

    def __init__(self, Ej, n, alpha, phi_ext):

        self.Ej = Ej  # Hz
        self.n = n
        self.alpha = alpha
        self.phi_ext = phi_ext  # reduced flux

    def potential(self, phi, norm=True):
        """
        Potential energy of the josephson junction loop as a function of the reduced
        flux ::phi:: over the element. ::norm:: = True normalizes the cosines (Ej = 1).
        """

        pot_branch1 = -self.alpha * np.cos(phi)
        pot_branch2 = -self.n * np.cos((self.phi_ext - phi) / self.n)

        if norm:
            return pot_branch1 + pot_branch2

        return self.Ej * (pot_branch1 + pot_branch2)

    def solve_expansion(self, degree=40, scale=9 * np.pi, order=None, norm=True):
        """
        Returns the flux of minimum potential and the coefficients of the truncated
        Taylor expansion around the minimum.
        scale is the width of the interval used in the Taylor fit.
        """

        order = order if order else degree + 10

        # Initial guess for potential minimum
        phi_array = np.arange(-np.pi * self.n, np.pi * self.n, 0.01)
        phi_min_0 = min(self.potential(phi) for phi in phi_array)

        # find flux of minimum potential
        phi_min = minimize(self.potential, phi_min_0).x[0]

        # Fit Taylor expansion around minimum
        taylor_potential = approximate_taylor_polynomial(
            self.potential, phi_min, degree, scale, order=order
        )

        # return phi_min, taylor_potential
        Ej = 1 if norm else self.Ej

        return phi_min, Ej * taylor_potential

    def inductance(self, degree=40):
        """
        Obtain resonant frequency of the SNAIL shunted by a capacitance C. Also return SNAIL inductance Lj from 2nd order term.
        """

        taylor_expansion = self.solve_expansion(degree=degree, norm=False)[1]
        a2 = taylor_expansion[2]
        # Since self.Ej and consequently a2 are in units of Hz, the Lj expression needs
        # a 2*pi*hbar correction factor.
        Lj = 1 / 2 / (2 * np.pi * hbar * a2) * (flux_quantum / 2 / np.pi) ** 2

        return Lj

    def truncated_potential(
        self,
        degree=40,
        scale=9 * np.pi,
        order=None,
        norm=True,
        shift=True,
        nonlinear=False,
    ):
        """
        Calculates the potential Taylor expansion and reconstructs the potential
        function from the coefficients.
        degree is the order of the cosine expasion.
        norm = True returns potential in units of Ej.
        nonlinear = True returns only the nonlinear part of the potential.
        element scale the (i+3)th term of the taylor expansion of the potential.
        """

        phi_0, taylor_potential = self.solve_expansion(
            degree=degree, scale=scale, order=order, norm=norm
        )
        phi_0 = phi_0 if shift else 0
        limit = 3 if nonlinear else 0

        a3 = taylor_potential[3]
        a4 = taylor_potential[4]

        def potential(x):
            return sum(
                taylor_potential[degree - k] * (x - phi_0) ** (degree - k)
                for k in range(len(taylor_potential) + 1 - limit)
            )

        return potential, a3, a4

    def potential_derivative(self, phi, norm=True):
        """
        Derivative of the snail potential with respect to ::phi::. ::norm:: = True
        normalizes the potential cosines (Ej = 1). This function is used to analyze if
        the potential has multiple wells in self.has_multiple_wells() method.
        """

        pot_branch1_derivative = self.alpha * np.sin(phi)
        pot_branch2_derivative = -np.sin((self.phi_ext - phi) / self.n)

        Ej = 1 if norm else self.Ej

        return Ej * (pot_branch1_derivative + pot_branch2_derivative)

    @property
    def has_multiple_wells(self):
        """
        Analyzes if the potential has more than one local minimum per period.
        """

        return more_than_2_roots(self.potential_derivative, 0, self.n * 2 * np.pi)
