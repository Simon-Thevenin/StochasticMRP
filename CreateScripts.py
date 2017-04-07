#!/usr/bin/python
#script de lancement pour les fichiers 


import os
import subprocess

if __name__=="__main__":

	#Path to the program you want to run
	exec_file=r"/home/thesim/TestFolder/stochasticmrp/"

	#Path to a folder containing the data set you want to run your program on.
	#Your program will be run on every file in the folder but the files whose names start by '.' (hidden files)
	data_folder=r"/home/isabel/Models/OneT/Data/no_trend"
	
	#Path to a folder where you want your results to be
	output_folder=r"/home/thesim/TestFolder/stochasticmrp/"

	for f in ["01", "02", "03", "04", "05", "06", "07", "08", "09", 
			  "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", 
			  "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", 
			  "30", "31", "32", "33", "34", "35", "36", "37", "38"]:
		for b in [ "02", "03", "04", "05", "06", "07", "08", "09", "10"]:
			qsub_filename = "job_%s_%s"%(f, b)
			qsub_file=open(qsub_filename, 'w')
			qsub_file.write("""
#!/bin/bash -l
#
#$ -cwd
#$ -q idra
#$ -j y
#$ -o /home/thesim/outputjob.txt
python test.py %s %s
""" %(f, b) )


#Create the sh file
filename = "runalljobs.sh"
file=open(filename, 'w')
file.write("""
#!/bin/bash -l
#
""" ) 
for f in ["01", "02", "03", "04", "05", "06", "07", "08", "09", 
			  "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", 
			  "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", 
			  "30", "31", "32", "33", "34", "35", "36", "37", "38"]:
    for b in [ "02", "03", "04", "05", "06", "07", "08", "09", "10"]:
	        file.write("qsub job_%s_%s \n"%(f, b) )