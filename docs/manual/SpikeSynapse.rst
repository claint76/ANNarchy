***********************************
Spike synapses
***********************************

Synapses in spiking networks differ from rate-coded synapses in that they are event-driven, i.e. the most important changes occur whenever a pre- or post-synaptic spike is emitted. For this reason, additional arguments have to be passed to the ``Synapse`` object.
   
Increase of conductance after a presynaptic spike
==================================================

In the simplest case, a presynaptic spike increases a ``target`` conductance value in the postsynaptic neuron. The rule defining how this conductance is modified has to be placed in the ``pre_spike`` argument of a ``Synapse`` object.

The default spiking synapse in ANNarchy is equivalent to:

.. code-block:: python

    DefaultSynapse = Synapse(
        parameters = "",
        equations = "",
        pre_spike = """
            g_target += w
        """     
    ) 

The only thing it does is to increase the conductance ``g_target`` of the postsynaptic neuron (for example ``g_exc`` if the target is ``exc``) every time a pre-syanptic spike arrives at the synapse, proportionally to the synaptic efficiency ``w`` of the synapse. 

You can override this default behavior by providing a new ``Synapse`` object when building a ``Projection``. For example, you may want to implement a "fatigue" mechanism for the synapse, transciently reducing the synaptic efficiency when the pre-synaptic neuron fires too strongly. One solution would be to decrease a synaptic variable everytime a pre-synaptic spike  is received and increase the post-synaptic conductance proportionally to this value. When no spike is received, this ``trace`` variable should slowly return to its maximal value.

.. code-block:: python

    FatigueSynapse = Synapse(
        parameters = """
            tau = 1000 : postsynaptic # Time constant of the trace is 1 second
            dec = 0.05 : postsynaptic # Decrement of the trace
        """,
        equations = """
            tau * dtrace/dt + trace = 1.0 : min = 0.0
        """,
        pre_spike = """
            g_target += w * trace
            trace -= dec
        """     
    ) 
   
Each time a pre-synaptic spike occurs, the postsynaptic conductance is increased from ``w*trace``. As the baseline of ``trace`` is 1.0 (as defined in ``equations``), this means that a "fresh" synapse will use the full synaptic efficiency. However, after each pre-synaptic spike, trace is decreased from ``dec = 0.05``, meaning that the "real" synaptic efficiency can go down to 0.0 (the minimal value of trace) if the pre-synaptic neuron fires too much.

It is important here to restrict ``trace`` to positive values with the flags ``min=0.0``, as it could otherwise transform an excitatory synapse into an inhibitory one...

.. hint:: 

    It is obligatory to use the keyword ``g_target`` for the post-synaptic conductance. This value relates to the corresponding value in postsynaptic neuron: The ``target`` will be replaced with the projection's target (for example ``exc`` or ``inh``). So if you use this synapse in a projection with target = 'exc', the value of g_exc in postsynaptic neuron will be automatically replaced. 

.. note::

    The ``psp`` argument will be ignored in a spiking network.

Synaptic plasticity
==========================

In spiking networks, there are usually two ways to implement synaptic plasticity (see the entry on STDP at `Scholarpedia <http://www.scholarpedia.org/article/Spike-timing_dependent_plasticity>`_):

* by using the difference in spike times between the pre- and post-synaptic neurons;
* by using online implementations.


Using spike-time differences
-----------------------------

A ``Synapse`` has access to two specific variables:

* ``t_pre`` corresponding to the time of the *last* pre-synaptic spike in milliseconds.

* ``t_post`` corresponding to the time of the *last* post-synaptic spike in milliseconds.
  
These times are relative to the creation of the network, so they only make sense when compared to each other or to ``t``.

Spike-timing dependent plasticity can for example be implemented the following way:

.. code-block:: python


    STDP = Synapse(
        parameters = """
            tau_pre = 10.0 : postsynaptic
            tau_post = 10.0 : postsynaptic
            cApre = 0.01 : postsynaptic
            cApost = 0.0105 : postsynaptic
            wmax = 0.01 : postsynaptic
        """,
        pre_spike = """
            g_target += w
            w = clip(w - cApost * exp((t_post - t)/tau_post) , 0.0 , wmax) 
        """,                  
        post_spike = """
            w = clip(w + cApre * exp((t_pre - t)/tau_pre) , 0.0 , wmax)
        """      
    ) 

* Every time a pre-synaptic spike arrives at the synapse (``pre_spike``), the postsynaptic conductance is increased from the current value of the synaptic efficiency. 

.. code-block:: python
    
    g_target += w

When a synapse object is defined, this behavior should be explicitely declared.

The value ``w`` is then decreased using a decreasing exponential function of the time elapsed since the last postsynaptic spike:

.. code-block:: python
    
    w = clip(w - cApost * exp((t_post - t)/tau_post) , 0.0 , wmax) 

The ``clip()`` global function is there to ensure that ``w`` is bounded between 0.0 and ``wmax``. As ``t >= t_post``, the exponential part is smaller than 1.0. The ``pre_spike`` argument therefore ensures that the synapse is depressed is a pre-synaptic spike occurs shortly after a post-synaptic one. "Shortly" is quantified by the time constant ``tau_post``, usually in the range of 10 ms.

* Every time a post-synaptic spike is emitted (``post_spike``), the value ``w`` is increased proportionally to the time elapsed since the last pre-synaptic spike:

.. code-block:: python
    
    w = clip(w + cApre * exp((t_pre - t)/tau_pre) , 0.0 , wmax)

This term defines the potentiation of a synapse when a pre-synaptic spike is followed immediately by a post-synaptic one: the inferred causality between the two events should be reinforced.

.. warning::

    Only the last pre- and post-synaptic spikes are accessible, not the whole history. Only **nearest-neighbor spike-interactions** are possible using ANNarchy, not temporal all-to-all interactions where the whole spike history is used for learning (see the entry on STDP at `Scholarpedia <http://www.scholarpedia.org/article/Spike-timing_dependent_plasticity>`_).

    Some networks may not work properly when using this simulation mode. For example, whenever the pre-synaptic neurons fires twice in a very short interval and causes a post-synaptic spike, the corresponding weight should be reinforced twice. With the proposed STDP rule, it would be reinforced only once.

    It is therefore generally advised to use online versions of STDP.


Online version
---------------

The online version of STDP requires two synaptic traces, which are increased whenever a pre- resp. post-synaptic spike is perceived, and decay with their own dynamics in between.

Using the same vocabulary as Brian, such an implementation would be:

.. code-block:: python

    STDP_online = Synapse(
        parameters = """
            tau_pre = 10.0 : postsynaptic
            tau_post = 10.0 : postsynaptic
            cApre = 0.01 : postsynaptic
            cApost = 0.0105 : postsynaptic
            wmax = 0.01 : postsynaptic
        """,
        equations = """
            tau_pre * dApre/dt = - Apre
            tau_post * dApost/dt = - Apost
        """,
        pre_spike = """
            g_target += w
            Apre += cApre 
            w = clip(w + Apost, 0.0 , wmax)
        """,                  
        post_spike = """
            Apost += cApost
            w = clip(w + Apre, 0.0 , wmax)
        """      
    ) 
    
The variables ``Apre`` and ``Apost`` are exponentially decreasing traces of pre- and post-synaptic spikes, as shown by the leaky integration in ``equations``. When a presynaptic spike is emitted, ``Apre`` is incremented, the conductance level of the postsynaptic neuron ``g_target`` too, and the synaptic efficiency is decreased proportionally to ``Apost`` (this means that if a post-synaptic spike was emitted shortly before, LTD will strongly be apllied, while if it was longer ago, no major change will be observed). When a post-synaptic spike is observed, ``Apost`` increases and the synaptic efficiency is increased proportionally to ``Apre``. 

The effect of this online version is globally the same as the spike timing dependent version, except that the history of pre- and post-synaptic spikes is fully contained in the variables ``Apre`` and ``Apost``.

.. todo::

    event-driven integration
