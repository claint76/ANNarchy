# distutils: language = c++

from libcpp.vector cimport vector
import numpy as np
cimport numpy as np

from libc.math cimport exp, fabs

import ANNarchy
from ANNarchy.core import Global
from ANNarchy.core.Random import RandomDistribution

cimport ANNarchy.core.cython_ext.Coordinates as Coordinates

cdef class CSR:

    def __init__(self):
        self.data = {}
        self.delay = {}
        self.max_delay = Global.config['dt']
        self.dt = Global.config['dt']
        self.size = 0
        self.nb_synapses = 0

    def add (self, int rk, list r, list w, list d):
        cdef list val
        val = []
        val.append(r)
        val.append(w)
        self.data[rk] = val
        
        max_d = np.max(d)
        if max_d*self.dt > self.dt:
            self.delay[rk] = d

            if max_d > self.max_delay:
                self.max_delay = max_d
        else:
            self.delay[rk] = []

        self.size += 1
        self.nb_synapses += len(r)

    cdef push_back (self, int rk, vector[int] r, vector[float] w, vector[int] d):
        cdef list val
        val = []
        val.append(r)
        val.append(w)
        self.data[rk] = val

        max_d = np.max(d)
        if max_d*self.dt > self.dt:
            self.delay[rk] = d

            if max_d > self.max_delay:
                self.max_delay = max_d
        else:
            self.delay[rk] = []

        self.size += 1
        self.nb_synapses += len(r)

    def keys(self):
        return self.data.keys()

    cpdef set_delay(self, int rk, vector[int] d):
        self.delay[rk] = d

    cpdef get_data(self):
        return self.data

    cpdef get_delay(self):
        return self.delay

    cpdef get_max_delay(self):
        return self.max_delay

def all_to_all(pre, post, weights, delays, allow_self_connections):
    """ Cython implementation of the all-to-all pattern."""

    cdef CSR projection
    cdef float dt
    cdef int r_post, size_pre, i
    cdef list tmp, post_ranks, pre_ranks
    cdef vector[int] r, d
    cdef vector[float] w

    # Retrieve simulation time step
    dt = Global.config['dt']

    # Retríeve ranks
    if hasattr(post, 'ranks'): # PopulationView
        post_ranks = post.ranks
    else: # Plain population
        post_ranks = range(post.size)
    if hasattr(pre, 'ranks'): # PopulationView
        pre_ranks = pre.ranks
    else:
        pre_ranks = range(pre.size)

    # Create the projection data as CSR
    projection = CSR()

    for r_post in post_ranks:
        # List of pre ranks
        tmp = [i for i  in pre_ranks]
        if not allow_self_connections:
            try:
                tmp.remove(r_post)
            except: # was not in the list
                pass
        r = tmp
        size_pre = len(tmp)
        # Weights
        if isinstance(weights, (int, float)):
            w = vector[float](size_pre, float(weights))
        elif isinstance(weights, RandomDistribution):
            w = weights.get_list_values(size_pre)
        # Delays
        if isinstance(delays, (float, int)):
            d = vector[int](1, int(delays/dt))
        elif isinstance(delays, RandomDistribution):
            d = [int(a/dt) for a in delays.get_list_values(size_pre) ]
        # Create the dendrite
        projection.push_back(r_post, r, w, d)

    return projection

def one_to_one(pre, post, weights, delays):
    """ Cython implementation of the one-to-one pattern."""

    cdef CSR projection
    cdef float dt
    cdef int r_post
    cdef list tmp, post_ranks, pre_ranks
    cdef vector[int] r, d
    cdef vector[float] w

    # Retrieve simulation time step
    dt = Global.config['dt']

    # Retríeve ranks
    if hasattr(post, 'ranks'): # PopulationView
        post_ranks = post.ranks
    else: # Plain population
        post_ranks = range(post.size)
    if hasattr(pre, 'ranks'): # PopulationView
        pre_ranks = pre.ranks
    else:
        pre_ranks = range(pre.size)

    # Create the projection data as CSR
    projection = CSR()

    for r_post in post_ranks:
        # List of pre ranks
        if not r_post in pre_ranks:
            continue
        tmp = [r_post]
        r = tmp
        # Weights
        if isinstance(weights, (int, float)):
            tmp = [float(weights)]
        elif isinstance(weights, RandomDistribution):
            tmp = weights.get_list_values(1)
        w = tmp
        # Delays
        if isinstance(delays, (float, int)):
            tmp = [int(delays/dt)]
        elif isinstance(delays, RandomDistribution):
            tmp = [int(a/dt) for a in delays.get_list_values(1) ]
        d=tmp
        # Create the dendrite
        projection.push_back(r_post, r, w, d)

    return projection



def fixed_probability(pre, post, probability, weights, delays, allow_self_connections):
    """ Cython implementation of the fixed_probability pattern."""

    cdef CSR projection
    cdef float dt
    cdef int r_post, r_pre, size_pre
    cdef list tmp, pre_ranks, post_ranks
    cdef vector[int] r, d
    cdef vector[float] w

    # Retrieve simulation time step
    dt = Global.config['dt']

    # Retríeve ranks
    if hasattr(post, 'ranks'): # PopulationView
        post_ranks = post.ranks
    else: # Plain population
        post_ranks = range(post.size)
    if hasattr(pre, 'ranks'): # PopulationView
        pre_ranks = pre.ranks
    else:
        pre_ranks = range(pre.size)

    # Create the projection data as CSR
    projection = CSR()

    for r_post in post_ranks:
        # List of pre ranks
        tmp = []
        for r_pre in pre_ranks:
            if not allow_self_connections and (r_pre==r_post):
                continue
            if np.random.random() < probability:
                tmp .append(r_pre) 
        r = tmp
        size_pre = len(tmp)
        # Weights
        if isinstance(weights, (int, float)):
            w = vector[float](size_pre, float(weights))
        elif isinstance(weights, RandomDistribution):
            w = weights.get_list_values(size_pre)
        # Delays
        if isinstance(delays, (float, int)):
            d = vector[int](1, int(delays/dt))
        elif isinstance(delays, RandomDistribution):
            d = [int(a/dt) for a in delays.get_list_values(size_pre) ]
        # Create the dendrite
        projection.push_back(r_post, r, w, d)

    return projection

def fixed_number_pre(pre, post, int number, weights, delays, allow_self_connections):
    """ Cython implementation of the fixed_number_pre pattern."""

    cdef CSR projection
    cdef float dt
    cdef int r_post, r_pre, size_pre
    cdef np.ndarray indices, tmp
    cdef list pre_ranks, post_ranks
    cdef vector[int] r, d
    cdef vector[float] w

    # Retrieve simulation time step
    dt = Global.config['dt']
    
    # Retríeve ranks
    if hasattr(post, 'ranks'): # PopulationView
        post_ranks = post.ranks
    else: # Plain population
        post_ranks = range(post.size)
    if hasattr(pre, 'ranks'): # PopulationView
        pre_ranks = pre.ranks
    else:
        pre_ranks = range(pre.size)

    # Create the projection data as CSR
    projection = CSR()
    
    # Array to permute
    indices = np.array(pre_ranks)

    for r_post in post_ranks:
        # List of pre ranks
        indices = np.random.permutation(indices)
        tmp = indices[:number]
        if not allow_self_connections:
            if (tmp == r_post).any(): # the post index is in the list
                tmp[tmp==r_post] = indices[number]
        r = list(tmp)
        # Weights
        if isinstance(weights, (int, float)):
            w = vector[float](number, float(weights))
        elif isinstance(weights, RandomDistribution):
            w = weights.get_list_values(number)
        # Delays
        if isinstance(delays, (float, int)):
            d = vector[int](1, int(delays/dt))
        elif isinstance(delays, RandomDistribution):
            d = [int(a/dt) for a in delays.get_list_values(number) ]
        # Create the dendrite
        projection.push_back(r_post, r, w, d)

    return projection

def fixed_number_post(pre, post, int number, weights, delays, allow_self_connections):
    """ Cython implementation of the fixed_number_post pattern."""

    cdef CSR projection
    cdef float dt
    cdef int r_post, r_pre, size_pre
    cdef np.ndarray indices, tmp
    cdef list pre_ranks, post_ranks
    cdef list rk_mat, pre_r
    cdef vector[int] r, d
    cdef vector[float] w

    # Retrieve simulation time step
    dt = Global.config['dt']
    
    # Retríeve ranks
    if hasattr(post, 'ranks'): # PopulationView
        post_ranks = post.ranks
    else: # Plain population
        post_ranks = range(post.size)
    if hasattr(pre, 'ranks'): # PopulationView
        pre_ranks = pre.ranks
    else:
        pre_ranks = range(pre.size)
    
    # Create the projection data as CSR
    projection = CSR()
    
    # Array to permute
    indices = np.array(post_ranks)

    # Build the backward matrix
    rk_mat = [ [] for i in xrange(post.size)]
    for r_pre in pre_ranks:
        indices = np.random.permutation(indices)
        tmp = indices[:number]
        if not allow_self_connections:
            if (tmp == r_pre).any(): # the post index is in the list
                tmp[tmp==r_pre] = indices[number] # pick the next one
        for i in xrange(number):
            rk_mat[tmp[i]].append(r_pre)

    # Create the dendrites
    for r_post in post_ranks:
        # List of pre ranks
        r = rk_mat[r_post]
        size_pre = len(rk_mat[r_post])
        # Weights
        if isinstance(weights, (int, float)):
            w = vector[float](size_pre, float(weights))
        elif isinstance(weights, RandomDistribution):
            w = weights.get_list_values(size_pre)
        # Delays
        if isinstance(delays, (float, int)):
            d = vector[int](1, int(delays/dt))
        elif isinstance(delays, RandomDistribution):
            d = [int(a/dt) for a in delays.get_list_values(size_pre) ]
        # Create the dendrite
        projection.push_back(r_post, r, w, d)

    return projection

def gaussian(tuple pre_geometry, tuple post_geometry, float amp, float sigma, delays, limit, allow_self_connections):
    """ Cython implementation of the fixed_number_post pattern."""

    cdef CSR projection
    cdef float dt, distance, value
    cdef int post, pre, pre_size, post_size, c, nb_synapses, pre_dim, post_dim
    cdef tuple pre_coord, post_coord
    cdef list ranks, values

    cdef vector[int] r, d
    cdef vector[float] w


    # Retrieve simulation time step
    dt = Global.config['dt']

    # Population sizes
    if isinstance(pre_geometry, int):
        pre_size = pre_geometry
        pre_dim = 1
    else:
        pre_dim = len(pre_geometry)
        pre_size = 1
        for c in pre_geometry:
            pre_size  = pre_size * c
    if isinstance(post_geometry, int):
        post_size = post_geometry
        post_dim = 1
    else:
        post_dim = len(post_geometry)
        post_size = 1
        for c in post_geometry:
            post_size  = post_size * c
    
    # Create the projection data as CSR
    projection = CSR()
    for post in xrange(post_size):
        ranks = []
        values = []
        if post_dim == 1:
            post_coord = (post/float(post_size-1), )
        elif post_dim == 2:
            post_coord = Coordinates.get_normalized_2d_coord(post, post_geometry)
        elif post_dim == 3:
            post_coord = Coordinates.get_normalized_3d_coord(post, post_geometry)
        else:
            post_coord = Coordinates.get_normalized_coord(post, post_geometry)
        for pre in xrange(pre_size):
            if not allow_self_connections and pre==post:
                continue
            if pre_dim == 1:
                pre_coord = (pre/float(pre_size-1), )
                distance = Coordinates.comp_dist1D(pre_coord, post_coord)
            elif pre_dim == 2:
                pre_coord = Coordinates.get_normalized_2d_coord(pre, pre_geometry)
                distance = Coordinates.comp_dist2D(pre_coord, post_coord)
            elif pre_dim == 3:
                pre_coord = Coordinates.get_normalized_3d_coord(pre, pre_geometry)
                distance = Coordinates.comp_dist3D(pre_coord, post_coord)
            else:
                pre_coord = Coordinates.get_normalized_coord(pre, pre_geometry)
                distance = Coordinates.comp_distND(pre_coord, post_coord)
            value = amp * exp(-distance/(2.0*sigma**2))
            if value > limit * amp:
                ranks.append(pre)
                values.append(value)
        nb_synapses = len(ranks)
        r = ranks
        w = values
        if isinstance(delays, (float, int)):
            d = vector[int](1, int(delays/dt))
        elif isinstance(delays, RandomDistribution):
            d = [int(a/dt) for a in delays.get_list_values(nb_synapses) ]
        # Create the dendrite
        projection.push_back(post, r, w, d)

    return projection

def dog(tuple pre_geometry, tuple post_geometry, float amp_pos, float sigma_pos, float amp_neg, float sigma_neg, delays, limit, allow_self_connections):
    """ Cython implementation of the fixed_number_post pattern."""

    cdef CSR projection
    cdef float dt, distance, value
    cdef int post, pre, pre_size, post_size, c, nb_synapses, pre_dim, post_dim
    cdef tuple pre_coord, post_coord
    cdef list ranks, values

    cdef vector[int] r, d
    cdef vector[float] w


    # Retrieve simulation time step
    dt = ANNarchy.core.Global.config['dt']

    # Population sizes
    if isinstance(pre_geometry, int):
        pre_size = pre_geometry
        pre_dim = 1
    else:
        pre_dim = len(pre_geometry)
        pre_size = 1
        for c in pre_geometry:
            pre_size  = pre_size * c
    if isinstance(post_geometry, int):
        post_size = post_geometry
        post_dim = 1
    else:
        post_dim = len(post_geometry)
        post_size = 1
        for c in post_geometry:
            post_size  = post_size * c
    
    # Create the projection data as CSR
    projection = CSR()
    for post in xrange(post_size):
        ranks = []
        values = []
        if post_dim == 1:
            post_coord = (post/float(post_size-1), )
        elif post_dim == 2:
            post_coord = Coordinates.get_normalized_2d_coord(post, post_geometry)
        elif post_dim == 3:
            post_coord = Coordinates.get_normalized_3d_coord(post, post_geometry)
        else:
            post_coord = Coordinates.get_normalized_coord(post, post_geometry)
        for pre in xrange(pre_size):
            if not allow_self_connections and pre==post:
                continue
            if pre_dim == 1:
                pre_coord = (pre/float(pre_size-1), )
                distance = Coordinates.comp_dist1D(pre_coord, post_coord)
            elif pre_dim == 2:
                pre_coord = Coordinates.get_normalized_2d_coord(pre, pre_geometry)
                distance = Coordinates.comp_dist2D(pre_coord, post_coord)
            elif pre_dim == 3:
                pre_coord = Coordinates.get_normalized_3d_coord(pre, pre_geometry)
                distance = Coordinates.comp_dist3D(pre_coord, post_coord)
            else:
                pre_coord = Coordinates.get_normalized_coord(pre, pre_geometry)
                distance = Coordinates.comp_distND(pre_coord, post_coord)
            value = amp_pos * exp(-distance/(2.0*sigma_pos**2)) - amp_neg * exp(-distance/(2.0*sigma_neg**2))
            if fabs(value) > limit * fabs(amp_pos - amp_neg):
                ranks.append(pre)
                values.append(value)
        nb_synapses = len(ranks)
        r = ranks
        w = values
        if isinstance(delays, (float, int)):
            d = vector[int](1, int(delays/dt))
        elif isinstance(delays, RandomDistribution):
            d = [int(a/dt) for a in delays.get_list_values(nb_synapses) ]
        # Create the dendrite
        projection.push_back(post, r, w, d)

    return projection