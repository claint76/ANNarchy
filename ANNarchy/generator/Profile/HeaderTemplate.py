cuda_profile_header =\
"""
#ifndef __PROFILING_H__
#define __PROFILING_H__

#include <string>
#include <vector>
#include <map>
#include <iostream>
#include <sstream>
#include <fstream>
#include <math.h>
#include <cmath>
#include <float.h>
#include <omp.h>
#include <papi.h>
#include <cuda_runtime_api.h>
#include <cuda_runtime.h>

#define pos(x) (x>0.0? x : 0.0)
#define square(x) (x*x)
#define checkstring(x) ((x.find(":")!=std::string::npos)||(x.find("#")!=std::string::npos)||(x.find("\\n")!=std::string::npos))

class Profiling {
    
    public:
        Profiling();

        ~Profiling() {
        }
	
	/*Set/get Anzahl,Namen*/
	void set_CPU_time_number( int number){Profiling_time_CPU_count=number;}
	void set_GPU_time_number( int number){Profiling_time_count=number;}
	void set_Init_time_number(int number){Profiling_time_init_count=number;}
	void set_memcopy_number(  int number){Profiling_memcopy_count=number;}

	void get_device_prop(int device);

	//Aufruf direkt nach allen set Number's
	void init(int extended=1);
	void init_GPU_prof(void);

	//Funktionen um alle Profiling Aktionen an(Standart)/ab zuschalten(betrifft !ALLE! start/stop/evaluate/error)->Messung Gesammtzeit ohne Profiling Wartepausen
	void set_profiling_off(){Profil=0;}
	void set_profiling_on( ){Profil=1;}

	
	//Folgende Funktionen erst nach init nutzbar
	void set_CPU_time_name( int number,std::string name){Prof_time_CPU[number].name=name;}
	void set_GPU_time_name( int number,std::string name){Prof_time[number].name=name;}
	void set_Init_time_name(int number,std::string name){Prof_time_init[number].name=name;}
	void set_memcopy_name(  int number,std::string name){Prof_memcopy[number].name=name;}

	//additonal Syntax fuer Python Auswertung: Zahl(X-Ache);String
	void set_CPU_time_additional(  int number,std::string additonal){Prof_time_CPU[number].additonal=additonal;}
	void set_GPU_time_additional(  int number,std::string additonal){Prof_time[number].additonal=additonal;}
	void set_Init_time_additional( int number,std::string additonal){Prof_time_init[number].additonal=additonal;}
	void set_memcopy_additional(   int number,std::string additonal){Prof_memcopy[number].additonal=additonal;}

	void start_CPU_time_prof( int number);
	void start_GPU_time_prof( int number);
	void start_Init_time_prof(int number);
	void start_memcopy_prof(  int number,int bytesize);
	void start_overall_time_prof();

	void stop_CPU_time_prof( int number,int directevaluate=1);
	void stop_GPU_time_prof( int number,int directevaluate=1);
	void stop_Init_time_prof(int number,int directevaluate=1);
	void stop_memcopy_prof(  int number,int directevaluate=1);
	void stop_overall_time_prof();

	void evaluate_CPU_time_prof( int number);
	void evaluate_GPU_time_prof( int number);
	void evaluate_Init_time_prof(int number);
	void evaluate_memcopy_prof(  int number);
	void evaluate_overall_time_prof();

	void reset_CPU_time_prof( int number);
	void reset_GPU_time_prof( int number);
	void reset_Init_time_prof(int number);
	void reset_memcopy_prof(  int number);
	void reset_overall_time_prof();

	void error_CPU_time_prof();
	void error_GPU_time_prof();


	void evaluate(int disp, int file,const char * filename="Profiling.log");

    private:

	struct Profiling_unit{
		long count=0;
		double min=FLT_MAX;
		double max=FLT_MIN;
		double avg;
		double standard;//Standard deviation
		double prozent_CPU;
		double prozent_GPU;
		double summ=0;
		double summsqr=0;
	};

	struct Profiling_time{
	   	std::string name="";
	   	std::string additonal="";
		Profiling_unit time;

		cudaEvent_t startevent, stopevent;
		long_long start,stop;
	};
	struct Profiling_memcopy{
	   	std::string name="";
	   	std::string additonal="";
		Profiling_unit time;
		Profiling_unit memorysize;
		Profiling_unit memorythroughput;

		cudaEvent_t startevent, stopevent;
		long_long start,stop;
		int memory;
	};

	struct Profiling_general{
		double CPU_summ=0;
		double GPU_summ=0;

		long_long start,stop;
	};

	struct Device_prop{
		int maxThreadsPerBlock;
		int ECCEnabled;
		int regsPerMultiprocessor;
		int maxThreadsPerMultiprocessor;
		int major,minor;
	};

	int Profiling_time_count=0;
	int Profiling_time_CPU_count=0;
	int Profiling_time_init_count=0;
	int Profiling_memcopy_count=0;

	int Profil=1;

	//Profiling
        Profiling_time *Prof_time;
        Profiling_time *Prof_time_CPU;
        Profiling_time *Prof_time_init;
        Profiling_memcopy *Prof_memcopy;
        Profiling_general Prof_general;
	Device_prop device_prop;

	void evaluate_calc();
	void evaluate_disp();
	int evaluate_file(const char * filename="Profiling.log");
};


#endif
"""

openmp_profile_header=\
"""
#ifndef __PROFILING_CPU_H__
#define __PROFILING_CPU_H__

#include <string>
#include <vector>
#include <map>
#include <iostream>
#include <sstream>
#include <fstream>
#include <math.h>
#include <cmath>
#include <float.h>
#include <omp.h>
#include <papi.h>
#include <sched.h>  // sched_getcpu

//[hdin]
#include <algorithm>
#include <iterator>

#define pos(x) (x>0.0? x : 0.0)
#define square(x) (x*x)
#define checkstring(x) ((x.find(":")!=std::string::npos)||(x.find("#")!=std::string::npos)||(x.find("\\n")!=std::string::npos))

#define INIT_THREAD 1
#define INIT_OUTLIER 2

class Profiling {
    
public:
    Profiling();

    ~Profiling();

    /*use following functions only befor the init function to set how many measurement units of each type you want to use*/
    void set_CPU_time_number(  int number){Profiling_time_CPU_count=number;}
    void set_CPU_cycles_number(int number){Profiling_cycles_CPU_count=number;}
    void set_thread_statistic_number(int number){Profiling_thread_count=number;}
    void set_overall_number(int number){Profiling_overall_count=number;}
    
    /*use following function only befor the init thread function to set how many treads you want to use maximal in thread statistic measurements*/
    void set_max_thread_number(int number){thread_count=number;}

    //Aufruf direkt nach allen set Number's
    //param extended: set Bit 0x01:execute init thread 
    //                  set Bit 0x02:execute init trash
    void init(int extended= INIT_THREAD | INIT_OUTLIER);
    void init_thread();

    /*use following functions to control the outlier-System, only befor the init outlier function and after the init function*/
    void set_CPU_time_hight_outlier_count(  int number,int count){if(Profil) Prof_time_CPU[number].time.maxac=count;}
    void set_CPU_time_low_outlier_count(  int number,int count){if(Profil) Prof_time_CPU[number].time.minac=count;}
    void set_CPU_cycles_hight_outlier_count(  int number,int count){if(Profil) Prof_time_CPU[number].time.maxac=count;}
    void set_CPU_cycles_low_outlier_count(  int number,int count){if(Profil) Prof_time_CPU[number].time.minac=count;}

    /*init the outlier System*/
    void init_outlier();

    //Funktionen um alle Profiling Aktionen an(Standart)/ab zuschalten(betrifft !ALLE! start/stop/evaluate)->Messung Gesammtzeit ohne Profiling Wartepausen
    void set_profiling_off(){Profil=0;}
    void set_profiling_on( ){Profil=1;}

/*use all following functions only after the init function*/

    //set Names for output
    void set_CPU_time_name(  int number,std::string name){Prof_time_CPU[number].name=name;}
    void set_CPU_cycles_name(int number,std::string name){Prof_cycles_CPU[number].name=name;}
    void set_thread_statistic_name(int number,std::string name){Prof_thread_statistic[number].name=name;}

    //set additional for output in files ( syntax depends on the evaluator )
    void set_CPU_time_additional(  int number,std::string additonal){Prof_time_CPU[number].additonal=additonal;}
    void set_CPU_cycles_additional(int number,std::string additonal){Prof_cycles_CPU[number].additonal=additonal;}
    void set_thread_statistic_additional(int number,std::string additonal){Prof_thread_statistic[number].additonal=additonal;}

    //set related overall time
    void set_CPU_time_related_time(  int number,int overallnumber){Prof_time_CPU[number].overall_time=overallnumber;}
    //void set_CPU_cycles_related_time(int number,int overallnumber){Prof_cycles_CPU[number].overall_time=overallnumber;}

    //set 'General section' text for output in files ( syntax depends on the evaluator )
    void set_general_text(std::string text){Generaltext=text;}
    
    void start_CPU_time_prof( int number);
    void start_overall_time_prof(int number=0);
    void start_CPU_cycles_prof( int number);

    void stop_CPU_time_prof( int number,int directevaluate=1);
    void stop_overall_time_prof(int number=0,int directevaluate=1);
    void stop_CPU_cycles_prof( int number,int directevaluate=1);

    //use this functions only if directevaluate=0 in the corresponding stop function
    void evaluate_CPU_time_prof( int number);
    void evaluate_overall_time_prof(int number=0);
    void evaluate_CPU_cycles_prof( int number);

    //reset single measurement units
    void reset_CPU_time_prof( int number);
    void reset_CPU_cycles_prof( int number);
    void reset_thread_statistic( int number);
    void reset_overall_time_prof(int number=0);

    //get measurement results 
    //    return: Average
    double get_CPU_time_prof( int number);
    double get_CPU_cycles_prof( int number);
    double get_overall_time_prof(int number=0);

    //measurement Error measure
    void error_CPU_time_prof();
    void error_CPU_cycles_prof();

    //use within parallel loop
    void thread_statistic_run( int number);

    //Generate output
    void evaluate(int disp, int file,const char * filename="Profiling.log");
    int mergefiles(const char * infilename1,const char * infilename2="Profiling.log",const char * outfilename="Profiling.log");

    //for [hdin]
    void store_CPU_time_raw(int number){Prof_time_CPU[number].storeRawData=true;}
    void store_not_CPU_time_raw(int number){Prof_time_CPU[number].storeRawData=false;}
    void store_CPU_cycles_raw(int number){Prof_cycles_CPU[number].storeRawData=true;}
    void store_not_CPU_cycles_raw(int number){Prof_cycles_CPU[number].storeRawData=false;}

    enum TimeUnits{
        MICROSECS=0,
        MILLISECS,
        SECS
    };

    void set_time_unit(TimeUnits time_unit) { used_time_unit = time_unit; }
    
private:
    bool evaluateInMillisecs_ = true;

    struct Profiling_unit{
        long count=0;
        double min=FLT_MAX;
        double max=FLT_MIN;
        double avg;
        double standard;//Standard deviation
        double prozent_CPU;
        double summ=0;
        double summsqr=0;

        //'Trash' section
        double *maxarray,*minarray;
        int maxac=0;
        int minac=0;
        
        // [hdin] sometimes needed for additional evaluation
        double adjustedMean=0.0;
        std::vector<double> rawData=std::vector<double>();
    };

    struct Profiling_thread_statistic_unit{
        volatile long count=0;
    };

    struct Profiling_time{
       std::string name="";
       std::string additonal="";
        Profiling_unit time;

        int overall_time=0;
        int calculated=0;

        long_long start,stop;

        bool storeRawData=false;
    };

    struct Profiling_thread_statistic_core{
        Profiling_thread_statistic_unit *core;
    };

    struct Profiling_thread_statistic{
           std::string name="";
           std::string additonal="";
        Profiling_thread_statistic_core *thread;
        int used_threads=0;
    };

    struct Profiling_general{
        double CPU_summ=0;

        long_long start,stop;
    };

    int Profiling_time_CPU_count=0;
    int Profiling_cycles_CPU_count=0;
    int Profiling_thread_count=0;
    int Profiling_overall_count=1;
    int thread_count=0;
    int core_count=0;

    int Profil=1;

    //Profiling
    Profiling_time *Prof_time_CPU;
    Profiling_time *Prof_cycles_CPU;
    Profiling_thread_statistic *Prof_thread_statistic;
    Profiling_general *Prof_general;
    std::string Generaltext="";

    void evaluate_calc(int sec=0, int number=0);
    void evaluate_recalc(int sec=0,int number=0);
    void evaluate_disp();
    int evaluate_file(const char * filename="Profiling.log");

    // [hdin] time unit handling
    std::vector< std::pair<std::string, double> > time_units;   ///< used time units: unit name and rescale factor
    int used_time_unit; ///< chose time unit (default TimeUnit::SECS)

    double compAdjustedMeanV1(std::vector<double> data) {
        if ( data.empty() )
            return 0.0;

        if ( data.size() < 100 )
            return 0.0;

        int toRemove = ceil(double(data.size()) / 100.0 * 5.0); // remove 10 percent of the items 
        std::vector<double> tmp = data; // need to copy vector, otherwise we would overwrite input
        std::sort( tmp.begin(), tmp.end() ); // default comparison is '<'
        
        tmp.erase( tmp.end()-toRemove, tmp.end());
        tmp.erase( tmp.begin(), tmp.begin()+toRemove);
        
        double sum = 0.0;
        for ( auto it = tmp.begin(); it != tmp.end(); it++ )
            sum+= *it;
            
        return sum / double(tmp.size());
    }
    
    template<typename T>
    T compMean(std::vector<T> data) {
        // compute mean
        T sum = 0.0;
        for ( auto it = data.begin(); it != data.end(); it++ )
            sum += *it;
        return T(sum / double(data.size()));
    }
    
    template<typename T>
    T compStandardDeviation(std::vector<T> data, T mean) {
        // compute varianz
        T var = 0.0;
        for ( auto it = data.begin(); it != data.end(); it++ )
            var += (*it-mean)*(*it-mean);
        
        // Notice: there are both variants in literature divide b N or N-1,
        //         I decided I take the second version, as it seems the more correct one.
        return sqrt( (var / double(data.size()-1) ) );
    }

    double compAdjustedMeanV2(std::vector<double> data, double thresholdFactor = 3.0) {
        if ( data.empty() )
            return 0.0;

        double mean = compMean<double>(data);
        double std_dev = compStandardDeviation<double>(data, mean);

        std::vector<double> tmp = data;
        double pos_threshold = mean+thresholdFactor*std_dev;
        double neg_threshold = mean-thresholdFactor*std_dev;
        for ( auto it = tmp.begin(); it != tmp.end(); it++ )
            if ( *it < neg_threshold || *it > pos_threshold )
                it = tmp.erase(it);

        return compMean<double>(tmp);
    }    
};
#endif
"""
