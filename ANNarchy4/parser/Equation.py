"""

    Equation.py

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
from ANNarchy4.core.Global import _warning

from sympy import *
from sympy.parsing.sympy_parser import parse_expr, standard_transformations, convert_xor, auto_number



# Dictionary of built-in symbols or functions
global_dict = {
    'dt' : Symbol('dt_'),
    't' : Symbol('ANNarchy_Global::time'),
    'weight' : Symbol('value_[i]'), 
    'value' : Symbol('value_[i]'), 
    't_spike': Symbol('pre_population_->getLastSpikeTime(rank_[i])'),
    'pos': Function('positive'),
    'positive': Function('positive'), 
    'neg': Function('negative'), 
    'negative': Function('negative'), 
}

# Predefined symbols which must not be declared by the user, but used in the equations
_predefined = ['weight', 'value']

class Equation(object):
    '''
    Class to analyse one equation.
    '''
    def __init__(self, name, expression, variables, 
                 local_variables, global_variables, untouched = [], method='explicit', type=None):
        '''
        Parameters:
        
        * name : The name of the variable
        * expression: The expression as a string
        * variables: a list of all the variables in the neuron/synapse
        * local_variables: a list of the local variables
        * global_variables: a list of the global variables
        * method: the numerical method to use for ODEs
        '''
        # Store attributes
        self.name = name
        self.expression = expression
        self.variables = variables
        self.local_variables = local_variables
        self.global_variables = global_variables
        self.untouched = untouched
        self.method = method
        
        # Determine the type of the equation
        if not type:
            self.type = self.identify_type()
        else:
            self.type = type
        
        # Build the default dictionary for the analysis
        self.local_dict = global_dict
        for var in self.variables: # Add each variable of the neuron
            if var in self.local_variables:
                self.local_dict[var] = Symbol(var+'_[i]')
            elif var in self.global_variables:
                if var in _predefined:
                    continue
                self.local_dict[var] = Symbol(var+'_')
        for var in self.untouched: # Add each untouched variable
            self.local_dict[var] = Symbol(var)
        
    def parse(self):
        if self.type == 'ODE':
            code = self.analyse_ODE(self.expression)
        elif self.type == 'cond':
            code = self.analyse_condition(self.expression)
        elif self.type == 'inc':
            code = self.analyse_increment(self.expression)
        elif self.type == 'return':
            code = self.analyse_return(self.expression)
        elif self.type == 'simple':
            code = self.analyse_assignment(self.expression)
        return code
    
    def identify_type(self):
        """ Identifies which type has the equation:
        
        * inc for "a += 0.2"
        * ODE for "dV/dt + V = A"
        * cond for "mp > 30.0" or "rate != 0.0"
        * simple for the rest, e.g. "rate = pos(mp)" or "baseline = Uniform(0,1)"
        """
        # Suppress spaces to extract dvar/dt
        expression = self.expression.replace(' ', '')
        # Check if it an increment
        for op in ['+=', '-=', '*=', '/=']:
            if op in expression:
                return 'inc'
        # Check if it is an ode
        if 'd'+self.name+'/dt' in expression:
            return 'ODE'
        # Check if it is a condition (e.g spike)
        split_expr = expression.split('=') 
        if len(split_expr) == 1: # no equal sign = treat as condition (return statements will be specified
            return 'cond'
        if split_expr[1] == '': # the first = is followed by another =
            return 'cond'
        for logop in ['<', '>', '!']: # the first operator is <=, >= or !=
            if logop == split_expr[0][-1]:
                return 'cond'
        # Only a simple assignement
        return 'simple'

    
    def c_code(self, equation):
        "Returns the C version of a Sympy expression"
        return ccode(equation, precision=8)#, user_functions=custom_functions)
    
    def parse_expression(self, expression, local_dict):
        " Parses a string with respect to the vocabulary defined in local_dict."
        
        return parse_expr(expression,
            local_dict = local_dict,
            transformations = (standard_transformations + (convert_xor,)) 
                                            # to use ^ for power functions
        )
    
    def analyse_ODE(self, expression):
        " Returns the C++ code corresponding to an ODE with the method defined in self.method"
        # transform the expression to suppress =
        if '=' in expression:
            expression = expression.replace('=', '- (')
            expression += ')'
    
        # Suppress spaces to extract dvar/dt
        expression=expression.replace(' ', '')
    
        if self.method == 'implicit':
            return self.implicit(expression)
        elif self.method == 'explicit':
            return self.explicit(expression)
        elif self.method == 'exponential':
            return self.exponential(expression)
        
    def explicit(self, expression):
        " Explicit or backward Euler numerical method"

        # Add the gradient sympbol
        delta_var = Symbol('d' + self.name)
    
        # Parse the string
        analysed = self.parse_expression(expression,
            local_dict = self.local_dict
        )
    
        # Solve the equation for delta_mp
        explicit_equation = solve(analysed, delta_var)[0].simplify()
    
        # Obtain C code
        explicit_code = self.c_code(self.local_dict[self.name]) + ' += ' \
                        +  self.c_code(explicit_equation) + ';'
    
        # Return result
        return explicit_code
    
    def implicit2(self, expression):
        "Full implicit method, linearising for example (V - E)^2, but this is not desired."
        # Transform the gradient into a difference TODO: more robust...
        expression = expression.replace('d'+self.name, 't_gradient_')
        expression = expression.replace(self.name, 'newval')
        expression = expression.replace('t_gradient_', '(newval - '+self.name+')')

        # Add a sympbol for the next value of the variable
        newval = Symbol('newval')
        self.local_dict['newval'] = newval

        # Parse the string
        analysed = parse_expr(expression,
            local_dict = self.local_dict,
            transformations = (standard_transformations + (convert_xor,))
        )

        # Solve the equation for delta_mp
        explicit_equation = solve(analysed, newval)[0].simplify()
        explicit_equation = simplify(explicit_equation - self.local_dict[self.name])

        # Obtain C code
        explicit_code = self.c_code(self.local_dict[self.name]) + ' += ' +  \
                        self.c_code(explicit_equation) + ';'

        # Return result
        return explicit_code
    
    def implicit(self, expression):
        " Implicit or forward Euler numerical method."
    
        # Standardize the equation
        real_tau, stepsize, steadystate = self.standardize_ODE(expression)
        if real_tau == None: # the equation can not be standardized
            return self.explicit(expression)
    
        instepsize = simplify( stepsize / (stepsize + S(1.0)) )
    
        # Update rule
        explicit_code = self.c_code(self.local_dict[self.name]) + ' += (' + self.c_code(instepsize) + ')*(' \
                        + self.c_code(steadystate)+ ' - ' + self.c_code(self.local_dict[self.name]) +');'
    
        # Return result
        return explicit_code
    
    
    def exponential(self, expression):
        # Standardize the equation
        real_tau, stepsize, steadystate = self.standardize_ODE(expression)
        if real_tau == None: # the equation can not be standardized
            return self.explicit(expression)
    
        # Update rule
        explicit_code = self.c_code(self.local_dict[self.name]) + ' += (1.0 - exp(' \
                        + self.c_code(simplify(-stepsize)) + ')))*(' \
                        + self.c_code(steadystate)+ ' - ' + self.c_code(self.local_dict[self.name]) +');'
    
        # Return result
        return explicit_code
    
    def standardize_ODE(self, expression):
        """ Transform any 1rst order ODE into the standardized form:
    
        tau * dV/dt + V = S
    
        Non-linear functions of V are left in the steady-state argument.
    
        Returns:
    
            * tau : the time constant associated to the standardized equation.
    
            * stepsize: a simplified version of dt/tau.
    
            * steadystate: the right term of the equation after standardization
        """
        # Replace the gradient with a temporary variable
        expression = expression.replace('d' + self.name +'/dt', '_gradvar_') # TODO: robust to spaces
    
        # Add the gradient sympbol
        grad_var = Symbol('_gradvar_')
    
        # Parse the string
        analysed = self.parse_expression(expression,
            local_dict = self.local_dict
        )
    
        # Collect factor on the gradient and main variable A*dV/dt + B*V = C
        expanded = analysed.expand(modulus=None, power_base=False, power_exp=False, 
                                   mul=True, log=False, multinomial=False)
        
        
        # Make sure the expansion went well
        collected_var = collect(expanded, self.local_dict[self.name], evaluate=False, exact=True)
        if self.local_dict[self.name] in collected_var.keys():
            factor_var = collected_var[self.local_dict[self.name]]
        else:
            _warning(self.expression + '\nThe ' + self.method + \
                     ' method is reserved for linear first-order ODEs of the type tau*d'+\
                     self.name+'/dt + '+self.name+' = f(t).\nUsing the explicit method.')
            return None, None, None
            
    
        collected_gradient = collect(expand(analysed, grad_var), grad_var, evaluate=False, exact=True)
        if grad_var in collected_gradient.keys():
            factor_gradient = collected_gradient[grad_var]
        else:
            factor_gradient = S(1.0)
    
        # Real time constant when using the form tau*dV/dt + V = A
        real_tau = factor_gradient / factor_var
    
        # Normalized equation tau*dV/dt + V = A
        normalized = analysed / factor_var
    
        # Steady state A
        steadystate = simplify(real_tau * grad_var + self.local_dict[self.name] - normalized)
    
        # Stepsize
        stepsize = simplify(self.local_dict['dt']/real_tau)
    
        return real_tau, stepsize, steadystate
    
    
    def analyse_condition(self, expression):
        " Analyzes a boolean condition (e.g. for the spike argument)."
                
        # Parse the string
        analysed = self.parse_expression(expression,
            local_dict = self.local_dict
        )
    
        # Obtain C code
        code = self.c_code(simplify(analysed)) 
    
        # Return result
        return code
    
    def analyse_increment(self, expression):
        " Analyzes an incremental assignment (e.g. a += 0.2)."
        
        # Get only the right term
        if '+=' in expression:
            expression = expression[expression.find('+=')+2:]   
            ope = ' += '     
        elif '-=' in expression:
            expression = expression[expression.find('-=')+2:]   
            ope = ' -= '     
        elif '*=' in expression:
            expression = expression[expression.find('*=')+2:]   
            ope = ' *= '     
        elif '/=' in expression:
            expression = expression[expression.find('/=')+2:]   
            ope = ' /= '           
                
        # Parse the string
        analysed = self.parse_expression(expression,
            local_dict = self.local_dict
        )
    
        # Obtain C code
        code = self.c_code(self.local_dict[self.name]) + ope + self.c_code(simplify(analysed)) +';'
    
        # Return result
        return code
    
    def analyse_assignment(self, expression):
        " Analyzes a simple assignment (e.g. a = 0.2)."
        
        # Get only the right term
        expression = expression[expression.find('=')+1:]
                
        # Parse the string
        analysed = self.parse_expression(expression,
            local_dict = self.local_dict
        )
    
        # Obtain C code
        code = self.c_code(self.local_dict[self.name]) + ' = ' + self.c_code(simplify(analysed)) +';'
    
        # Return result
        return code
    
    def analyse_return(self, expression):
        " Analyzes a return statement (e.g. value * pre.rate)."
                
        # Parse the string
        analysed = self.parse_expression(expression,
            local_dict = self.local_dict
        )
    
        # Obtain C code
        code = self.c_code(analysed) +';'
    
        # Return result
        return code
        