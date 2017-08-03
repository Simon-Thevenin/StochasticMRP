#!/usr/bin/python
# script de lancement pour les fichiers
#!/usr/bin/python
# script de lancement pour les fichiers


import os
import subprocess

if __name__ == "__main__":

    InstanceSet = [ "00_C=2", "01_C=2", "02_C=2", "03_C=2", "04_C=2", "05_C=2" ]
    #InstanceSet = ["05_C=2"]

    #["00", "01", "02", "03", "04", "05" ]
               #    "01_Theta4", "02_Theta4", "03_Theta4", "04_Theta4", "05_Theta4",
               #    "00_b=2h", "01_b=2h", "02_b=2h", "03_b=2h", "04_b=2h", "05_b=2h",
               #    "00_b=50h", "01_b=50h", "02_b=50h", "03_b=50h", "04_b=50h", "05_b=50h",
               #    "00_C=2", "01_C=2", "02_C=2", "03_C=2", "04_C=2", "05_C=2",
               #    "00_OneResourcePerLevelC=2", "01_OneResourcePerLevelC=2", "02_OneResourcePerLevelC=2", "03_OneResourcePerLevelC=2", "04_OneResourcePerLevelC=2", "05_OneResourcePerLevelC=2" ]
               #    "00_OneResourcePerLevelC=1", "01_OneResourcePerLevelC=1", "02_OneResourcePerLevelC=1", "03_OneResourcePerLevelC=1", "04_OneResourcePerLevelC=1", "05_OneResourcePerLevelC=1" ]


    #modelset = ["YFix", "YQFix", "Average"]
    modelset = [ "YFix"]#, "YQFix"]
    generationset = ["RQMC"]#, "MC"]
    Nrseed = 5

    for instance in InstanceSet :
    #for instance in ["00", "01", "01_LTH"]:
         distributionset = ["NonStationary"]
         # distributionset = ["SlowMoving", "Normal", "Lumpy", "NonStationary"]
         if instance == "00_C=2":
             distributionset = ["Binomial"]
         if instance == "01_C=2":
             distributionset = ["Uniform", "NonStationary"]
            #distributionset = ["Uniform", "NonStationary"]
             #     distributionset = ["SlowMoving", "Normal", "Lumpy", "Uniform", "NonStationary"]
         for distribution in distributionset:
             # model = "YFix"
             # nrscenar = 500
             # generation = "RQMC"
             #modelset = [ "YFix" ]

             for model in modelset:
                 #generationset = ["MC", "RQMC"]

                 #scenarset = ["512"]

                 policyset = [ "S"]
                 methodset = ["MIP"]
                 avg = False
                 if model == "YFix":
                     scenarset = ["512"]
                     methodset = ["MIP"]
                     #if instance in ["00", "01", "02", "03", "04", "05"]:
                         #methodset = ["MIP", "SDDP"]
                     #    methodset = ["MIP"]
                     #else:
                     #    methodset = ["SDDP"]

                 if model == "YQFix":
                     scenarset = [ "200" ]
                     #scenarset = ["2", "4", "8", "50", "100", "200", "500", "1000"]
                     #policyset = ["Fix", "Re-solve"]
                     policyset = ["Fix"]
                     #generationset = ["RQMC"]
                 if model == "Average":
                     scenarset = ["1"]
                     avg = True
                     policyset = ["Fix", "Re-solve"]
                     #generationset = ["MC"]

                 for method in methodset:

                     # if (instance == "00" or instance == "01") and (model == "YFix" and method == "MIP") and (
                     #        distribution == "Binomial" or distribution == "Uniform"):
                     #    generationset = ["MC", "RQMC", "all"]

                     for generation in generationset:

                         if method == "SDDP":
                             scenarset = ["10", "50", "100", "200"]
                             policyset = ["SDDP"]

                         if model == "YFix" and method == "MIP":
                             scenarset = ["512"]

                         for nrscenar in scenarset:
                             for seed in range(Nrseed):
                                 #maxvss = 7
                                 #if  instance ==  "02_C=2" or  instance ==  "04_C=2":
                                 #    maxvss = 9
                                 #if instance == "05_C=2" or instance == "03_C=2":
                                 #    maxvss = 11

                                 #for vss in range(1, maxvss):
                                    print "job_solve_%s_%s_%s_%s_%s_%s_%s" % (
                                            instance, distribution, model, nrscenar, generation, seed, method  )
                                    qsub_filename = "job_solve_%s_%s_%s_%s_%s_%s_%s_evpi" % (
                                            instance, distribution, model, nrscenar, generation, seed, method  )
                                    qsub_file = open(qsub_filename, 'w')
                                    qsub_file.write("""
#!/bin/bash -l
#
#$ -cwd
#$ -q idra
#$ -j y
#$ -o /home/thesim/outputjob%s%s%s%s%s%s%s.txt
ulimit -v 16000000
mkdir /tmp/thesim
python test.py Solve %s %s %s %s %s -s %s  -n 500 -m %s
""" % ( instance, distribution, model, nrscenar, generation, seed, method,  instance, distribution, model, nrscenar, generation, seed, method  ))
                                    for Policy in policyset:
                                          qsub_filename = "job_evaluate_%s_%s_%s_%s_%s_%s_%s_%s" % (
                                              instance, distribution, model, nrscenar, generation,method, Policy, seed)
                                          qsub_file = open(qsub_filename, 'w')
                                          qsub_file.write("""
#!/bin/bash -l
#
#$ -cwd
#$ -q idra
#$ -j y
#$ -o /home/thesim/outputjobevaluate%s%s%s%s%s%s%s.txt
ulimit -v 16000000
mkdir /tmp/thesim
python test.py Evaluate %s %s %s %s %s  -s %s -p %s
 """ % (instance, distribution, model, nrscenar, generation, seed, Policy, instance, distribution, model, nrscenar, generation, seed, Policy) )


    # Create the sh file
    filename = "runalljobeval.sh"
    file = open(filename, 'w')
    file.write("""
#!/bin/bash -l
#
""")
    for instance in InstanceSet:
        # for instance in ["00", "01", "01_LTH"]:
        distributionset = ["NonStationary"]
        # distributionset = ["SlowMoving", "Normal", "Lumpy", "NonStationary"]
        if instance == "00_C=2":
            distributionset = ["Binomial"]
        if instance == "01_C=2":
            distributionset = ["Uniform", "NonStationary"]
            #     distributionset = ["SlowMoving", "Normal", "Lumpy", "Uniform", "NonStationary"]
        for distribution in distributionset:
            # model = "YFix"
            # nrscenar = 500
            # generation = "RQMC"
            #modelset = ["YFix", "YQFix", "Average"]




            for model in modelset:
                #generationset = ["MC", "RQMC"]


                 #scenarset = [ "512" ]

                 policyset = [ "S","NNS", "NND", "NNDAC", "NNSAC", "Re-solve"]
                 policyset = ["S"]

                 methodset = ["MIP"]
                 avg = False
                 methodset = ["MIP"]
                 # if instance in ["00", "01", "02", "03", "04", "05"]:
                 # methodset = ["MIP", "SDDP"]
                 #    methodset = ["MIP"]
                 # else:
                 #    methodset = ["SDDP"]

                 if model == "YQFix":
                     scenarset = [ "200" ]
                     #scenarset = ["2", "4", "8", "50", "100", "200", "500", "1000"]
                     #policyset = ["Fix", "Re-solve"]
                     policyset = ["Fix"]

                 if model == "Average":
                     scenarset =  [ "1" ]
                     avg = True
                     policyset = ["Fix", "Re-solve"]
                     generationset = ["MC"]


                 for method in methodset:
                     #if (instance == "00" or instance == "01") and (model == "YFix" and method == "MIP") and (distribution == "Binomial" or distribution == "Uniform"):
                     #  generationset = ["MC", "RQMC", "all"]
                     for generation in generationset:

                         if method == "SDDP":
                             scenarset = ["10",  "50", "100", "200"]
                             policyset = [ "SDDP" ]

                         if model == "YFix" and method == "MIP":
                             scenarset = ["512"]

                         for nrscenar in scenarset:
                              for seed in range( Nrseed ):
                                  for Policy in policyset:
                                        file.write("qsub job_evaluate_%s_%s_%s_%s_%s_%s_%s_%s \n" % (
                                                      instance, distribution, model, nrscenar, generation,method, Policy, seed))


  # Create the sh file
    filename = "runalljobsolve.sh"
    file = open(filename, 'w')
    file.write("""
#!/bin/bash -l
#
""")
    for instance in InstanceSet:
        # for instance in ["00", "01", "01_LTH"]:
        distributionset = ["NonStationary"]
        # distributionset = ["SlowMoving", "Normal", "Lumpy", "NonStationary"]
        if instance == "00_C=2":
            distributionset = ["Binomial"]
        if instance == "01_C=2":
            distributionset = ["Uniform"]
            #distributionset = ["Uniform", "NonStationary"]
            #     distributionset = ["SlowMoving", "Normal", "Lumpy", "Uniform", "NonStationary"]
        for distribution in distributionset:
            # model = "YFix"
            # nrscenar = 500
            # generation = "RQMC"
            #modelset = ["YFix", "YQFix", "Average"]



            for model in modelset:


                 scenarset = [ "512" ]

                 policyset = [ "S","NNS", "NND", "NNDAC", "NNSAC", "Re-solve"]
                 methodset = ["MIP"]
                 avg = False
                 methodset = ["MIP"]
                 # if instance in ["00", "01", "02", "03", "04", "05"]:
                 # methodset = ["MIP", "SDDP"]
                 #    methodset = ["MIP"]
                 # else:
                 #    methodset = ["SDDP"]

                 if model == "YQFix":
                     scenarset = [ "200" ]
                     #scenarset = ["2", "4", "8", "50", "100", "200", "500", "1000"]
                     #policyset = ["Fix", "Re-solve"]
                     policyset = ["Fix"]

                 if model == "Average":
                     scenarset =  [ "1" ]
                     avg = True
                     policyset = [ "Fix", "Re-solve" ]
                     generationset = ["MC"]


                 for method in methodset:
                     #if (instance == "00" or instance == "01") and (model == "YFix" and method == "MIP") and (distribution == "Binomial" or distribution == "Uniform"):
                     #   generationset = ["MC", "RQMC", "all"]
                     print generationset
                     for generation in generationset:

                         if method == "SDDP":
                             scenarset = ["10",  "50", "100", "200"]
                             policyset = [ "SDDP" ]

                         if model == "YFix" and method == "MIP":
                             scenarset = ["512"]

                         for nrscenar in scenarset:
                                for seed in range( Nrseed ):
                                        file.write("qsub job_solve_%s_%s_%s_%s_%s_%s_%s_evpi \n" % (
                                            instance, distribution, model, nrscenar, generation, seed, method ) )