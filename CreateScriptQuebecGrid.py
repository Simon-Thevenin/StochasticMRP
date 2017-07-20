#!/usr/bin/python
# script de lancement pour les fichiers


import os
import subprocess

if __name__ == "__main__":

     #for instance in ["00", "01", "02", "03", "04", "05", "01_LTH", "02_LTH", "03_LTH", "04_LTH", "05_LTH" ]:
    for instance in ["00", "01", "01_LTH" ]:
        distributionset = [ "NonStationary"]
        #distributionset = ["SlowMoving", "Normal", "Lumpy", "NonStationary"]
        if instance == "00":
            distributionset = ["Binomial"]
        if instance == "01":
            distributionset = [ "Uniform", "NonStationary"]
       #     distributionset = ["SlowMoving", "Normal", "Lumpy", "Uniform", "NonStationary"]
        for distribution in distributionset:
            #model = "YFix"
            #nrscenar = 500
            #generation = "RQMC"
            modelset = ["YFix", "YQFix", "Average"]



            for model in modelset:
                 generationset = ["MC", "RQMC"]


                 scenarset = [ "512" ]

                 policyset = [ "S","NNS", "NND", "NNDAC", "NNSAC", "Re-solve"]
                 methodset = ["MIP"]
                 avg = False
                 if model == "YFix":
                     scenarset = ["512"]
                     if instance in ["00", "01", "02", "03", "04", "05"]:
                         methodset = ["MIP", "SDDP" ]
                     else:
                         methodset = ["MIP"]

                 if model == "YQFix":
                     #scenarset = [ "1000" ]
                     scenarset = ["2", "4", "8", "50", "100", "200", "500", "1000"]
                     policyset = [ "Fix" ]

                 if model == "Average":
                     scenarset =  [ "1" ]
                     avg = True
                     policyset = ["Fix"]
                     generationset = ["MC"]


                 for method in methodset:

                     if (instance == "00" or instance == "01") and (model == "YFix" and method == "MIP"):
                        generationset = ["MC", "RQMC", "all"]

                     for generation in generationset:

                         if method == "SDDP":
                             scenarset = ["10",  "50", "100", "200"]
                             policyset = [ "SDDP" ]

                         if model == "YFix" and method == "MIP":
                             scenarset = ["512"]

                         for nrscenar in scenarset:
                              for seed in range( 5 ):
                                    qsub_filename = "job_solve_%s_%s_%s_%s_%s_%s_%s" % (
                                            instance, distribution, model, nrscenar, generation, seed, method  )
                                    qsub_file = open(qsub_filename, 'w')
                                    qsub_file.write("""
#!/bin/bash
#PBS -A abc-123-aa
#PBS -l walltime=3:00:00
#PBS -l nodes=1:ppn=1
#PBS -r n
ulimit -v 16000000
mkdir /tmp/thesim
cd /home/thesim/stochasticmrp/
python test.py Solve %s %s %s %s %s -s %s  -n 500 -m %s
""" % ( instance, distribution, model, nrscenar, generation, seed, method  ))
                                    for Policy in policyset:
                                          qsub_filename = "job_evaluate_%s_%s_%s_%s_%s_%s_%s_%s" % (
                                              instance, distribution, model, nrscenar, generation,method, Policy, seed)
                                          qsub_file = open(qsub_filename, 'w')
                                          qsub_file.write("""
#!/bin/bash
#PBS -A abc-123-aa
#PBS -l walltime=30:00:00
#PBS -l nodes=1:ppn=1
#PBS -r n
ulimit -v 16000000
mkdir /tmp/thesim
cd /home/thesim/stochasticmrp/
python test.py Evaluate %s %s %s %s %s  -s %s -p %s
 """ % (instance, distribution, model, nrscenar, generation, seed, Policy) )


    # Create the sh file
    filename = "runalljobs.sh"
    file = open(filename, 'w')
    file.write("""
#!/bin/bash -l
#
""")
    for instance in ["00", "01", "01_LTH" ]:
        distributionset = [ "NonStationary"]
        #distributionset = ["SlowMoving", "Normal", "Lumpy", "NonStationary"]
        if instance == "00":
            distributionset = ["Binomial"]
        if instance == "01":
            distributionset = [ "Uniform", "NonStationary"]
       #     distributionset = ["SlowMoving", "Normal", "Lumpy", "Uniform", "NonStationary"]
        for distribution in distributionset:
            #model = "YFix"
            #nrscenar = 500
            #generation = "RQMC"
            modelset = ["YFix", "YQFix", "Average"]



            for model in modelset:
                 generationset = ["MC", "RQMC"]


                 scenarset = [ "512" ]

                 policyset = [ "S","NNS", "NND", "NNDAC", "NNSAC", "Re-solve"]
                 methodset = ["MIP"]
                 avg = False
                 if model == "YFix":
                     scenarset = ["512"]
                     if instance in ["00", "01", "02", "03", "04", "05"]:
                         methodset = ["MIP", "SDDP" ]
                     else:
                         methodset = ["MIP"]

                 if model == "YQFix":
                     #scenarset = [ "1000" ]
                     scenarset = ["2", "4", "8", "50", "100", "200", "500", "1000"]
                     policyset = [ "Fix" ]

                 if model == "Average":
                     scenarset =  [ "1" ]
                     avg = True
                     policyset = ["Fix"]
                     generationset = ["MC"]


                 for method in methodset:

                     if (instance == "00" or instance == "01") and (model == "YFix" and method == "MIP"):
                        generationset = ["MC", "RQMC", "all"]

                     for generation in generationset:

                         if method == "SDDP":
                             scenarset = ["10",  "50", "100", "200"]
                             policyset = [ "SDDP" ]

                         if model == "YFix" and method == "MIP":
                             scenarset = ["512"]

                         for nrscenar in scenarset:
                              for seed in range( 5 ):
                                file.write("qsub job_solve_%s_%s_%s_%s_%s_%s_%s \n" % (
                                                instance, distribution, model, nrscenar, generation, seed, method  ))
