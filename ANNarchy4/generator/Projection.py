"""
Projection generator.
"""

from ANNarchy4 import parser
from ANNarchy4.core import Global

class Projection:
    """
    Projection generator class.
    """
    def __init__(self, projection, synapse):
        """
        Projection generator class constructor.
        """
        self.projection = projection
        self.synapse = synapse
        self.parsed_synapse_variables = []
        
        #
        # for each synpase we create an own projection type
        if self.synapse:
            sid   = len(Global.generatedProj_)+1
            name = 'Projection'+str(sid)

            self.h_file = Global.annarchy_dir+'/build/'+name+'.h'
            self.cpp_file = Global.annarchy_dir+'/build/'+name+'.cpp'
            self.pyx = Global.annarchy_dir+'/pyx/'+name+'.pyx'

            Global.generatedProj_.append( { 'name': name, 'ID': sid, 'name': name } )
            self.proj_class = { 'class': 'Projection', 'ID': sid, 'name': name }
            
            synapse_parser = parser.SynapseAnalyser(self.synapse.variables)
            self.parsed_synapse_variables = synapse_parser.parse()

        else:
            self.proj_class = { 'class': 'Projection', 'ID': 0, 'name': 'Projection0' }
            

    def generate_cpp_add(self):
        """
        In case of cpp_stand_alone compilation, this function generates
        the connector calls.
        """
        if self.projection.connector != None:
            return ('net_->connect('+
                str(self.projection.pre.id)+', '+
                str(self.projection.post.id)+', '+
                self.projection.connector.cpp_call() +', '+ 
                str(self.proj_class['ID'])+', '+ 
                str(self.projection.post.generator.targets.index(self.projection.target))+
                ');\n')
        else:
            print '\tWARNING: no connector object provided.'
            return ''

    def generate(self):
        """
        generate projection c++ code.
        """
        def member_def(parsed_variables):
            """
            create variable/parameter header entries.
            """
            code = ''
            for var in parsed_variables:
                if var['name'] in Global.pre_def_synapse:
                    continue
                    
                if var['type'] == 'parameter':
                    code += "\tDATA_TYPE "+var['name']+"_;\n"
                elif var['type'] == 'local':
                    code += "\tstd::vector<DATA_TYPE> "+var['name']+"_;\n"
                else: # global (postsynaptic neurons), or weight bound
                    code += "\tDATA_TYPE "+var['name']+"_;\n"

            return code

        def init(parsed_variables):
            """
            create variable/parameter constructor entries.
            """
            code = ''
            for var in parsed_variables:
                if var['name'] == 'value':
                    continue
                        
                code += "\t"+var['init']+"\n"

            return code
            
        def compute_sum(parsed_variables):
            """
            update the weighted sum code.
            
            TODO: delay mechanism
            """

            #
            # check if 'psp' is contained in variable set
            psp_code = ''
            
            for var in parsed_variables:
                if var['name'] == 'psp':
                    psp_code = var['cpp'].split('=')[1]
                    
            if len(psp_code) > 0:
                code = '''\tDATA_TYPE psp = 0.0;
\tfor(int i=0; i<(int)value_.size();i++) {
\t\tpsp += %(pspCode)s
\t}
\tsum_ = psp;''' % { 'pspCode': psp_code } 
            else:
                code = 'Projection::computeSum();'

            return code
            
        def local_learn(parsed_variables):
            """
            generate synapse update per pre neuron
            """

            code = ''
            loop = ''

            if self.synapse.order == []:
                for var in parsed_variables:
                    if var['name'] == 'psp':
                        continue
                    if var['type'] == 'global':
                        continue

                    if len(var['cpp']) > 0:
                        loop += '\t\t'+var['cpp']+'\n'
                       
            else:
                for var in self.synapse.order:
                    if var == 'psp':
                        continue
                    if var == 'global':
                        continue

                    for var2 in parsed_variables:
                        if var == var2['name']:
                            if len(var2['cpp']) > 0:
                                loop += '\t\t'+var2['cpp']+'\n'
            

            code = '\tfor(int i=0; i<(int)rank_.size();i++) {\n'
            code += loop
            code += '\t}\n'

            return code

        def global_learn(parsed_variables):
            """
            generate synapse update per post neuron
            """
            
            code = ''
            loop = ''
            for var in parsed_variables:
                if var['name'] == 'psp':
                    continue
                if var['type'] == 'local':
                    continue
                
                if len(var['cpp']) > 0:
                    loop += '\t\t'+var['cpp']+'\n'

            code += loop
            return code

        def generate_accessor(synapse_values):
            """
            Creates for all variables/parameters of the synapse the 
            corresponding set and get methods. 
            """
            access = ''
    
            for value in synapse_values:
                if value['name'] in Global.pre_def_synapse:
                    continue
    
                if value['type'] == 'parameter':
                    access += 'void set'+value['name'].capitalize()+'(DATA_TYPE '+value['name']+') { this->'+value['name']+'_='+value['name']+'; }\n\n'
                    access += 'DATA_TYPE get'+value['name'].capitalize()+'() { return this->'+value['name']+'_; }\n\n'
                else:
                    access += 'void set'+value['name'].capitalize()+'(std::vector<DATA_TYPE> '+value['name']+') { this->'+value['name']+'_='+value['name']+'; }\n\n'
                    access += 'std::vector<DATA_TYPE> get'+value['name'].capitalize()+'() { return this->'+value['name']+'_; }\n\n'
                    
            return access

        #
        # generate func body            
        if self.synapse:
            name = self.proj_class['class']+str(self.proj_class['ID'])

            header = '''#ifndef __%(name)s_H__
#define __%(name)s_H__

#include "Global.h"

class %(name)s : public Projection {
public:
%(name)s(Population* pre, Population* post, int postRank, int target);

%(name)s(int preID, int postID, int postRank, int target);

~%(name)s();

void initValues(std::vector<int> rank, std::vector<DATA_TYPE> value, std::vector<int> delay = std::vector<int>());

void computeSum();

void globalLearn();

void localLearn();

%(access)s
private:
%(synapseMember)s
};
#endif
''' % { 'name': name, 
        'access': generate_accessor(self.parsed_synapse_variables),
        'synapseMember': member_def(self.parsed_synapse_variables) }

            body = '''#include "%(name)s.h"
%(name)s::%(name)s(Population* pre, Population* post, int postRank, int target) : Projection(pre, post, postRank, target) {
%(init)s
}

%(name)s::%(name)s(int preID, int postID, int postRank, int target) : Projection(preID, postID, postRank, target) {
%(init)s
}

%(name)s::~%(name)s() {

}

void %(name)s::initValues(std::vector<int> rank, std::vector<DATA_TYPE> value, std::vector<int> delay) {
    Projection::initValues(rank, value, delay);
}

void %(name)s::computeSum() {
%(sum)s
}

void %(name)s::localLearn() {
%(local)s
}

void %(name)s::globalLearn() {
%(global)s
}

''' % { 'name': name, 
        'init': init(self.parsed_synapse_variables), 
        'sum': compute_sum(self.parsed_synapse_variables), 
        'local': local_learn(self.parsed_synapse_variables), 
        'global': global_learn(self.parsed_synapse_variables) }

            with open(self.h_file, mode = 'w') as w_file:
                w_file.write(header)

            with open(self.cpp_file, mode = 'w') as w_file:
                w_file.write(body)
                
            with open(self.pyx, mode = 'w') as w_file:
                w_file.write(self.generate_pyx())            

    def generate_pyx(self):
        """
        Create projection class python extension.
        """
        
        def pyx_func(parsed_synapse):
            """
            function calls to wrap the c++ accessors.
            """
            code = ''
    
            for value in parsed_synapse:
                if value['name'] in Global.pre_def_synapse:
                    continue
   
                if value['type'] == 'parameter':
                    code += '        float get'+value['name'].capitalize()+'()\n\n'
                    code += '        void set'+value['name'].capitalize()+'(float value)\n\n'
                else:
                    code += '        vector[float] get'+value['name'].capitalize()+'()\n\n'
                    code += '        void set'+value['name'].capitalize()+'(vector[float] values)\n\n'
    
            return code
    
        def py_func(parsed_synapse):
            """
            function calls to provide access from python
            to c++ data.
            """            
            code = ''
            
            for value in parsed_synapse:
                if value['name'] in Global.pre_def_synapse:
                    continue
    
                code += '    property '+value['name']+':\n'
                if value['type'] == 'variable':
                    #getter
                    code += '        def __get__(self):\n'
                    code += '            return np.array(self.cInhInstance.get'+value['name'].capitalize()+'())\n\n'
    
                else:
                    #getter
                    code += '        def __get__(self):\n'
                    code += '            return self.cInhInstance.get'+value['name'].capitalize()+'()\n\n'
                
                code += '        def __set__(self, value):\n'
                code += '            self.cInhInstance.set'+value['name'].capitalize()+'(value)\n'
    
            return code
        
        pyx = '''from libcpp.vector cimport vector
from libcpp.string cimport string
import numpy as np

cdef extern from "../build/%(name)s.h":
    cdef cppclass %(name)s:
        %(name)s(int preLayer, int postLayer, int postNeuronRank, int target)

%(cFunction)s

cdef class Local%(name)s(LocalProjection):

    cdef %(name)s* cInhInstance

    def __cinit__(self, proj_type, preID, postID, rank, target):
        self.cInhInstance = <%(name)s*>(createProjInstance().getInstanceOf(proj_type, preID, postID, rank, target))

%(pyFunction)s

''' % { 'name': self.proj_class['name'], 
        'cFunction': pyx_func(self.parsed_synapse_variables), 
        'pyFunction': py_func(self.parsed_synapse_variables) 
    }
        return pyx
