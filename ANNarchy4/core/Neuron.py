"""
    
    Neuron.py
    
    This file is part of ANNarchy.
    
    Copyright (C) 2013-2016  Julien Vitay <julien.vitay@gmail.com>,
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
from ANNarchy4.core.Global import _error

import pprint

class RateNeuron(object):
    """
    Python definition of a mean rate coded neuron in ANNarchy4. This object is intended to encapsulate neuronal equations and further used in population class.
    """    
    def __init__(self, parameters, equations, extra_values={}, functions=None):
        """ 
        The user describes the initialization of variables / parameters. Neuron parameters are described as Variable object consisting of key - value pairs 
        <name> = <initialization value>. The update rule executed in each simulation step is described as equation.
        
        *Parameters*:
        
            * TODO

        """        
        
        # Store the parameters and equations
        self.parameters = parameters
        self.equations = equations
        self.functions = functions
        

    def __str__(self):
        """
        Customized print.
        """
        return pprint.pformat( self, depth=4 ) 
        
class SpikeNeuron(object):
    """
    Python definition of a mean rate coded neuron in ANNarchy4. This object is intended to encapsulate neuronal equations and further used in population class.
    """    
    def __init__(self, parameters="", equations="", spike=None, reset=None, extra_values={}, functions=None ):
        """ 
        The user describes the initialization of variables / parameters. Neuron parameters are described as Variable object consisting of key - value pairs 
        <name> = <initialization value>. The update rule executed in each simulation step is described as equation.
        
        *Parameters*:
        
            * *parameters*: stored as *key-value pairs*. For example:

                .. code-block:: python
        
                    parameters = \"\"\"
                        a = 0.2
                        b = 2
                        c = -65 
                    \"\"\"

                initializes a parameter ``tau`` with the value 10. Please note, that you may specify several constraints for a parameter:
            
                * *population* : 
                
                * *min*:
                
                * *max*:

            * *equations*: simply as a string contain the equations
            
                .. code-block:: python
        
                    equations = \"\"\"
                        dv/dt = 0.04 * v * v + 5*v + 140 -u + I
                    \"\"\"

                spcifies a variable ``rate`` bases on his excitory inputs.
                
            * *spike*: denotes the conditions when a spike should be emited.

                .. code-block:: python
        
                    spike = \"\"\"
                        v > treshold
                    \"\"\"

            * *reset*: denotes the equations executed after a spike

                .. code-block:: python
        
                    reset = \"\"\"
                        u = u + d
                        v = c
                    \"\"\"
        """        
        
        # Store the parameters and equations
        self.parameters = parameters
        self.equations = equations
        self.functions = functions
        self.spike = spike
        self.reset = reset
        
        
    def __str__(self):
        return pprint.pformat( self, depth=4 )
        
class IndividualNeuron(object):
    """Neuron object returned by the Population.neuron(rank) method.
    
    This only a wrapper around the Population data. It has the same attributes (parameter and variable) as the original population.
    """
    def __init__(self, pop, rank):
        self.__dict__['pop']  = pop
        self.__dict__['rank']  = rank
        self.__dict__['__members__'] = pop.parameters + pop.variables
        self.__dict__['__methods__'] = []
        
    def __getattr__(self, name):
        if name in self.pop.variables:
            return eval('self.pop.cyInstance._get_single_'+name+'(self.rank)')
        elif name in self.pop.parameters:
            return self.pop.__getattribute__(name)
        print('Error: population has no attribute called', name)
        print('Parameters:', self.pop.parameters)
        print('Variables:', self.pop.variables) 
                       
    def __setattr__(self, name, val):
        if hasattr(getattr(self.__class__, name, None), '__set__'):
            return object.__setattr__(self, name, val)
        
        # old version:
        #if name in self.pop.variables:
        #    eval('self.pop.cyInstance._set_single_'+name+'(self.rank, val)')
            
        #TODO: check if this works !!!
        if name in self.pop.variables:
            getattr(self.pop.cyInstance, '_set_single_'+name)(self.rank, val)
        elif name in self.pop.parameters:
            print('Warning: parameters are population-wide, this will affect all other neurons.')
            self.pop.__setattr__(name, val)
            
    def __repr__(self):
        desc = 'Neuron of the population ' + self.pop.name + ' with rank ' + str(self.rank) + ' (coordinates ' + str(self.pop.coordinates_from_rank(self.rank)) + ').\n'
        desc += 'Parameters:\n'
        for param in self.pop.parameters:
            desc += '  ' + param + ' = ' + str(self.__getattr__(param)) + ';'
        desc += '\nVariables:\n'
        for param in self.pop.variables:
            desc += '  ' + param + ' = ' + str(self.__getattr__(param)) + ';'
        return desc
