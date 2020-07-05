#!/usr/bin/python
# script de lancement pour les fichiers
#!/usr/bin/python
# script de lancement pour les fichiers
import sys

import csv
from Constants import Constants

NrScenarioEvaluation = "5000"


def CreatFileNantes( name, nrscen):
    qsub_filename = "./Jobs/job_solve_%s_%s"%(name, nrscen)
    qsub_file = open(qsub_filename, 'w')
    qsub_file.write("""#!/bin/bash
# Nom du job
#SBATCH -J %s_%s
#
# Partition visee
#SBATCH --partition=SMP-medium
#
# Nombre de noeuds
#SBATCH --nodes=1
# Nombre de processus MPI par noeud
#SBATCH --ntasks-per-node=1
#SBATCH --mem 40000
#
# Temps de presence du job
#SBATCH --time=40:00:00
#
# Adresse mel de l'utilisateur
#
# Envoi des mails
#SBATCH --mail-type=abort,end
#SBATCH --mail-user=simon.thevenin@imt-atlantique.fr
#
#SBATCH -o /home/LS2N/thevenin-s/log/job_mpi-%s-%s.out

module purge
module load intel/2016.3.210
module load intel/mkl/64/2016.3.210
module load intel/mpi/2016.3.210
module load python/2.7.12
module load intel/mkl/64/2017.4.196
module load compilateurs_interpreteurs/gcc/7.3.0

export LD_PRELOAD=/lib64/psm2-compat/libpsm_infinipath.so.1

# Faire le lien entre SLURM et Intel MPI
export I_MPI_PMI_LIBRARY=/usr/lib64/libpmi.so

srun python test.py Solve %s HeuristicYFix  %s RQMC -m MIP -n 0

"""%(name, nrscen, name, nrscen, name, nrscen))


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
ulimit -v 30000000
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
ulimit -v 30000000
mkdir -p /tmp/thesim
mkdir -p /tmp/thesim/Evaluations
mkdir -p /tmp/thesim/Solutions
mkdir -p /tmp/thesim/CPLEXLog
python test.py Evaluate %s %s %s %s  -s %s -p %s -n %s
""" % (instance,  model, nrscenar, generation, seed, Policy, NrScenarioEvaluation, instance, model, nrscenar,
        generation, seed, Policy, NrScenarioEvaluation))


def CreateRHJob(instance, model, nrscenar,  seed,  timehorizon ):
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
ulimit -v 30000000
mkdir -p /tmp/thesim
mkdir -p /tmp/thesim/Evaluations
mkdir -p /tmp/thesim/Solutions
mkdir -p /tmp/thesim/CPLEXLog
python test.py Evaluate %s %s %s RQMC  -s %s -p RH -n %s --timehorizon %s
""" % (instance, model, nrscenar, seed,  NrScenarioEvaluation, timehorizon,
       instance, model, nrscenar, seed,  NrScenarioEvaluation, timehorizon))

if __name__ == "__main__":

    csvfile = open("./Instances/InstancesToSolveSensitivity.csv", 'rb')
    data_reader = csv.reader(csvfile, delimiter=",", skipinitialspace=True)
    instancenameslist = []
    for row in data_reader:
        instancenameslist.append(row)
    InstanceSet = instancenameslist[0]
    InstanceSet = ["01", "02", "03", "04", "05", "06", "07",
                   "08", "09", "10", "11", "12", "13", "14", "15",
                   "16", "17", "18", "19", "20", "21", "22", "23", "24",
                   "25", "26", "27",
                   "28", "29", "30", "31", "32", "33", "34", "35",
                   "36", "37", "38", "39"]
    for instance in InstanceSet:
        iname = instance+"_NonStationary_b4_fe25_en_rk50_ll0_l40_HFalse_c2"
        CreatFileNantes(iname, "4")
        #CreatFileNantes(iname, "3200")
        #CreatFileNantes(iname, "6400b")
        # Create the sh file
    filename = "runallNantes.sh"
    file = open(filename, 'w')
    file.write("""
#!/bin/bash -l
#
""")
    for instance in InstanceSet:
        iname = instance + "_NonStationary_b4_fe25_en_rk50_ll0_l40_HFalse_c2"
        file.write("sbatch ./Jobs/job_solve_%s_%s \n" % (iname, "4"))
        #file.write("sbatch ./Jobs/job_solve_%s_%s \n" % (iname, "3200"))
        #file.write("sbatch ./Jobs/job_solve_%s_%s \n" % (iname, "6400b"))
    if False:
        csvfile = open("./Instances/InstancesToSolve.csv", 'rb')
        data_reader = csv.reader(csvfile, delimiter=",", skipinitialspace=True)
        instancenameslist = []
        for row in data_reader:
           instancenameslist.append(row)
        InstanceSet = instancenameslist[0]
        instancetosolvename = ""
        policyyqfix = ["Fix", "Re-solve"]
        policyyfix = ["Re-solve"]
        Generationset = ["RQMC", "MC"]
        scenarsetall = ["4096"]
        Nrseed = 1
        if sys.argv[1] == "preliminary":
            modelset = [  "AverageSS", "AverageSSGrave", "Average",  "L4L", "EOQ", "POQ", "SilverMeal",  "YQFix",  "YFix", "HeuristicYFix", "SFix" ]
            modelset = ["YQFix",  "YFix"]
            nrcenarioysfix= [ "10", "25", "50", "100"]
            nrcenarioyfqix = [ "10", "25", "50", "100", "200", "500", "1000"]
            nrcenarioyfix = ["800", "1600", "3200", "6400a", "6400b", "6400c", "12800", "25600", "51200b"]



            Generationset = ["QMC"]
            nrcenarioheuristicyfix = ["800", "1600", "3200", "6400a", "6400b", "6400c", "12800", "25600", "51200b",
                                      "102400b", "153600"]
            instancetosolvename = "./Instances/InstancesToSolve.csv"
    #        instancetosolvename = "./Instances/InstancesToSolveUncapacitated.csv"

        if sys.argv[1] == "sensitivity":
            modelset = ["AverageSS", "AverageSSGrave", "Average", "L4L", "EOQ", "POQ", "SilverMeal", "YQFix", "YFix",
                        "HeuristicYFix"]
            modelset = ["L4LGrave", "EOQGrave", "POQGrave"]#"AverageSSGrave", "L4L", "EOQ", "POQ", "SilverMeal", "L4LGrave", "EOQGrave", "POQGrave", "SilverMealGrave"]
            nrcenarioyfqix = [ "500"]
            nrcenarioyfix = ["6400b", "6400c"]

            Generationset = ["RQMC"]
            nrcenarioheuristicyfix = ["6400b"]
            instancetosolvename = "./Instances/InstancesToSolveSensitivity.csv"

        if sys.argv[1] == "multipleseed":
            Nrseed = 5
            modelset = [  "YQFix",  "YFix", "HeuristicYFix" ]
            Generationset = ["RQMC"]
            nrcenarioyfqix = [ "500"]
            nrcenarioyfix = ["6400b",  "6400c"]
            nrcenarioheuristicyfix = ["6400b"]
            instancetosolvename = "./Instances/InstancesToSolve.csv"

        if sys.argv[1] == "Policy":
            modelset = [ "YFix" ]
            #modelset = ["L4L", "EOQ", "POQ", "SilverMeal"]
            nrcenarioyfix = ["6400b"]
            Generationset = ["RQMC"]
            instancetosolvename = "./Instances/InstancesToSolve.csv"

        if sys.argv[1] == "perfectinfo":
            modelset = [ "YQFix", "YFix", "HeuristicYFix"]

            nrcenarioyfix =[  "6400b" ]
            nrcenarioheuristicyfix = ["6400b"]
            nrcenarioyfqix = [ "500"]
            Generationset = ["all",  "RQMC"]
            instancetosolvename = "./Instances/InstancesToSolveBinomial.csv"
        #nrcenarioheuristicyfix = ["6400b"]

        if sys.argv[1] == "rollinghorizon":

            modelset = [  "AverageSS", "Average", "AverageSSGrave",  "YQFix", "HeuristicYFix"]
            modelset = [ "HeuristicYFix"]
            nrcenarioyfix =[  "6400b" ]
            nrcenarioheuristicyfix = ["6400b"]
            nrcenarioyfqix = [ "500"]
            Generationset = ["RQMC"]
            NrScenarioEvaluation = "100"
            instancetosolvename = "./Instances/InstancesToSolveRH.csv"

        if sys.argv[1] == "rollinghorizon2":

            modelset = [ "YQFix", "AverageSS", "AverageSSGrave", "Average"]
            #modelset = [ "AverageSS"]
            nrcenarioyfix =[  "6400b" ]
            nrcenarioheuristicyfix = ["6400c"]
            nrcenarioyfqix = [ "100"]
            Generationset = ["RQMC"]
            NrScenarioEvaluation = "100"
            instancetosolvename = "./Instances/InstancesToSolveRH.csv"


        #policyyqfix = [  "Fix", "Re-solve" ]
        #policyyfix = [  "Fix" ]
        #Generationset = [ "RQMC" ]
        #Generationset = ["all", "MC", "RQMC"]

        methodset = ["MIP"]


        csvfile = open(instancetosolvename, 'rb')
        data_reader = csv.reader(csvfile, delimiter=",", skipinitialspace=True)
        instancenameslist = []
        for row in data_reader:
            instancenameslist.append(row)
        InstanceSet = instancenameslist[0]

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
        fileevalname = "runalljobrollinghorizon.sh"
        fileeval = open(fileevalname, 'w')
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
                         scenarsetsampling= nrcenarioyfix
                         generationset = Generationset
                         policyset = policyyfix
                     if model == "HeuristicYFix":
                         scenarsetsampling = nrcenarioheuristicyfix
                         generationset = Generationset
                         policyset = policyyfix
                     if model == "YQFix"  or model == "SFix" or model == "YSFix":
                         scenarsetsampling = nrcenarioyfqix
                         policyset = policyyqfix
                         generationset = Generationset
                     if model == "YSFix":
                         scenarsetsampling = nrcenarioysfix
                         policyset = policyyqfix
                         generationset = Generationset

                     if model == "Average" or model == "AverageSS"  or model == "AverageSSGrave" or model =="L4L" or  model == "EOQ" or  model == "POQ" or  model =="SilverMeal" \
                             or model == "L4LGrave" or model == "EOQGrave" or model == "POQGrave" or model == "SilverMealGrave":
                         scenarsetsampling = ["1"]
                         avg = True
                         generationset = ["MC"]
                         policyset = policyyqfix
                     for method in methodset:
                         for generation in generationset:
                             if generation == "all":
                                 scenarset = scenarsetall
                             else:
                                 scenarset = scenarsetsampling
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

                                        timehorizonrange = [1, 3, 5]

                                        if model == "HeuristicYFix":
                                            timehorizonrange = [1, 3]
                                        if model == "L4L" or model == "EOQ" or model == "POQ" or model == "SilverMeal":
                                            timehorizonrange = [ 5 ]

                                        for th in timehorizonrange :
                                            CreateRHJob(instance, model, nrscenar,  seed,  timehorizon = th)
                                            fileeval.write("qsub ./Jobs/job_evaluaterh_%s_%s_%s_%s_%s_%s \n" % (
                                                instance, model, nrscenar, seed, NrScenarioEvaluation, th) )


        for instance in InstanceSet:
            for seed in range(Nrseed):
                print "job_evpi_%s " % (instance )
                qsub_filename = "./Jobs/job_evpi_%s" % (instance )
                qsub_file = open(qsub_filename, 'w')
                allscenario = 0
                if 'Binomial' in instance:
                    allscenario = 1
                    NrScenarioEvaluation = 4096
                qsub_file.write("""
    #!/bin/bash -l
    #
    #$ -cwd
    #$ -q idra
    #$ -j y
    #$ -o /home/thesim/log/outputjob%s.txt
    ulimit -v 30000000
    mkdir -p /tmp/thesim
    mkdir -p /tmp/thesim/Evaluations
    mkdir -p /tmp/thesim/Solutions
    mkdir -p /tmp/thesim/CPLEXLog
    python test.py Evaluate %s YQFix 1 RQMC -e -n %s -s 0 -a %s
                """ % ( instance, instance, NrScenarioEvaluation, allscenario) )


      # Create the sh file
        filename = "runalljobevpi.sh"
        file = open(filename, 'w')
        file.write("""
    #!/bin/bash -l
    #
    """)
        for instance in InstanceSet :
                  file.write("qsub ./Jobs/job_evpi_%s \n" % (instance) )


