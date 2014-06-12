# Header for a spike dendrite.
# 
# Depends on:
# 
#     * name : the class name (e.g. Projection1)
#    
#     * access : public access methods for all parameters and variables
#    
#     * global_ops_access : access to the global operations (min, max, mean, etc)
#    
#     * global_ops_method : methods for the global operations (min, max, mean, etc)
#    
#     * member : private definition of parameters and variables    
#    
#     * random : private definition of RandomDistribution arrays  
#    
#     * functions : inline definition of custom functions      
spike_dendrite_header = \
"""#ifndef __%(class)s_H__
#define __%(class)s_H__

#include "Global.h"
#include "Includes.h"
#include "SpikeDendrite.h"

class %(class)s : public SpikeDendrite 
{
public:
    %(class)s(Population* pre, Population* post, int postRank, int target, class SpikeProjection* proj);
    
    %(class)s(int preID, int postID, int postRank, int target, class SpikeProjection* proj);
    
    ~%(class)s();
    
    class Population* getPrePopulation() { return static_cast<Population*>(pre_population_); }

    int getSynapseCount() { return nbSynapses_; }

    int addSynapse(int rank, DATA_TYPE w, int delay);

    int removeSynapse(int rank);
    
    int removeAllSynapses();
    
    void initValues();
    
    void globalLearn();

    void localLearn();

    void preEventPsp(int rank);

    void preEventLearn(int rank);

    void postEvent();
    
    bool isPreSynaptic(Population* pop) { return pop == static_cast<Population*>(pre_population_); }
        
    void record();
    
    void evaluatePreEvent();
    
%(access)s

%(functions)s

private:
%(member)s

%(random)s

    %(pre_name)s* pre_population_;
    %(post_name)s* post_population_;
};
#endif
"""

# Body for a Spike projection
#
# Depends on:
#
#    * class : the class name
#
#    * destructor : code for the destructor where all variables are freed
# 
#    * pre_type : name of class of the presynaptic population
# 
#    * post_type : name of class of the presynaptic population
# 
#    * init : initial values for parameters and variables
# 
#    * local : code for local_learn 
#
#    * global : code for global_learn
#
spike_dendrite_body = \
"""#include "%(class)s.h"        
#include "Global.h"

%(add_include)s

using namespace ANNarchy_Global;
        
%(class)s::%(class)s(Population* pre, Population* post, int postRank, int target, class SpikeProjection* proj) : SpikeDendrite(proj) 
{
    pre_population_ = static_cast<%(pre_type)s*>(pre);
    post_population_ = static_cast<%(post_type)s*>(post);

    target_ = target;
    post_neuron_rank_ = postRank;
    
    post_population_->getProjection(pre, target)->addDendrite(postRank, this);
    pre_population_->addSpikeTarget(this);
}

%(class)s::%(class)s(int preID, int postID, int postRank, int target, class SpikeProjection* proj) : SpikeDendrite(proj) 
{
    pre_population_ = static_cast<%(pre_type)s*>(Network::instance()->getPopulation(preID));
    post_population_ = static_cast<%(post_type)s*>(Network::instance()->getPopulation(postID));

    target_ = target;
    post_neuron_rank_ = postRank;
    
    post_population_->getProjection(pre_population_, target)->addDendrite(postRank, this);
    pre_population_->addSpikeTarget(this);
}

%(class)s::~%(class)s() 
{
#ifdef _DEBUG
    std::cout<<"%(class)s::Destructor"<<std::endl;
#endif

%(destructor)s
}

int %(class)s::addSynapse(int rank, DATA_TYPE w, int delay)
{
%(add_synapse_body)s
}

int %(class)s::removeSynapse(int rank)
{
%(rem_synapse_body)s
}

int %(class)s::removeAllSynapses()
{
%(rem_all_synapse_body)s
}

void %(class)s::initValues() 
{
%(init)s
}

void %(class)s::localLearn() {
%(local)s
}

void %(class)s::globalLearn() {
%(global)s
}

void %(class)s::record() 
{
%(record)s
}

void %(class)s::postEvent() 
{
%(post_event)s
}


void %(class)s::evaluatePreEvent()
{
    if ( pre_spikes_.size() > 0 )
    {
    #ifdef _DEBUG
        #pragma omp master
        {
            std::cout << "t = " << ANNarchy_Global::time << ", n = "<< post_neuron_rank_ << ": " << pre_spikes_.size() << " presynaptic event(s)." << std::endl;
            std::cout << "[";
            for (auto it = pre_spikes_.begin(); it != pre_spikes_.end(); it++)
                std::cout << *it << ", ";
            std::cout << "]"<< std::endl;
        }
    #endif

        for ( int n = 0; n < pre_spikes_.size(); n++)
        {
            int i = pre_spikes_[n];
            
            %(pre_event_psp)s            
        }
        
        if ( isLearning() && !post_population_->hasSpiked(post_neuron_rank_) )
        {
            for ( int n = 0; n < pre_spikes_.size(); n++)
            {
                int i = pre_spikes_[n];
                %(pre_event_learn)s
            }
        }
    }

    pre_spikes_.clear();
}
"""