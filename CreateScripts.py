#!/usr/bin/python
# script de lancement pour les fichiers


import os
import subprocess

if __name__ == "__main__":

    # Path to the program you want to run
    exec_file = r"/home/thesim/TestFolder/stochasticmrp/"

    # Path to a folder containing the data set you want to run your program on.
    # Your program will be run on every file in the folder but the files whose names start by '.' (hidden files)
    data_folder = r"/home/isabel/Models/OneT/Data/no_trend"

    # Path to a folder where you want your results to be
    output_folder = r"/home/thesim/TestFolder/stochasticmrp/"

    for instance in ["00", "01", "02", "03", "04", "05", "01_LTH", "02_LTH", "03_LTH", "04_LTH", "05_LTH" ]:
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
            for model in ["YFix", "YQFix", "Average"]:
                 generationset = ["MC", "RQMC"]
                 if instance == "00" or instance == "01":
                     generationset = ["MC", "RQMC", "all"]
                 scenarset = [ "512"]
                 policyset = [ "NNDAC", "NNSAC", "Re-solve"]
                 method = "MIP"
                 avg = False
                 if model == "YQFix":
                     scenarset = [ "1000" ]
                     #scenarset = ["2", "4", "8", "50", "100", "200", "500", "1000"]
                     policyset = [ "Fix" ]

                 if model == "Average":
                     scenarset =  [ "1" ]
                     avg = True
                     policyset = ["Fix"]
                     generationset = ["MC"]
                 for generation in generationset:
                     for nrscenar in scenarset:
                        for seed in range( 5 ):
                            qsub_filename = "job_solve_%s_%s_%s_%s_%s_%s_MIP" % (
                                    instance, distribution, model, nrscenar, generation, seed  )
                            qsub_file = open(qsub_filename, 'w')
                            qsub_file.write("""
#!/bin/bash -l
#
#$ -cwd
#$ -q idra
#$ -j y
#$ -o /home/thesim/outputjob%s%s%s%s%s%s.txt
ulimit -v 16000000
mkdir /tmp/thesim
python test.py Solve %s %s %s %s %s -s %s  -n 500 -m MIP
""" % ( instance, distribution, model, nrscenar, generation, seed,  instance, distribution, model, nrscenar, generation, seed  ))  # Create the sh file
                            for Policy in policyset:
                                     qsub_filename = "job_evaluate_%s_%s_%s_%s_%s_%s_%s_%s" % (
                                       instance, distribution, model, nrscenar, generation, method, Policy, seed)
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
 """ % (instance, distribution, model, nrscenar, generation, seed, Policy, instance, distribution, model,
                                nrscenar, generation, seed, Policy) )

filename = "runalljobs.sh"
file = open(filename, 'w')
file.write("""
#!/bin/bash -l
#
""")

# for instance in ["01", "02", "03", "04", "05" ]:
#      for distribution in ["SlowMoving", "Normal", "Lumpy", "Uniform", "NonStationary"]:
#          for model in ["YFix" ]:#, "YQFix", "Average"]:
#              generationset = ["RQMC",  "MC"]
#              scenarset = ["512"]
#              policyset = [ "NNDAC", "NNSAC", "NND", "NNS" ]
#              method = "MIP"
#              avg = False
#              if model == "YQFix":
#                  scenarset = ["2", "4", "8", "50", "100", "200", "500"]
#                  policyset = ["Fix"]
#
#              if model == "Average":
#                  scenarset = ["1"]
#                  avg = True
#                  policyset = ["Fix"]
#                  generationset = ["MC"]
#              for generation in generationset:
#                  for nrscenar in scenarset:
#                      for seed in range(5):
#                              file.write("qsub job_solve_%s_%s_%s_%s_%s_%s \n" % (
#                                      instance, distribution, model, nrscenar, generation, seed  ) )

#for instance in ["01_LTH", "02_LTH", "03_LTH", "04_LTH", "05_LTH"]:
for instance in ["00", "01", "02", "03", "04", "05", "01_LTH", "02_LTH", "03_LTH", "04_LTH", "05_LTH"]:
    distributionset = ["NonStationary"]
    # distributionset = ["SlowMoving", "Normal", "Lumpy", "NonStationary"]
    if instance == "00":
        distributionset = ["Binomial"]
    if instance == "01":
        distributionset = ["Uniform", "NonStationary"]
        #     distributionset = ["SlowMoving", "Normal", "Lumpy", "Uniform", "NonStationary"]
    for distribution in distributionset:
        # model = "YFix"
        # nrscenar = 500
        # generation = "RQMC"
        for model in ["YQFix"]:
            generationset = ["MC", "RQMC"]
            if instance == "00" or instance == "01":
                generationset = ["MC", "RQMC", "all"]
            scenarset = ["512"]
            policyset = ["NNDAC", "NNSAC", "Re-solve"]
            method = "MIP"
            avg = False
            if model == "YQFix":
                scenarset = ["1000"]
                # scenarset = ["2", "4", "8", "50", "100", "200", "500", "1000"]
                policyset = ["Fix"]

            if model == "Average":
                scenarset = ["1"]
                avg = True
                policyset = ["Fix"]
                generationset = ["MC"]
            for generation in generationset:
                if generation == "all":
                    scenarset = "8"
                for nrscenar in scenarset:
                    for seed in range(5):
                            file.write("qsub job_solve_%s_%s_%s_%s_%s_%s_MIP \n" % (
                                    instance, distribution, model, nrscenar, generation, seed  )
                            )