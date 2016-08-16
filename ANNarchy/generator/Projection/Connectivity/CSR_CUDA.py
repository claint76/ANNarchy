"""
This file contains all template codes to represent the connectivity as a
compressed sparse row and column data structure.

Please remember, that the interface to the PyExtension remains as a
list of list data structure.

All templates are gathered in a dictionary called conn_templates,
which should be used in CUDAGenerator or CUDAConnectivity.
"""
connectivity_matrix = {
    'declare': """
    // Connectivity (LIL)
    std::vector<int> post_rank ;
    std::vector< std::vector< int > > pre_rank ;

    // CSR
    int overallSynapses;
    std::vector<int> row_ptr;
    int *gpu_row_ptr;
    int* gpu_pre_rank;
""",
   'accessor': """
    // Accessor to connectivity data
    std::vector<int> get_post_rank() { return post_rank; }
    void set_post_rank(std::vector<int> ranks) { post_rank = ranks; }
    std::vector< std::vector<int> > get_pre_rank() { return pre_rank; }
    void set_pre_rank(std::vector< std::vector<int> > ranks) { pre_rank = ranks; }
    int nb_synapses(int n) { return pre_rank[n].size(); }
""",
   'init': """
        // row_ptr and overallSynapses
        genRowPtr();
    #ifdef _DEBUG_CONN
        std::cout << "Post to Pre:" << std::endl;
        for(int i = 0; i < pop%(id_post)s.size; i++) {
            std::cout << i << ": " << row_ptr[i] << " -> "<< row_ptr[i+1] << std::endl;
        }
    #endif
        cudaMalloc((void**)&gpu_row_ptr, row_ptr.size()*sizeof(int));
        cudaMemcpy(gpu_row_ptr, row_ptr.data(), row_ptr.size()*sizeof(int), cudaMemcpyHostToDevice);

        // pre ranks
        std::vector<int> flat_pre_rank = flattenArray<int>(pre_rank);
        cudaMalloc((void**)&gpu_pre_rank, flat_pre_rank.size()*sizeof(int));
        cudaMemcpy(gpu_pre_rank, flat_pre_rank.data(), flat_pre_rank.size()*sizeof(int), cudaMemcpyHostToDevice);
""",
    'pyx_struct': """
        vector[int] get_post_rank()
        vector[vector[int]] get_pre_rank()
        void set_post_rank(vector[int])
        void set_pre_rank(vector[vector[int]])
        # void inverse_connectivity_matrix()
""",
    'pyx_wrapper_args': " synapses",
    'pyx_wrapper_init': """
        cdef CSR syn = synapses
        cdef int size = syn.size
        cdef int nb_post = syn.post_rank.size()
        proj%(id_proj)s.set_size( size )
        proj%(id_proj)s.set_post_rank( syn.post_rank )
        proj%(id_proj)s.set_pre_rank( syn.pre_rank )
""",
    'pyx_wrapper_accessor': """
    def post_rank(self):
        return proj%(id_proj)s.get_post_rank()
    def set_post_rank(self, val):
        proj%(id_proj)s.set_post_rank(val)
        # proj%(id_proj)s.inverse_connectivity_matrix() # TODO: spike only
    def pre_rank(self, int n):
        return proj%(id_proj)s.get_pre_rank()[n]
    def pre_rank_all(self):
        return proj%(id_proj)s.get_pre_rank()
    def set_pre_rank(self, val):
        proj%(id_proj)s.set_pre_rank(val)
        # proj%(id_proj)s.inverse_connectivity_matrix() ' TODO: spike only'
""",
}

weight_matrix = {
    'declare': """
    // Local variable w
    std::vector<std::vector<double> > w;
    double *gpu_w;
    bool w_dirty;
    """,
    'accessor': """
    // Local variable w
    std::vector<std::vector< double > > get_w() { return w; }
    std::vector<double> get_dendrite_w(int rk) { return w[rk]; }
    double get_synapse_w(int rk_post, int rk_pre) { return w[rk_post][rk_pre]; }
    void set_w(std::vector<std::vector< double > >value) { w = value; w_dirty = true; }
    void set_dendrite_w(int rk, std::vector<double> value) { w[rk] = value; w_dirty = true; }
    void set_synapse_w(int rk_post, int rk_pre, double value) { w[rk_post][rk_pre] = value; w_dirty = true; }
    """,
    'init': """
        // weights
        cudaMalloc((void**)&gpu_w, overallSynapses * sizeof(double));
        w_dirty = true; // enforce update
        cudaError_t err_w = cudaGetLastError();
        if ( err_w != cudaSuccess )
            std::cout << cudaGetErrorString(err_w) << std::endl;
""",
    'pyx_struct': """
        vector[ vector[ double] ] get_w()
        vector[ double ] get_dendrite_w(int)
        double get_synapse_w(int, int)
        void set_w(vector[ vector[ double] ])
        void set_dendrite_w( int, vector[double])
        void set_synapse_w(int, int, double)
    """,
    'pyx_wrapper_args': "",
    'pyx_wrapper_init': """
        proj%(id_proj)s.set_w(syn.w)
    """,
    'pyx_wrapper_accessor': """
    # Local variable w
    def get_w(self):
        return proj%(id_proj)s.get_w()
    def set_w(self, value):
        proj%(id_proj)s.set_w( value )
    def get_dendrite_w(self, int rank):
        return proj%(id_proj)s.get_dendrite_w(rank)
    def set_dendrite_w(self, int rank, vector[double] value):
        proj%(id_proj)s.set_dendrite_w(rank, value)
    def get_synapse_w(self, int rank_post, int rank_pre):
        return proj%(id_proj)s.get_synapse_w(rank_post, rank_pre)
    def set_synapse_w(self, int rank_post, int rank_pre, double value):
        proj%(id_proj)s.set_synapse_w(rank_post, rank_pre, value)
"""
}

inverse_connectivity_matrix = {
    'declare': """
    // Inverse connectivity, only on gpu
    int* gpu_col_ptr;
    int* gpu_row_idx;
    int* gpu_inv_idx;
""",
    'init': """
        //
        // 2-pass algorithm: 1st we compute the inverse connectivity as LIL, 2ndly transform it to CSR
        //
        std::vector< std::vector< int > > pre_to_post_rank = std::vector< std::vector< int > >(pop%(id_pre)s.size, std::vector<int>());
        std::vector< std::vector< int > > pre_to_post_idx = std::vector< std::vector< int > >(pop%(id_pre)s.size, std::vector<int>());

        // some iterator definitions we need
        typename std::vector<std::vector<int> >::iterator pre_rank_out_it = pre_rank.begin();  // 1st level iterator
        typename std::vector<int>::iterator pre_rank_in_it;                                    // 2nd level iterator
        typename std::vector< int >::iterator post_rank_it = post_rank.begin();

        // iterate over post neurons, post_rank_it encodes the current rank
        for( ; pre_rank_out_it != pre_rank.end(); pre_rank_out_it++, post_rank_it++ ) {

            int syn_idx = row_ptr[*post_rank_it]; // start point of the flattened array, post-side
            // iterate over synapses, update both result containers
            for( pre_rank_in_it = pre_rank_out_it->begin(); pre_rank_in_it != pre_rank_out_it->end(); pre_rank_in_it++) {
                //std::cout << *pre_rank_in_it << "->" << *post_rank_it << ": " << syn_idx << std::endl;
                pre_to_post_rank[*pre_rank_in_it].push_back(*post_rank_it);
                pre_to_post_idx[*pre_rank_in_it].push_back(syn_idx);
                syn_idx++;
            }
        }

        std::vector<int> col_ptr = std::vector<int>( pop%(id_pre)s.size, 0 );
        int curr_off = 0;
        for ( int i = 0; i < pop%(id_pre)s.size; i++) {
            col_ptr[i] = curr_off;
            curr_off += pre_to_post_rank[i].size();
        }
        col_ptr.push_back(curr_off);

    #ifdef _DEBUG_CONN
        std::cout << "Pre to Post:" << std::endl;
        for ( int i = 0; i < pop%(id_pre)s.size; i++ ) {
            std::cout << i << ": " << col_ptr[i] << " -> " << col_ptr[i+1] << std::endl;
        }
    #endif

        cudaMalloc((void**)&gpu_col_ptr, col_ptr.size()*sizeof(int));
        cudaMemcpy(gpu_col_ptr, col_ptr.data(), col_ptr.size()*sizeof(int), cudaMemcpyHostToDevice);

        std::vector<int> row_idx = flattenArray(pre_to_post_rank);
        cudaMalloc((void**)&gpu_row_idx, row_idx.size()*sizeof(int));
        cudaMemcpy(gpu_row_idx, row_idx.data(), row_idx.size()*sizeof(int), cudaMemcpyHostToDevice);

        std::vector<int> inv_idx = flattenArray(pre_to_post_idx);
        cudaMalloc((void**)&gpu_inv_idx, inv_idx.size()*sizeof(int));
        cudaMemcpy(gpu_inv_idx, inv_idx.data(), inv_idx.size()*sizeof(int), cudaMemcpyHostToDevice);
"""
}

attribute_decl = {
    'local':
"""
    // Local %(attr_type)s %(name)s
    std::vector< std::vector<%(type)s > > %(name)s;
    %(type)s* gpu_%(name)s;
    bool %(name)s_dirty;
""",
    'global':
"""
    // Global %(attr_type)s %(name)s
    std::vector< %(type)s >  %(name)s ;
    %(type)s* gpu_%(name)s;
    bool %(name)s_dirty;
"""
}

attribute_acc = {
    'local':
"""
    // Local %(attr_type)s %(name)s
    std::vector<std::vector< %(type)s > > get_%(name)s() { return %(name)s; }
    std::vector<%(type)s> get_dendrite_%(name)s(int rk) { return %(name)s[rk]; }
    %(type)s get_synapse_%(name)s(int rk_post, int rk_pre) { return %(name)s[rk_post][rk_pre]; }
    void set_%(name)s(std::vector<std::vector< %(type)s > >value) { %(name)s = value; %(name)s_dirty = true; }
    void set_dendrite_%(name)s(int rk, std::vector<%(type)s> value) { %(name)s[rk] = value; %(name)s_dirty = true; }
    void set_synapse_%(name)s(int rk_post, int rk_pre, %(type)s value) { %(name)s[rk_post][rk_pre] = value; %(name)s_dirty = true; }
""",
    'global':
"""
    // Global %(attr_type)s %(name)s
    std::vector<%(type)s> get_%(name)s() { return %(name)s; }
    %(type)s get_dendrite_%(name)s(int rk) { return %(name)s[rk]; }
    void set_%(name)s(std::vector<%(type)s> value) { %(name)s = value; }
    void set_dendrite_%(name)s(int rk, %(type)s value) { %(name)s[rk] = value; }
"""
}

attribute_cpp_init = {
    'local':
"""
        // Local %(attr_type)s %(name)s
        %(name)s = std::vector< std::vector<%(type)s> >(post_rank.size(), std::vector<%(type)s>());
        cudaMalloc((void**)&gpu_%(name)s, overallSynapses * sizeof(%(type)s));
        %(name)s_dirty = true;
""",
    'global':
"""
        // Global %(attr_type)s %(name)s
        %(name)s = std::vector<%(type)s>(post_rank.size(), %(init)s);
        cudaMalloc((void**)&gpu_%(name)s, post_rank.size() * sizeof(%(type)s));
        %(name)s_dirty = true;
"""
}

delay = {
    'declare': """
    // Non-uniform delay
    std::vector< std::vector< int > > delay ;""",
    'pyx_struct':
"""
        # Non-uniform delay
        vector[vector[int]] delay""",
    'pyx_wrapper_init':
"""
        proj%(id_proj)s.delay = syn.delay""",
    'pyx_wrapper_accessor':
"""
    # Access to non-uniform delay
    def get_delay(self):
        return proj%(id_proj)s.delay
    def get_dendrite_delay(self, idx):
        return proj%(id_proj)s.delay[idx]
    def set_delay(self, value):
        proj%(id_proj)s.delay = value
"""
}

event_driven = {
    'declare': """
    std::vector<std::vector<long> > _last_event;
    long* gpu_last_event;
    void update_gpu_last_event() {
        std::vector<long> tmp =flattenArray<long>(_last_event);
        cudaMalloc((void**)&gpu_last_event, sizeof(long)*tmp.size());
        cudaMemcpy(gpu_last_event, tmp.data(), sizeof(long)*tmp.size(), cudaMemcpyHostToDevice);
        tmp.clear();
    }
""",
    'cpp_init': """
""",
    'pyx_struct': """
        vector[vector[long]] _last_event
        void update_gpu_last_event()
""",
    'pyx_wrapper_init':
"""
        proj%(id_proj)s._last_event = vector[vector[long]](nb_post, vector[long]())
        for n in range(nb_post):
            proj%(id_proj)s._last_event[n] = vector[long](proj%(id_proj)s.nb_synapses(n), -10000)
        proj%(id_proj)s.update_gpu_last_event()
"""
}

conn_templates = {
    # connectivity
    'connectivity_matrix': connectivity_matrix,
    'inverse_connectivity_matrix': inverse_connectivity_matrix,
    'weight_matrix': weight_matrix,
    'single_weight_matrix': None,
    
    # accessors
    'attribute_decl': attribute_decl,
    'attribute_acc':attribute_acc,
    'attribute_cpp_init': attribute_cpp_init,
    'delay': delay,
    'event_driven': event_driven
}