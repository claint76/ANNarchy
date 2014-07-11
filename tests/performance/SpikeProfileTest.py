#
#   ANNarchy - SimpleSTDP
#
#   A simple model showing the STDP learning on a single neuron.
# 
#   Model adapted from Song, Miller and Abbott (2000) and Song and Abbott (2001)
#
#   Code adapted from the Brian example: https://brian2.readthedocs.org/en/latest/examples/synapses_STDP.html
#
#   authors: Helge Uelo Dinkelbach, Julien Vitay
#
from ANNarchy import *
from ANNarchy.extensions.Profile import *

# Parameters
dt = 1.0 # Time step
F = 15.0 # Poisson distribution at 15 Hz
N = 1000 # 1000 Poisson inputs
gmax = 0.01 # Maximum weight
duration = 100000.0 # Simulation for 100 seconds

# Definition of the neuron
IF = SpikeNeuron(
    parameters = """
        tau_m = 10.0 
        tau_e = 5.0 
        vt = -54.0 
        vr = -60.0 
        El = -74.0 
        Ee = 0.0 
    """,
    equations = """
        tau_m * dv/dt = El - v + g_exc * (Ee - vr) : init = -60.0
        tau_e * dg_exc/dt = -g_exc
    """,
    spike = """
        v > vt
    """,
    reset = """
        v = vr
    """
)
 
# Definition of the STDP learning rule
STDP = SpikeSynapse(
    parameters="""
        tau_pre = 20.0 : postsynaptic
        tau_post = 20.0 : postsynaptic
        cApre = 0.01 : postsynaptic
        cApost = -0.0105 : postsynaptic
        wmax = 0.01 : postsynaptic
    """,
    equations = """
        tau_pre * dApre/dt = -Apre : init=0.0
        tau_post * dApost/dt = -Apost : init=0.0
    """,
    pre_spike="""
        g_target += w
        Apre += cApre * wmax
        w = clip(w + Apost, 0.0 , wmax)
    """,                  
    post_spike="""
        Apost += cApost * wmax
        w = clip(w + Apre, 0.0 , wmax)
    """
)

# Input population
Input = PoissonPopulation(name = 'Input', geometry=N, rates=F)
# Output neuron
Output = Population(name = 'Output', geometry=10, neuron=IF)
# Projection learned using STDP
proj = Projection( 
    pre = Input, 
    post = Output, 
    target = 'exc',
    synapse = STDP
)
proj.connect_all_to_all(weights=Uniform(0.0, gmax))


if __name__ == '__main__':

    # Compile the network
    compile()

    profiler = SpikeProfile([1,2,3,4], 10, 'profile_spike', 'tests')
    profiler.add_to_profile(MagicNetwork())

    profiler.measure_func(simulate, 1)

    profiler.analyse_data()
    
    profiler.visualize_data()
    
    profiler.print_data()
    
    raw_input()