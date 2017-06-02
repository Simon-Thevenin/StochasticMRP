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

    for f in ["01"]:  # , "02", "03", "04", "05" ]:# "06", "07", "08", "09",
        #			  "10", "11", "12", "13", "14", "15", "16", "17", "18", "19",
        #			  "20", "21", "22", "23", "24", "25", "26", "27", "28", "29",
        #			  "30", "31", "32", "33", "34", "35", "36", "37", "38"]:
        for b in ["SlowMoving", "Normal", "Lumpy"]:  # "02", "03", "04", "05", "06", "07", "08", "09", "10"]:
            for m in ["YFix", "YQFix"]:  # , "YFix", "_Fix" ]:
                for generation in ["MC", "RQMC"]:
                    scenarset = ["512"]
                    policyset = [ "NearestNeighbor", "Re-solve"]
                    scenarioasYPset = ["False", "True"]
                    avg = False
                    if m == "YQFix":
                        scenarset = ["2", "4", "8", "50", "100", "200", "500"]
                        policyset = [ "Fix" ]
                        scenarioasYPset =  ["False"  ]
                        scenarioasYP = False
            # if m == "Average":
            #			scenarset =  [ "1" ]

            #			avg = True
                    for scenarioasYP in scenarioasYPset:
                          for Policy in policyset:  # , "07", "08", "09", "10"]:
                             for nrscenar in scenarset:
                                qsub_filename = "job_%s_%s_%s_%s_%s_%s_%s_%s" % (
                                f, m, avg, b, nrscenar, scenarioasYP, Policy, generation)
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
python test.py %s 05 %s %s %s %s %s %s %s 2000
""" % ( f, m, avg, scenarioasYP, Policy, b, nrscenar,
       generation))
# Create the sh file
filename = "runalljobs.sh"
file = open(filename, 'w')
file.write("""
#!/bin/bash -l
#
""")
for f in ["01"]:  # , "02", "03", "04", "05" ]:# "06", "07", "08", "09",
    #			  "10", "11", "12", "13", "14", "15", "16", "17", "18", "19",
    #			  "20", "21", "22", "23", "24", "25", "26", "27", "28", "29",
    #			  "30", "31", "32", "33", "34", "35", "36", "37", "38"]:
    for b in ["SlowMoving", "Normal", "Lumpy"]:  # "02", "03", "04", "05", "06", "07", "08", "09", "10"]:
        for m in ["YFix", "YQFix"]:  # , "YFix", "_Fix" ]:
            for generation in ["MC", "RQMC"]:
                scenarset = ["512"]
                policyset = ["NearestNeighbor", "Re-solve"]
                scenarioasYPset = ["False", "True"]
                avg = False
                if m == "YQFix":
                    scenarset = ["2", "4", "8", "50", "100", "200", "500"]
                    policyset = ["Fix"]
                    scenarioasYPset = ["False"]
                    scenarioasYP = False
                    # if m == "Average":
                    #			scenarset =  [ "1" ]

                    #			avg = True
                for scenarioasYP in scenarioasYPset:
                    for Policy in policyset:  # , "07", "08", "09", "10"]:
                        for nrscenar in scenarset:
                            file.write("qsub job_%s_%s_%s_%s_%s_%s_%s_%s \n" % (
                            f, m, avg, b, nrscenar, scenarioasYP, Policy, generation))
