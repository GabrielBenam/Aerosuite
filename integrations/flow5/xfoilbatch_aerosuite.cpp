// AeroSuite adapter for flow5 v7.57. Original API pattern: API_examples/XFoilBatchRun.
// Compile as a separate CMake target linked to the flow5 libraries.
// GPL-3.0-or-later compatibility must be reviewed before distribution.
#include <cmath>
#include <filesystem>
#include <iostream>
#include <stdexcept>
#include <string>
#include <vector>
#include <thread>
#include <api.h>
#include <constants.h>
#include <flow5-io.h>
#include <foil.h>
#include <objects2d.h>
#include <objects2d_globals.h>
#include <polar.h>
#include <polarnamemaker.h>
#include <xfoiltask.h>

namespace fs = std::filesystem;
struct Params {
    int naca = 2412;
    std::vector<double> reynolds = {100000, 200000, 500000};
    double alpha_start = -4.0, alpha_end = 12.0, alpha_step = 1.0, mach = 0.0;
    fs::path output;
};
static void usage() {
    std::cout << "Usage: aerosuite-xfoilbatch --naca 2412 --reynolds 100000,200000 "
                 "--alpha-start -4 --alpha-end 12 --alpha-step 1 --mach 0 "
                 "--output C:/results/run.fl5\n";
}
static double number(const std::string &s) {
    size_t n=0;
    double d=std::stod(s,&n);
    if(n!=s.size() || !std::isfinite(d)) throw std::invalid_argument("Non-finite or invalid number: "+s);
    return d;
}
static Params parse(int argc, char** argv) {
    Params p;
    for(int i=1;i<argc;i++) {
        std::string flag=argv[i];
        if(flag=="--help") {usage();std::exit(0);}
        if(i+1>=argc) throw std::invalid_argument("Missing value for "+flag);
        std::string v=argv[++i];
        if(flag=="--naca") {
            if(v.size()!=4 || v.find_first_not_of("0123456789")!=std::string::npos) throw std::invalid_argument("NACA must be four digits");
            p.naca=std::stoi(v);
            int m=p.naca/1000,camber_pos=(p.naca/100)%10,thickness=p.naca%100;
            if(thickness==0 || (m==0)!=(camber_pos==0)) throw std::invalid_argument("Invalid NACA geometry");
        } else if(flag=="--reynolds") {
            p.reynolds.clear();
            size_t start=0;
            while(start<v.size()) {
                size_t end=v.find(',',start);
                auto chunk=v.substr(start,end==std::string::npos ? std::string::npos : end-start);
                double re=number(chunk);
                if(re<=0) throw std::invalid_argument("Reynolds must be positive");
                p.reynolds.push_back(re);
                if(end==std::string::npos) break;
                start=end+1;
            }
        } else if(flag=="--alpha-start") p.alpha_start=number(v);
        else if(flag=="--alpha-end") p.alpha_end=number(v);
        else if(flag=="--alpha-step") p.alpha_step=number(v);
        else if(flag=="--mach") p.mach=number(v);
        else if(flag=="--output") p.output=fs::path(v);
        else throw std::invalid_argument("Unknown option: "+flag);
    }
    if(p.output.empty()) throw std::invalid_argument("--output is required");
    if(p.reynolds.empty() || p.reynolds.size()>32) throw std::invalid_argument("Require 1-32 Reynolds values");
    if(!(p.alpha_end>=p.alpha_start && p.alpha_step>0 && (p.alpha_end-p.alpha_start)/p.alpha_step<=500))
        throw std::invalid_argument("Invalid alpha range");
    if(p.mach<0 || p.mach>=1) throw std::invalid_argument("Mach must be in [0,1)");
    return p;
}
int main(int argc,char** argv) {
    try {
        Params p=parse(argc,argv);
        Foil* foil=new Foil;
        Objects2d::makeNacaFoil(foil,p.naca,200);
        foil->setName("NACA"+std::to_string(p.naca));
        Objects2d::insertThisFoil(foil);
        std::vector<Polar*> polars;
        for(double re:p.reynolds) {
            // Same T1POLAR argument convention as flow5 API_examples/XFoilBatchRun.
            Polar* polar=Objects2d::createPolar(foil,xfl::T1POLAR,re,p.mach,9.0,1.0,1.0);
            polar->setName(PolarNameMaker::makeName(polar));
            Objects2d::insertPolar(polar);
            polars.push_back(polar);
        }
        // Sequential execution is intentional for an initial deterministic integration.
        for(auto* polar:polars) {
            XFoilTask task;
            task.initialize(*foil,polar,false);
            task.appendRange({true,p.alpha_start,p.alpha_end,p.alpha_step});
            task.run();
            std::cout<<"Finished Reynolds="<<polar->Reynolds()<<"\n";
        }
        if(p.output.has_parent_path()) fs::create_directories(p.output.parent_path());
        std::string msg;
        bool saved=io::saveProject(p.output.string(),msg);
        globals::deleteObjects();
        if(!saved) {std::cerr<<"Failed to save .fl5: "<<msg<<"\n";return 3;}
        std::cout<<"AeroSuite saved "<<p.output.string()<<"\n";
        return 0;
    } catch(const std::exception& e) {
        std::cerr<<"AeroSuite flow5 adapter: "<<e.what()<<"\n";
        return 2;
    }
}
