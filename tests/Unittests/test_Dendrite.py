"""

    test_Dendrite.py

    This file is part of ANNarchy.

    Copyright (C) 2013-2016 Joseph Gussev <joseph.gussev@s2012.tu-chemnitz.de>,
    Helge Uelo Dinkelbach <helge.dinkelbach@gmail.com>

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    ANNarchy is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
import unittest
import numpy

from ANNarchy import *

class test_Dendrite(unittest.TestCase):
    """
    This class tests the *Dendrite* object, which gathers all synapses
    belonging to a post-synaptic neuron in a *Projection*:

        * access to parameters
        * the *rank* method
        * the *size* method
    """
    @classmethod
    def setUpClass(self):
        """
        Compile the network for this test
        """
        neuron = Neuron(
            parameters = "tau = 10",
            equations="r += 1/tau * t"
        )

        neuron2 = Neuron(
            parameters = "tau = 10: population",
            equations="r += 1/tau * t: init = 1.0"
        )

        Oja = Synapse(
            parameters="""
                tau = 5000.0 : postsynaptic
                alpha = 8.0
            """,
            equations = """
                tau * dw/dt = pre.r * post.r - alpha * post.r^2 * w
            """
        )

        pop1 = Population(5, neuron)
        pop2 = Population(8, neuron2)

        proj = Projection(
             pre = pop1,
             post = pop2,
             target = "exc",
             synapse = Oja
        )

        proj.connect_all_to_all(weights = 1.0)

        self.test_net = Network()
        self.test_net.add([pop1, pop2, proj])
        self.test_net.compile(silent=True)

        self.net_proj = self.test_net.get(proj)

    def setUp(self):
        """
        In our *setUp()* function we call *reset()* to reset the network.
        """
        self.test_net.reset()

    def test_none(self):
        """
        If a non-existent *Dendrite* is accessed, an error should be thrown.
        This is tested here.
        """
        from ANNarchy.core.Global import ANNarchyException
        with self.assertRaises(ANNarchyException) as cm:
            d = self.net_proj.dendrite(14)
        # self.assertEqual(cm.exception.code, 1)

    def test_pre_ranks(self):
        """
        Tests the *pre_ranks* method, which returns the ranks of the
        pre-synaptic neurons belonging to the accessed *Dendrite*.
        """
        self.assertEqual(self.net_proj.dendrite(5).pre_ranks, [0, 1, 2, 3, 4])

    def test_dendrite_size(self):
        """
        Tests the *size* method, which returns the number of pre-synaptic
        neurons belonging to the accessed *Dendrite*.
        """
        self.assertEqual(self.net_proj.dendrite(3).size, 5)

    def test_get_dendrite_tau(self):
        """
        Tests the direct access of the parameter *tau* of a *Dendrite*.
        """
        self.assertTrue(numpy.allclose(self.net_proj.dendrite(1).tau, 5000.0))

    def test_get_dendrite_alpha(self):
        """
        Tests the direct access of the variable *alpha* of a *Dendrite*.
        """
        self.assertTrue(numpy.allclose(self.net_proj.dendrite(0).alpha, [8.0, 8.0, 8.0, 8.0, 8.0]))

    def test_get_dendrite_weights(self):
        """
        Tests the direct access of the parameter *w* (weights) of a *Dendrite*.
        """
        self.assertTrue(numpy.allclose(self.net_proj.dendrite(7).w, [1.0, 1.0, 1.0, 1.0, 1.0]))

    def test_set_tau(self):
        """
        Tests the setting of the parameter *tau* for the whole *Projection* through a single value.
        """
        self.net_proj.tau = 6000.0
        self.assertTrue(numpy.allclose(self.net_proj.dendrite(0).tau, 6000.0))

    def test_set_alpha(self):
        """
        Tests the setting of the parameter *alpha* of a *Dendrite*.
        """
        self.net_proj.dendrite(4).alpha = 9.0
        self.assertTrue(numpy.allclose(self.net_proj.dendrite(4).alpha, [9.0, 9.0, 9.0, 9.0, 9.0]))

    def test_set_alpha_2(self):
        """
        Tests the setting of the parameter *alpha* of a specific synapse in a *Dendrite*.
        """
        self.net_proj.dendrite(4)[1].alpha = 10.0
        self.assertTrue(numpy.allclose(self.net_proj.dendrite(4).alpha, [9.0, 10.0, 9.0, 9.0, 9.0]))

    def test_set_weights(self):
        """
        Tests the setting of the parameter *w* (weights) of a *Dendrite*.
        """
        self.net_proj.dendrite(6).w = 2.0
        self.assertTrue(numpy.allclose(self.net_proj.dendrite(6).w, [2.0, 2.0, 2.0, 2.0, 2.0]))

    def test_set_weights_2(self):
        """
        Tests the setting of the parameter *w* (weights) of a specific synapse in a *Dendrite*.
        """
        self.net_proj.dendrite(6)[2].w = 3.0
        self.assertTrue(numpy.allclose(self.net_proj.dendrite(6).w, [2.0, 2.0, 3.0, 2.0, 2.0]))
