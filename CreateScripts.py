#!/usr/bin/python
# script de lancement pour les fichiers
#!/usr/bin/python
# script de lancement pour les fichiers


import csv
from Constants import Constants

NrScenarioEvaluation = "5000"

def Createsolvejob(instance, model, nrscenar, generation, seed, method, mipsetting):
    print "job_solve_%s_%s_%s_%s_%s_%s_%s" % (
        instance, model, nrscenar, generation, seed, method, mipsetting)
    qsub_filename = "./Jobs/job_solve_%s_%s_%s_%s_%s_%s_%s" % (
        instance, model, nrscenar, generation, seed, method, mipsetting)
    qsub_file = open(qsub_filename, 'w')
    qsub_file.write("""
#!/bin/bash -l
#
#$ -cwd
#$ -q idra
#$ -j y
#$ -o /home/thesim/log/outputjob%s%s%s%s%s%s%s.txt
ulimit -v 16000000
mkdir -p /tmp/thesim
mkdir -p /tmp/thesim/Evaluations
mkdir -p /tmp/thesim/Solutions
mkdir -p /tmp/thesim/CPLEXLog
python test.py Solve %s %s %s %s -s %s  -m %s --mipsetting %s -n %s
""" % (instance, model, nrscenar, generation, seed, method, mipsetting, instance,
                          model, nrscenar, generation, seed, method, mipsetting, NrScenarioEvaluation))


def CreatePolicyJob(instance, model, nrscenar, generation, seed, Policy):
    qsub_filename = "./Jobs/job_evaluate_%s_%s_%s_%s_%s_%s_%s" % (
        instance, model, nrscenar, generation, method, Policy, seed)
    qsub_file = open(qsub_filename, 'w')
    qsub_file.write("""
#!/bin/bash -l
#
#$ -cwd
#$ -q idra
#$ -j y
#$ -o /home/thesim/log/outputjobevaluate%s%s%s%s%s%s%s.txt
ulimit -v 16000000
mkdir -p /tmp/thesim
mkdir -p /tmp/thesim/Evaluations
mkdir -p /tmp/thesim/Solutions
mkdir -p /tmp/thesim/CPLEXLog
python test.py Evaluate %s %s %s %s  -s %s -p %s -n %s
""" % (instance,  model, nrscenar, generation, seed, Policy, NrScenarioEvaluation, instance, model, nrscenar,
        generation, seed, Policy, NrScenarioEvaluation))


def CreateRHJob(instance, model, nrscenar, generation, seed, Policy, timehorizon ):
    qsub_filename = "./Jobs/job_evaluaterh_%s_%s_%s_%s_%s_%s" % (
        instance, model, nrscenar, seed, NrScenarioEvaluation, timehorizon)
    qsub_file = open(qsub_filename, 'w')
    qsub_file.write("""
#!/bin/bash -l
#
#$ -cwd
#$ -q idra
#$ -j y
#$ -o /home/thesim/log/outputjobevaluate%s%s%s%s%s%s.txt
ulimit -v 16000000
mkdir -p /tmp/thesim
mkdir -p /tmp/thesim/Evaluations
mkdir -p /tmp/thesim/Solutions
mkdir -p /tmp/thesim/CPLEXLog
python test.py Evaluate %s %s %s RQMC  -s %s -p RH -n %s --timehorizon %s
""" % (instance, model, nrscenar, seed,  NrScenarioEvaluation, timehorizon,
       instance, model, nrscenar, seed,  NrScenarioEvaluation, timehorizon))

if __name__ == "__main__":
    csvfile = open("./Instances/InstancesToSolve.csv", 'rb')
    data_reader = csv.reader(csvfile, delimiter=",", skipinitialspace=True)
    instancenameslist = []
    for row in data_reader:
       instancenameslist.append(row)
    InstanceSet = instancenameslist[0]
    modelset = [ "Average", "AverageSS", "YQFix", "YFix",  "L4L", "EOQ", "POQ", "SilverMeal" ]#, "HeuristicYFix", "YFix", "YQFix"]
    #modelset = ["L4L", "EOQ", "POQ", "SilverMeal"]
    #nrcenarioyfix =[  "800", "1600", "3200", "6400a", "6400b", "6400c",  "12800", "25600", "51200b", "102400b", "153600" ]
    #nrcenarioyfqix = [ "10", "25", "50", "1q00", "200", "500", "1000"]
    #nrcenarioheuristicyfix = ["6400b",  "102400b"]

    #policyyqfix = ["Fix", "Re-solve"]
    #policyyfix = ["Re-solve"]
    #Generationset = [ "RQMC",  "MC" ]

    nrcenarioyfix =[  "6400b" ]
    nrcenarioyfqix = [ "200"]
    nrcenarioheuristicyfix = ["6400b",  "102400b"]

    policyyqfix = [ "RH", "Fix", "Re-solve" ]
    policyyfix = [ "RH", "Fix" ]
    Generationset = [ "RQMC" ]


    methodset = ["MIP"]
    Nrseed = 1

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

    # Create the sh file for resolution
    fileeval = "runalljobrollinghorizon.sh"
    fileeval = open(filesolvename, 'w')
    fileeval.write("""
    #!/bin/bash -l
    #
    """)

    for instance in InstanceSet :
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
                 if model == "Average" or model == "AverageSS" or model =="L4L" or  model == "EOQ" or  model == "POQ" or  model =="SilverMeal":
                     scenarset = ["1"]
                     avg = True
                     generationset = ["MC"]
                     policyset = policyyqfix
                 for method in methodset:
                     for generation in generationset:
                         for nrscenar in scenarset:
                             for seed in range(Nrseed):
                                   for mipsetting in[ "Default"]:

                                    Createsolvejob(instance, model, nrscenar, generation, seed, method, mipsetting)
                                    filesolve.write("qsub ./Jobs/job_solve_%s_%s_%s_%s_%s_%s_%s \n" % (
                                                    instance, model, nrscenar, generation, seed, method, mipsetting))

                                    if Constants.RunEvaluationInSeparatedJob:
                                        for Policy in policyset:
                                            CreatePolicyJob(instance, model, nrscenar, generation, seed,
                                                            Policy)
                                            fileeval.write("qsub ./Jobs/job_evaluate_%s_%s_%s_%s_%s_%s_%s \n" % (
                                                instance, model, nrscenar, generation, method, Policy, seed))

                                    CreateRHJob(instance, model, nrscenar, generation, seed, Policy, timehorizon = 1)
                                    CreateRHJob(instance, model, nrscenar, generation, seed, Policy, timehorizon = 3)
                                    fileeval.write("qsub ./Jobs/job_evaluaterh_%s_%s_%s_%s_%s_%s \n" % (
                                        instance, model, nrscenar, seed, NrScenarioEvaluation, 1) )
                                    fileeval.write("qsub ./Jobs/job_evaluaterh_%s_%s_%s_%s_%s_%s \n" % (
                                        instance, model, nrscenar, seed, NrScenarioEvaluation, 2) )
                                    fileeval.write("qsub ./Jobs/job_evaluaterh_%s_%s_%s_%s_%s_%s \n" % (
                                        instance, model, nrscenar, seed, NrScenarioEvaluation, 3) )

    for instance in InstanceSet:
        print "job_evpi_%s" % (instance )
        qsub_filename = "./Jobs/job_evpi_%s" % (instance )
        qsub_file = open(qsub_filename, 'w')
        qsub_file.write("""
#!/bin/bash -l
#
#$ -cwd
#$ -q idra
#$ -j y
#$ -o /home/thesim/log/outputjob%s.txt
ulimit -v 16000000
mkdir -p /tmp/thesim
mkdir -p /tmp/thesim/Evaluations
mkdir -p /tmp/thesim/Solutions
mkdir -p /tmp/thesim/CPLEXLog
python test.py Evaluate %s YQFix 1 RQMC -e -n 5000 -s 0
            """ % ( instance, instance) )


  # Create the sh file
    filename = "runalljobevpi.sh"
    file = open(filename, 'w')
    file.write("""
#!/bin/bash -l
#
""")
    for instance in InstanceSet :
              file.write("qsub ./Jobs/job_evpi_%s \n" % (instance) )


