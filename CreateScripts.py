#!/usr/bin/python
# script de lancement pour les fichiers
#!/usr/bin/python
# script de lancement pour les fichiers


import os
import subprocess
import csv

NrScenarioEvaluation = "500"

def Createsolvejob(instance, distribution, model, nrscenar, generation, seed, method, mipsetting):
    print "job_solve_%s_%s_%s_%s_%s_%s_%s_%s" % (
        instance, distribution, model, nrscenar, generation, seed, method, mipsetting)
    qsub_filename = "./Jobs/job_solve_%s_%s_%s_%s_%s_%s_%s_%s" % (
        instance, distribution, model, nrscenar, generation, seed, method, mipsetting)
    qsub_file = open(qsub_filename, 'w')
    qsub_file.write("""
#!/bin/bash -l
#
#$ -cwd
#$ -q idra
#$ -j y
#$ -o /home/thesim/outputjob%s%s%s%s%s%s%s%s.txt
ulimit -v 16000000
mkdir /tmp/thesim
python test.py Solve %s %s %s %s %s -s %s  -m %s --mipsetting %s
""" % (instance, distribution, model, nrscenar, generation, seed, method, mipsetting, instance,
                          distribution, model, nrscenar, generation, seed, method, mipsetting))


def CreatePolicyJob(instance, distribution, model, nrscenar, generation, seed, Policy):
    qsub_filename = "./Jobs/job_evaluate_%s_%s_%s_%s_%s_%s_%s_%s" % (
        instance, distribution, model, nrscenar, generation, method, Policy, seed)
    qsub_file = open(qsub_filename, 'w')
    qsub_file.write("""
#!/bin/bash -l
#
#$ -cwd
#$ -q idra
#$ -j y
#$ -o /home/thesim/outputjobevaluate%s%s%s%s%s%s%s%s.txt
ulimit -v 16000000
mkdir /tmp/thesim
python test.py Evaluate %s %s %s %s %s  -s %s -p %s -n %s
""" % (instance, distribution, model, nrscenar, generation, seed, Policy, NrScenarioEvaluation, instance, distribution, model, nrscenar,
        generation, seed, Policy, NrScenarioEvaluation))


if __name__ == "__main__":
    csvfile = open("./Instances/InstancesToSolve.csv", 'rb')
    data_reader = csv.reader(csvfile, delimiter=",", skipinitialspace=True)
    instancenameslist = []
    for row in data_reader:
       instancenameslist.append(row)
    InstanceSet = instancenameslist[0]
    #InstanceSet = ["G5047323b2"]
    # for InstanceName in instancenameslist:#["01", "02", "03", "04", "05"]:
    #InstanceSet = [ "00", "01", "02", "03", "04", "05" ]
    #InstanceSet = ["05_C=2"]

    #["00", "01", "02", "03", "04", "05" ]
               #    "01_Theta4", "02_Theta4", "03_Theta4", "04_Theta4", "05_Theta4",
               #    "00_b=2h", "01_b=2h", "02_b=2h", "03_b=2h", "04_b=2h", "05_b=2h",
               #    "00_b=50h", "01_b=50h", "02_b=50h", "03_b=50h", "04_b=50h", "05_b=50h",
               #    "00_C=2", "01_C=2", "02_C=2", "03_C=2", "04_C=2", "05_C=2",
               #    "00_OneResourcePerLevelC=2", "01_OneResourcePerLevelC=2", "02_OneResourcePerLevelC=2", "03_OneResourcePerLevelC=2", "04_OneResourcePerLevelC=2", "05_OneResourcePerLevelC=2" ]
               #    "00_OneResourcePerLevelC=1", "01_OneResourcePerLevelC=1", "02_OneResourcePerLevelC=1", "03_OneResourcePerLevelC=1", "04_OneResourcePerLevelC=1", "05_OneResourcePerLevelC=1" ]


    #modelset = [ "Average", "YQFix", "YFix", "HeuristicYFix"]
    modelset = [ "YQFix", "YFix", "HeuristicYFix", "Average", "AverageSS", ]#, "HeuristicYFix", "YFix", "YQFix"]

    nrcenarioyfix =["6400" ]
    nrcenarioyfqix = ["200"]
    nrcenarioheuristicyfix = ["6400", "40000"] # scenarset = ["200", "512", "3200", "6400"]

    policyyqfix = ["Fix", "Resolve"]
    policyyfix = ["Resolve"]
    Generationset = [ "RQMC"]#, "MC"]cd J
    methodset = ["MIP"]
    Nrseed = 1
    distributionset = ["NonStationary"]

    # Create the sh file for evaluation
    jobevalfilename = "runalljobeval.sh"
    fileeval = open(jobevalfilename, 'w')
    fileeval.write("""
#!/bin/bash -l
#
""")

    # Create the sh file for resolution
    filesolvename = "runalljobsolve.sh"
    filesolve = open(filesolvename, 'w')
    filesolve.write("""
#!/bin/bash -l
#
""")


    for instance in InstanceSet :
        for distribution in distributionset:
             for model in modelset:

                 policyset = [ "Fix"]
                 methodset = ["MIP"]
                 avg = False
                 if model == "YFix":
                     scenarset= nrcenarioyfix
                     generationset = Generationset
                     policyset = policyyfix
                 if model == "HeuristicYFix":
                    scenarset = nrcenarioheuristicyfix
                    generationset = Generationset
                    policyset = policyyfix
                 if model == "YQFix":
                     scenarset = nrcenarioyfqix
                     policyset = policyyqfix
                     generationset = Generationset
                 if model == "Average" or model == "AverageSS":
                     scenarset = ["1"]
                     avg = True
                     generationset = ["MC"]
                     policyset = policyyqfix
                 for method in methodset:
                     for generation in generationset:
                         for nrscenar in scenarset:
                             for seed in range(Nrseed):
                                   for mipsetting in[ "Default"]:#, "pathcut2", "mircut2","gomor2"]: #"CutFactor10", "emphasis0","emphasis1",
                                                    #"emphasis2", "emphasis3", "emphasis4", "localbranching","heuristicfreq10", "feasibilitypomp0" ,"feasibilitypomp1",
                                                    #"feasibilitypomp2", "BB" ,"flowcovers1", "flowcovers2", "pathcut1", "pathcut2", "gomory1", "gomor2",
                                                    #"zerohalfcut1", "zerohalfcut2" ,"mircut1", "mircut2" , "implied1" ,"implied2", "gubcovers1" , "gubcovers2",
                                                    #"disjunctive1", "disjunctive2", "disjunctive3", "covers1", "covers2",
                                                    #"covers3", "cliques1", "cliques2", "cliques3", "allcutmax", "variableselect00",
                                                    #"variableselect1", "variableselect2", "variableselect3", "variableselect4" ]:

                                    Createsolvejob(instance, distribution, model, nrscenar, generation, seed, method, mipsetting)
                                    filesolve.write("qsub ./Jobs/job_solve_%s_%s_%s_%s_%s_%s_%s_%s \n" % (
                                                    instance, distribution, model, nrscenar, generation, seed, method, mipsetting))

                                    for Policy in policyset:
                                        CreatePolicyJob(instance, distribution, model, nrscenar, generation, seed,
                                                        Policy)
                                        fileeval.write("qsub ./Jobs/job_evaluate_%s_%s_%s_%s_%s_%s_%s_%s \n" % (
                                            instance, distribution, model, nrscenar, generation, method, Policy, seed))

    for instance in InstanceSet:
        distributionset = ["NonStationary"]
        for distribution in distributionset:
            print "job_evpi_%s_%s" % (instance, distribution)
            qsub_filename = "./Jobs/job_evpi_%s_%s" % (instance, distribution)
            qsub_file = open(qsub_filename, 'w')
            qsub_file.write("""
#!/bin/bash -l
#
#$ -cwd
#$ -q idra
#$ -j y
#$ -o /home/thesim/outputjob%s%s.txt
ulimit -v 16000000
mkdir /tmp/thesim
python test.py Evaluate %s %s YQFix 1 RQMC -e -n 500 -s 0
            """ % ( instance, distribution, instance, distribution) )


  # Create the sh file
    filename = "runalljobevpi.sh"
    file = open(filename, 'w')
    file.write("""
#!/bin/bash -l
#
""")
    for instance in InstanceSet :
         distributionset = ["NonStationary"]
         for distribution in distributionset:
                file.write("qsub ./Jobs/job_evpi_%s_%s \n" % (instance, distribution) )


