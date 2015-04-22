from ANNarchy import *
from time import time

# ###########################################
# Configuration
# ###########################################
setup(dt=0.1)

# ###########################################
# Parameters
# ###########################################
N = 12500 # Total number of neurons
NE = 10000 # Number of excitatory neurons
Nrec = 1000 # Number of neurons to record
J_ex  = 0.1 # excitatory weight
J_in  = -0.5 # inhibitory weight
p_rate = 20. # external Poisson rate
delay = 1.5 # synaptic delay
simtime = 100.0 # simulation duration

# ###########################################
# Neuron model
# ###########################################
IAF = Neuron(
    parameters="""
        v_th = 20.0 : population
        tau_m = 20.0 : population
    """,
    equations="""
        # The real equation should be:
        # tau_m * dv/dt = -v + g_exc + g_inh
        # But incoming spikes increment the membrane potential directly
        # So we apply the numerical method by hand
        v += g_exc + g_inh - dt*v/tau_m
    """,
    spike="v > v_th",
    reset="v = 0.0",
    refractory=2.0
)


# ###########################################
# Populations
# ###########################################
P = Population(geometry=N, neuron=IAF)
PE = P[:10000]
PI = P[10000:]
poisson = PoissonPopulation(geometry=NE, rates=p_rate)

# ###########################################
# Projections
# ###########################################
ee = Projection(PE, P, 'exc').connect_fixed_number_pre(number=NE/10, weights=J_ex, delays=delay)
ii = Projection(PI, P, 'inh').connect_fixed_number_pre(number=(N-NE)/10, weights=J_in, delays=delay)
noise = Projection(poisson, P, 'exc').connect_fixed_number_pre(number=NE/10, weights=J_ex, delays=delay)

compile()

# ###########################################
# Simulation
# ###########################################
print 'Start simulation'
P.start_record(['spike'])
simulate(simtime, measure_time=True)
data = P.get_record()

# ###########################################
# Data analysis
# ###########################################
spikes = raster_plot(data['spike'])
print 'Mean firing rate:', len(spikes)/float(N)*1000./simtime, 'Hz'
from pylab import *
plot(0.1*spikes[:, 0], spikes[:, 1], '.')
ylim(0, Nrec)
show()
