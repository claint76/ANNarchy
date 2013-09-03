#ifndef __POPULATION_H__
#define __POPULATION_H__

#include "Global.h"

class Population{
public:
	// functions
	Population(std::string name, int nbNeurons);

	~Population();

	virtual void metaSum();
	virtual void metaStep();
	virtual void metaLearn();
	virtual void globalOperations();

	std::string getName() { return name_; }

	virtual int getNeuronCount() { return nbNeurons_; }

	class Projection* getProjection(int neuron, int type) { return projections_[neuron][type]; }

	void addProjection(int postRankID, Projection* proj);

	void removeProjection(Population *pre);

	void printRates();

	void setMaxDelay(int delay);

	DATA_TYPE sum(int neur, int type);

	std::vector<DATA_TYPE>* getRates() {
		return &rate_;
	}

	std::vector<DATA_TYPE>* getRates(int delay) {
		if (delay < (int)delayedRates_.size())
			return &(delayedRates_[delay-1]);
		else
			return NULL;
	}

	std::vector<DATA_TYPE> getRates(std::vector<int> delays, std::vector<int> ranks);

	DATA_TYPE getDt() { return dt_;	}

	void setDt(DATA_TYPE dt) { dt_ = dt; }

protected:
	// data
	int nbNeurons_;
	std::string name_;	///< name of layer
	int maxDelay_;
	DATA_TYPE dt_;

	std::vector<DATA_TYPE>	rate_;
	std::vector< std::vector<DATA_TYPE>	> delayedRates_;
	std::vector<std::vector<class Projection*> > projections_;	// first dimension, neuron wise
};

#endif
