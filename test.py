#from __future__ import absolute_import, division, print_function
from __future__ import division
from matplotlib import pyplot as PLT

import cplex
import pandas as pd
import openpyxl as opxl
from MRPInstance import MRPInstance
from MRPSolution import MRPSolution
from MIPSolver import MIPSolver
from ScenarioTreeNode import ScenarioTreeNode
from ScenarioTree import ScenarioTree
import time
import sys
import numpy as np
import csv
import math
from datetime import datetime
from matplotlib import pyplot as plt
import cPickle as pickle
from Constants import Constants
from Evaluator import Evaluator
from SDDP import SDDP
import argparse
import subprocess

import glob as glob
#pass Debug to true to get some debug information printed

Action = ""
InstanceName = ""
Distribution = ""

Instance = MRPInstance()
AverageInstance = MRPInstance()

#If UseNonAnticipativity is set to true a variable per scenario is generated, otherwise only the required variable a created.
EVPI = False
#ActuallyUseAnticipativity is set to False to compute the EPVI, otherwise, it is set to true to add the non anticipativity constraints
#UseInmplicitAnticipativity = False
#PrintScenarios is set to true if the scenario tree is printed in a file, this is usefull if the same scenario must be reloaded in a ater test.
PrintScenarios = False
NrScenario = -1

#The attribut model refers to the model which is solved. It can take values in "Average, YQFix, YFix,_Fix"
# which indicates that the avergae model is solve, the Variable Y and Q are fixed at the begining of the planning horizon, only Y is fix, or everything can change at each period
Model = "YFix"
Method = "MIP"
ComputeAverageSolution = False

#How to generate a policy from the solution of a scenario tree
PolicyGeneration = "NearestNeighbor"
NearestNeighborStrategy = ""
NrEvaluation = 500
ScenarioGeneration = "MC"
#When a solution is obtained, it is recorded in Solution. This is used to compute VSS for instance.
Solution = None
#Evaluate solution is true, the solution in the variable "GivenQuantities" is given to CPLEX to compute the associated costs
EvaluateSolution = False
FixUntilTime = 0
GivenQuantities =[]
GivenSetup = []
VSS = []
ScenarioSeed = 1
SeedIndex = -1
TestIdentifier = []
EvaluatorIdentifier = []
SeedArray = [ 2934, 875, 3545, 765, 546, 768, 242, 375, 142, 236, 788 ]

#This list contain the information obtained after solving the problem
SolveInformation = []
OutOfSampleTestResult = []
InSampleKPIStat= [ 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0  ]
EvaluateInfo = []
OptimizationInfo = [0,0]

def PrintTestResult():
    Parameter =  [ UseNonAnticipativity, Model, ComputeAverageSolution, ScenarioSeed ]
    data = TestIdentifier + SolveInformation +  Parameter
    d = datetime.now()
    date = d.strftime('%m_%d_%Y_%H_%M_%S')
    myfile = open(r'./Test/SolveInfo/TestResult_%s.csv' % (GetTestDescription()), 'wb')
    wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
    wr.writerow( data )
    myfile.close()

def PrintFinalResult():
    data = TestIdentifier + EvaluatorIdentifier + OptimizationInfo+  InSampleKPIStat + OutOfSampleTestResult
    d = datetime.now()
    date = d.strftime('%m_%d_%Y_%H_%M_%S')
    print "print the test result ./Test/TestResult_%s_%s.csv" % (GetTestDescription(), GetEvaluateDescription())
    myfile = open(r'./Test/TestResult_%s_%s.csv' % (GetTestDescription(), GetEvaluateDescription()), 'wb')
    wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
    wr.writerow( data )
    myfile.close()

#This function creates the CPLEX model and solves it.
def MRP( treestructur = [ 1, 8, 8, 4, 2, 1, 0 ], averagescenario = False, recordsolveinfo = False ):

    global SolveInformation
    global CompactSolveInformation


    scenariotree = ScenarioTree( Instance, treestructur, ScenarioSeed,
                                     averagescenariotree=averagescenario,
                                     scenariogenerationmethod = ScenarioGeneration,
                                     generateRQMCForYQfix = ( Model  == Constants.ModelYQFix and ScenarioGeneration == Constants.RQMC ),
                                 model= Model)



    MIPModel = Model
    if Model == Constants.Average:
        MIPModel = Constants.ModelYQFix

    mipsolver = MIPSolver(Instance, MIPModel, scenariotree, evpi = EVPI,
                          implicitnonanticipativity=(not EVPI),
                          evaluatesolution = EvaluateSolution,
                          givenquantities = GivenQuantities,
                          givensetups = GivenSetup,
                          fixsolutionuntil = FixUntilTime )
    if Constants.Debug:
        Instance.PrintInstance()
        for s in mipsolver.ScenarioSet:
            print "demand scenario %d:%r"%( s,mipsolver.Scenarios[s].Demands)
    if PrintScenarios:
        mipsolver.PrintScenarioToFile(  )

    if Constants.Debug:
        print "Start to model in Cplex"
    mipsolver.BuildModel()
    if Constants.Debug:
        print "Start to solve instance %s with Cplex"% Instance.InstanceName;


    scenario = mipsolver.Scenarios
    #demands = [ [ [ scenario[w].Demands[t][p] for w in mipsolver.ScenarioSet ] for p in Instance.ProductSet ] for t in Instance.TimeBucketSet ]
    # for t in Instance.TimeBucketSet:
    #     for p in Instance.ProductWithExternalDemand:
    #         print "The demands for product %d at time %d : %r" %(p, t, demands[t][p] )
    #         with open('Histp%dt%d.csv'%(p, t), 'w+') as f:
    #             #v_hist = np.ravel(v)  # 'flatten' v
    #             fig = PLT.figure()
    #             ax1 = fig.add_subplot(111)
    #
    #             n, bins, patches = ax1.hist(demands[t][p], bins=100, normed=1, facecolor='green')
    #             PLT.show()
    solution = mipsolver.Solve()
   # result = solution.TotalCost, [ [ sum( solution.Production.get_value( Instance.ProductName[ p], t, w ) *  for w in Instance.ScenarioSet ) for p in Instance.ProductSet ] for t in Instance.TimeBucketSet ]

    if Constants.Debug:
       #    solution.Print()
           description = "%r_%r" % ( Model, ScenarioSeed )
      #     solution.PrintToExcel( description )

    if recordsolveinfo:
        SolveInformation = mipsolver.SolveInfo

    return solution, mipsolver

def GetTestDescription():
    result = JoinList( TestIdentifier)
    return result

def JoinList(list):
    result = "_".join( str(elm) for elm in list)
    return result

def GetEvaluateDescription():
    result = JoinList(EvaluatorIdentifier)
    return result

def SolveYQFix( ):
    global OptimizationInfo

    if Constants.Debug:
        Instance.PrintInstance()

    average = False
    nrscenario = NrScenario
    if Model == "Average":
        average = True
        nrscenario = 1

    treestructure = [1, nrscenario] +  [1] * ( Instance.NrTimeBucket - 1 ) +[ 0 ]
    solution, mipsolver = MRP( treestructure, average, recordsolveinfo=True )
    OptimizationInfo[0] = solution.CplexTime
    OptimizationInfo[1] = solution.CplexGap
    PrintTestResult()
    PrintSolutionToFile( solution )
    if EVPI:
        PrintFinalResult()
    RunEvaluation()


def PrintSolutionToFile( solution  ):
    testdescription = GetTestDescription()
    if Constants.PrintSolutionFileToExcel:
        solution.PrintToExcel(testdescription)
    else:
        solution.PrintToPickle(testdescription)

def SolveYFix():
    global SolveInformation
    global OptimizationInfo
    if Constants.Debug:
        Instance.PrintInstance()

    treestructure = GetTreeStructure()

    if Method == "MIP" :
            solution, mipsolver = MRP(treestructure, averagescenario=False, recordsolveinfo=True)
            OptimizationInfo[0] = solution.CplexTime
            OptimizationInfo[1] = solution.CplexGap
    if Method == "SDDP":
         sddpsolver = SDDP( Instance, ScenarioSeed, nrscenarioperiteration = NrScenario, generationmethod = ScenarioGeneration  )
         sddpsolver.Run()

         SolveInformation = sddpsolver.SolveInfo
         OptimizationInfo[0] = SolveInformation[5]
         OptimizationInfo[1] = sddpsolver.CurrentUpperBound - sddpsolver.CurrentLowerBound
         evaluator = Evaluator(Instance, [], [sddpsolver], optimizationmethod = Constants.SDDP)


         OutOfSampleTestResult = evaluator.EvaluateYQFixSolution(TestIdentifier, EvaluatorIdentifier, Model,
                                                            saveevaluatetab=True, filename=GetEvaluationFileName())
    # PrintFinalResult()

    PrintTestResult()
    #if EVPI:
    #    PrintSolutionToFile(solution)
    #    ComputeInSampleStatistis()
    #    PrintFinalResult()
    if   Method == "MIP" :
        PrintSolutionToFile( solution )
        RunEvaluation()
    GatherEvaluation()

def GetPreviouslyFoundSolution():
    result = []
    for s in SeedArray:
        try:
            TestIdentifier[6] = s
            filedescription = GetTestDescription()
            solution = MRPSolution()
            solution.ReadFromFile( filedescription )
            result.append( solution )

            #for s in range(len(solution.Scenarioset)):
            #    print "Scenario with demand:%r" % solution.Scenarioset[s].Demands
            #    print "quantity %r" % [ [solution.ProductionQuantity.loc[solution.MRPInstance.ProductName[p], (time, s)] for p in
            #                           solution.MRPInstance.ProductSet ] for time in solution.MRPInstance.TimeBucketSet ]

        except IOError:
            if Constants.Debug:
                print "No solution found for seed %d"%s



    return result

def ComputeInSampleStatistis():
    global InSampleKPIStat
    solutions = GetPreviouslyFoundSolution()
    for i in range(11 + Instance.NrLevel + 51):
        InSampleKPIStat[i] =0
    for solution in solutions:
        solution.ComputeStatistics()
        insamplekpisstate = solution.PrintStatistics(TestIdentifier, "InSample", -1, 0, ScenarioSeed)
        for i in range(11 + Instance.NrLevel + 51):
            InSampleKPIStat[i] = InSampleKPIStat[i] + insamplekpisstate[i]

    for i in range(11 + Instance.NrLevel + 51):
        InSampleKPIStat[i] = InSampleKPIStat[i] / len( solutions )

def Evaluate():
    ComputeInSampleStatistis()
    global OutOfSampleTestResult
    solutions = GetPreviouslyFoundSolution()
    evaluator = Evaluator( Instance, solutions, [], PolicyGeneration, ScenarioGeneration, treestructure=GetTreeStructure(), nearestneighborstrategy= NearestNeighborStrategy )
    OutOfSampleTestResult = evaluator.EvaluateYQFixSolution( TestIdentifier, EvaluatorIdentifier,  Model )
    PrintFinalResult()

def GetEvaluationFileName():
    result = "./Evaluations/" + GetTestDescription() + GetEvaluateDescription()
    return result

def EvaluateSingleSol(  ):
   # ComputeInSampleStatistis()
    global OutOfSampleTestResult
   # solutions = GetPreviouslyFoundSolution()
    filedescription = GetTestDescription()
    solution = MRPSolution()
    solution.ReadFromFile(filedescription)
    evaluator = Evaluator( Instance, [solution], [], PolicyGeneration, evpi=EVPI, scenariogenerationresolve=ScenarioGeneration, treestructure=GetTreeStructure(), nearestneighborstrategy= NearestNeighborStrategy, evaluateaverage= (Model==Constants.Average) )

    MIPModel = Model
    if Model == Constants.Average:
        MIPModel = Constants.ModelYQFix

    OutOfSampleTestResult = evaluator.EvaluateYQFixSolution( TestIdentifier, EvaluatorIdentifier,  MIPModel, saveevaluatetab= True, filename = GetEvaluationFileName(), evpi=EVPI  )
   # PrintFinalResult()
    GatherEvaluation()

def GatherEvaluation():
    global ScenarioSeed
    currentseedvalue = ScenarioSeed
    evaluator = Evaluator(Instance, [], [], PolicyGeneration, ScenarioGeneration, treestructure=GetTreeStructure())
    EvaluationTab = []
    KPIStats = []
    nrfile = 0
    #Creat the evaluation table
    for seed in SeedArray:
        try:
            ScenarioSeed = seed
            filename =  GetEvaluationFileName()
            TestIdentifier[6] = seed
            print "open file %rEvaluator.txt"%filename
            with open(filename + "Evaluator.txt", 'rb') as f:
                list = pickle.load(f)
                EvaluationTab.append( list )
            with open(filename + "KPIStat.txt", "rb") as f:  # Pickling
                list = pickle.load(f)
                KPIStats.append( list )
                nrfile =nrfile +1
        except IOError:
            if Constants.Debug:
                print "No evaluation file found for seed %d" % seed

    if nrfile >= 1:

        KPIStat = [sum(e) / len(e) for e in zip(*KPIStats)]

        global OutOfSampleTestResult
        OutOfSampleTestResult =      evaluator.ComputeStatistic(EvaluationTab, NrEvaluation, TestIdentifier,EvaluatorIdentifier, KPIStat, -1, Model)
        if Method == Constants.MIP:
            ComputeInSampleStatistis()
        PrintFinalResult()
    ScenarioSeed = currentseedvalue
    TestIdentifier[6] = currentseedvalue



def GetTreeStructure():
    if Model == Constants.Average:
        treestructure = [1, 1] + [1] * (Instance.NrTimeBucket - 1) + [0]

    if Model == Constants.ModelYQFix:
        treestructure = [1, NrScenario] + [1] * (Instance.NrTimeBucket - 1) + [0]

    if Model == Constants.ModelYFix:
        treestructure = [1, 20, 20, 1, 1, 1, 0]

        if NrScenario == 8:
            if Instance.NrTimeBucket == 6:
                treestructure = [1, 8, 8, 8, 1, 1, 1, 0]
                # treestructure = [1, 8, 4, 2, 1, 1, 1, 0 ]
            if Instance.NrTimeBucket == 8:
                treestructure = [1, 2, 2, 2, 1, 1, 1, 1, 1, 0]
            if Instance.NrTimeBucket == 9:
                treestructure = [1, 2, 2, 2, 1, 1, 1, 1, 1, 1, 0]
            if Instance.NrTimeBucket == 10:
                treestructure = [1, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 0]
            if Instance.NrTimeBucket == 12:
                treestructure = [1, 8, 4, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0]
            if Instance.NrTimeBucket == 15:
                treestructure = [1, 4, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0]

        if NrScenario == 64:
            if Instance.NrTimeBucket == 6:
                treestructure = [1, 4, 4, 4, 1, 1, 1, 0]
                # treestructure = [1, 8, 4, 2, 1, 1, 1, 0 ]
            if Instance.NrTimeBucket == 8:
                treestructure = [1, 4, 4, 4, 4, 1, 1, 1, 1, 0]
            if Instance.NrTimeBucket == 9:
                treestructure = [1, 4, 4, 4, 4, 1, 1, 1, 1, 1, 0]
            if Instance.NrTimeBucket == 10:
                treestructure = [1, 4, 4, 4, 4, 4, 1, 1, 1, 1, 1, 0]
            if Instance.NrTimeBucket == 12:
                treestructure = [1, 8, 4, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0]
            if Instance.NrTimeBucket == 15:
                treestructure = [1, 4, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0]

        if NrScenario == 512:
            if Instance.NrTimeBucket == 6:
                # treestructure = [1, 2, 2, 2, 1, 1, 1, 0]
                treestructure = [1, 8, 8, 8, 1, 1, 1, 0]
            if Instance.NrTimeBucket == 8:
                treestructure = [1, 8, 8, 4, 2, 1, 1, 1, 1, 0]
            if Instance.NrTimeBucket == 9:
                treestructure = [1, 8, 8, 4, 2, 1, 1, 1, 1, 1, 0]
            if Instance.NrTimeBucket == 10:
                treestructure = [1, 8, 8, 2, 2, 2, 1, 1, 1, 1, 1, 0]
            if Instance.NrTimeBucket == 12:
                treestructure = [1, 8, 4, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0]
            if Instance.NrTimeBucket == 15:
                treestructure = [1, 4, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0]

        if NrScenario == 1024:
            if Instance.NrTimeBucket == 6:
                # treestructure = [1, 2, 2, 2, 1, 1, 1, 0]
                treestructure = [1, 32, 8, 4, 1, 1, 1, 0]
            if Instance.NrTimeBucket == 9:
                treestructure = [1, 8, 4, 4, 2, 2, 2, 1, 1, 1, 0]
            if Instance.NrTimeBucket == 12:
                treestructure = [1, 4, 4, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 0]
            if Instance.NrTimeBucket == 15:
                treestructure = [1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 0]

        if NrScenario == 8192:
            if Instance.NrTimeBucket == 6:
                treestructure = [1, 25, 25, 25, 1, 1, 1, 0]
            if Instance.NrTimeBucket == 9:
                treestructure = [1, 8, 4, 4, 4, 4, 4, 1, 1, 1, 0]
            if Instance.NrTimeBucket == 12:
                treestructure = [1, 8, 4, 4, 4, 2, 2, 2, 2, 1, 1, 1, 1, 0]
            if Instance.NrTimeBucket == 15:
                treestructure = [1, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 0]

    return treestructure




#This function compute some statistic about the genrated trees. It is usefull to check if the generator works as expected.
def ComputeAverageGeneraor():
    offset=1000
    nrscenario = 10000
    Average = [ 0  ] * Instance.NrProduct
    data = [0] * nrscenario
    for myseed in range(offset, nrscenario + offset, 1):
        #Generate a random scenario
        tree = ScenarioTree(  instance = Instance, branchperlevel = [1] * Instance.NrTimeBucket + [0] , seed = myseed, mipsolver = None, averagescenariotree = False, slowmoving = True )
        mipsolver = MIPSolver(Instance, Model, tree, UseNonAnticipativity,
                              implicitnonanticipativity=True,
                              evaluatesolution=EvaluateSolution,
                              givensolution=GivenQuantities,
                              fixsolutionuntil=FixUntilTime )

        scenarios = tree.GetAllScenarios( True )

        data[myseed - offset] = scenarios[0].Demands[0][7]
        for p in Instance.ProductSet:
            Average[p] = Average[p] + scenarios[0].Demands[0][p]

    for p in Instance.ProductSet:
        Average[p] = Average[p] / nrscenario

    print Average

    # fixed bin size
    bins = np.arange(0, 1000, 1)  # fixed bin size

    plt.xlim([min(data) - 5, max(data) + 5])

    plt.hist(data, bins=bins, alpha=0.5, normed=1)
    plt.title('Shifted poisson distribution')
    axes = plt.gca()
    axes.set_ylim( [0, 0.02 ] )
    plt.xlabel('Demand')
    plt.ylabel('Frequency')
    plt.show()


def parseArguments():
    # Create argument parser
    parser = argparse.ArgumentParser()
    # Positional mandatory arguments
    parser.add_argument("Action", help="Evaluate, Solve, VSS, EVPI", type=str)
    parser.add_argument("Instance", help="Cname of the instance.", type=str)
    parser.add_argument("Distribution", help="Considered didemand disdistribution.", type=str)
    parser.add_argument("Model", help="Average/YQFix/YFiz .", type=str)
    parser.add_argument("NrScenario", help="the number of scenario used for optimization", type=int)
    parser.add_argument("ScenarioGeneration", help="MC,/RQMC.", type=str)
    parser.add_argument("-s", "--ScenarioSeed", help="The seed used for scenario generation", type=int, default= -1 )

    # Optional arguments
    parser.add_argument("-p", "--policy", help="NearestNeighbor", type=str, default="")
    parser.add_argument("-n", "--nrevaluation", help="nr scenario used for evaluation.", type=int, default=500)
    parser.add_argument("-m", "--method", help="method used to solve", type=str, default="MIP")
    parser.add_argument("-f", "--fixuntil", help="Use with VSS action, howmany periods are fixed", type=int, default=0)
    parser.add_argument("-e", "--evpi", help="if true the evpi model is consdiered",  default=False, action='store_true')
    # Print version
    parser.add_argument("--version", action="version", version='%(prog)s - Version 1.0')

    # Parse arguments
    args = parser.parse_args()

    global Action
    global InstanceName
    global Distribution
    global Model
    global PolicyGeneration
    global NrScenario
    global ScenarioGeneration
    global ScenarioSeed
    global TestIdentifier
    global EvaluatorIdentifier
    global PolicyGeneration
    global NrEvaluation
    global SeedIndex
    global NearestNeighborStrategy
    global Method
    global FixUntilTime
    global EVPI

    Action = args.Action
    InstanceName = args.Instance
    Distribution = args.Distribution
    Model = args.Model
    Method = args.method
    NrScenario = args.NrScenario
    ScenarioGeneration = args.ScenarioGeneration
    ScenarioSeed = SeedArray[ args.ScenarioSeed ]
    SeedIndex = args.ScenarioSeed
    PolicyGeneration = args.policy
    FixUntilTime = args.fixuntil
    EVPI = args.evpi
    NearestNeighborStrategy = ""
    if PolicyGeneration in ["NNDAC", "NNSAC", "NND", "NNS" ]:
        PolicyGeneration = "NN"
        NearestNeighborStrategy = args.policy
    else:
        NearestNeighborStrategy = PolicyGeneration #to have something in the table of results
    NrEvaluation = args.nrevaluation
    TestIdentifier = [ InstanceName, Distribution, Model, Method, ScenarioGeneration, NrScenario, ScenarioSeed, EVPI ]
    EvaluatorIdentifier = [ PolicyGeneration, NearestNeighborStrategy, NrEvaluation]



    return args

#Save the scenario tree in a file
#def ReadCompleteInstanceFromFile( name, nrbranch ):
#        result = None
#        filepath = '/tmp/thesim/%s_%r.pkl'%( name, nrbranch )

#        try:
#            with open(filepath, 'rb') as input:
#                result = pickle.load(input)
#            return result
#        except:
#            print "file %r not found" % (filepath)

#This function runs the evaluation for the just completed test :
def RunEvaluation(  ):
    if Constants.LauchEvalAfterSolve:
        policyset = [ "NNSAC", "NNDAC", "Re-solve"]
        if Model == Constants.ModelYQFix or Model == Constants.Average:
                policyset = ["Fix", "Re-solve"]
        for policy in policyset:
                jobname = "job_evaluate_%s_%s_%s_%s_%s_%s_%s_%s" % (
                    TestIdentifier[0],  TestIdentifier[1],  TestIdentifier[2],  TestIdentifier[5], TestIdentifier[4], TestIdentifier[3],  policy, SeedIndex)
                subprocess.call( ["qsub", jobname]  )
#This function runs the evaluation jobs when the method is solved for the 5 seed:
def RunEvaluationIfAllSolve(  ):
    #Check among the available files, if one of the sceed is not solve
    solutions = GetPreviouslyFoundSolution()
    if len( solutions ) >= 5 :
        policyset = ["NNDAC", "NNSAC", "NND", "NNS", "Re-solve"]
        if Model == Constants.ModelYQFix or Model == Constants.Average:
            policyset = ["Fix"]
        for policy in policyset:
            jobname = "job_evaluate_%s_%s_%s_%s_%s_%s_%s_s" % (
                TestIdentifier[0], TestIdentifier[1], TestIdentifier[2], TestIdentifier[5], TestIdentifier[4],
                TestIdentifier[3], policy, SeedIndex)
            subprocess.call( ["qsub", jobname]  )

def RunTestsAndEvaluation():
    global ScenarioSeed
    global SeedIndex
    for s in range( 5 ):
        SeedIndex = s
        ScenarioSeed = SeedArray[ s ]
        TestIdentifier[6] = ScenarioSeed
        if Model == Constants.ModelYQFix:
            SolveYQFix()
        if Model == Constants.ModelYFix:
            SolveYFix()
        EvaluateSingleSol()

# Compute the value of VSS as  defined in the paper: "The value of the stochastic solution in multistage problems" Laureano F. Escudero  Araceli Garin  Maria Merino  Gloria Perez
def ComputeVSS( ):

    global GivenQuantities
    global GivenSetup
    global EvaluateSolution
    global FixUntilTime

    print "Compute VSS"
    # Get the YQFix solution
    #TestIdentifier[2] = Constants.ModelYQFix
    filedescription = GetTestDescription()
    yqfixsolution = MRPSolution()
    yqfixsolution.ReadFromFile(filedescription)
    oldtest2 = TestIdentifier[2]
    oldtest3 = TestIdentifier[3]
    oldtest4 = TestIdentifier[4]
    oldtest5 = TestIdentifier[5]

    # Get the average value solution
    TestIdentifier[2] = Constants.Average
    TestIdentifier[3] = Constants.MIP
    TestIdentifier[4] = Constants.MonteCarlo
    TestIdentifier[5] = 1
    filedescription = GetTestDescription()
    averagesolution = MRPSolution()
    averagesolution.ReadFromFile(filedescription)


    TestIdentifier[2] = oldtest2
    TestIdentifier[3] = oldtest3
    TestIdentifier[4] = oldtest4
    TestIdentifier[5] = oldtest5
    EvaluateSolution = True
    # Run the MIP with the additional constraint to fix the average solution up to the first fixuntiltime stages
    treestructure = GetTreeStructure()

    # Get the setup quantitities associated with the solultion

    GivenSetup = [[averagesolution.Production[0][t][p]  for p in averagesolution.MRPInstance.ProductSet] for t in averagesolution.MRPInstance.TimeBucketSet]

    GivenQuantities = [[averagesolution.ProductionQuantity[0][t][p] for p in averagesolution.MRPInstance.ProductSet]
                        for t in averagesolution.MRPInstance.TimeBucketSet ]


    if FixUntilTime == 0:
        GivenSetup = []
        GivenQuantities = []
        EvaluateSolution = False

    if TestIdentifier[2] == Constants.ModelYQFix and  FixUntilTime > 0:
        FixUntilTime = Instance.NrTimeBucket

    solution, mipsolver = MRP(treestructure, False, recordsolveinfo=True)

    # Something need to be printed....
    Parameter =  [ UseNonAnticipativity, Model, ComputeAverageSolution, ScenarioSeed]
    data = TestIdentifier + SolveInformation +  Parameter + [ FixUntilTime , solution.TotalCost - yqfixsolution.TotalCost ]
    d = datetime.now()
    date = d.strftime('%m_%d_%Y_%H_%M_%S')
    myfile = open(r'./Test/VSS/TestResult_%s_%s.csv' % (GetTestDescription(), FixUntilTime  ), 'wb')
    wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
    wr.writerow( data )
    myfile.close()
   # PrintTestResult()
   # PrintFinalResult()

if __name__ == "__main__":
    instancename = ""
    try: 
        args = parseArguments()
        #ScenarioNr = scenarionr
        #Instance.ScenarioNr = scenarionr
        UseNonAnticipativity = True

        #if Model == "YFix" or Model == "YQFix":  UseInmplicitAnticipativity = True
        Instance.Average = False
        #Instance.BranchingStrategy = nrbranch

        Instance.LoadScenarioFromFile = False
        PrintScenarios = False

        #Instance.DefineAsSuperSmallIntance()
        #


        Instance.ReadInstanceFromExelFile( InstanceName,  Distribution )
        #for InstanceName in ["01", "02", "03", "04", "05"]:  # "06", "07", "08", "09",
            #			  "10", "11", "12", "13", "14", "15", "16", "17", "18", "19",
            #			  "20", "21", "22", "23", "24", "25", "26", "27", "28", "29",
            #			  "30", "31", "32", "33", "34", "35", "36", "37", "38"]:
        #    Distribution = "NonStationary"
        #    for Distribution in ["SlowMoving", "Normal", "Lumpy", "Uniform",
        #         "NonStationary"]:
        #    Instance.ReadFromFile( InstanceName, Distribution )
        #    Instance.SaveCompleteInstanceInExelFile()
        #Instance.ReadFromFile(InstanceName, Distribution)
        #Instance.SaveCompleteInstanceInExelFile()
        #Instance.DefineAsSuperSmallIntance()
        #Instance.SaveCompleteInstanceInExelFile()
    except KeyError:
        print "This instance does not exist. Instance should be in 01, 02, 03, ... , 38"
      
    #MRP() #[1, 2, 1, 1, 1, 1, 0 ])
   # ComputeVSS()
   # ComputeAverageGeneraor()
    if Action == Constants.Solve:

        if Model == Constants.ModelYQFix or Model == Constants.Average:
            #if Constants.LauchEvalAfterSolve :
                SolveYQFix()
            #else: RunTestsAndEvaluation()

        if Model == Constants.ModelYFix:
            #if Constants.LauchEvalAfterSolve:
                SolveYFix(  )

            #else:
            #    RunTestsAndEvaluation()

    if Action == Constants.VSS:
        ComputeVSS( )


    if Action == Constants.Evaluate:
        if ScenarioSeed == -1:
            Evaluate()
        else:
            EvaluateSingleSol()



#    CompactSolveInformation = [CompactSolveInformation[i] /  int( nrsolve ) for i in range( 3) ]
#    PrintFinalResult()

  #  PrintResult()
  # end = raw_input( "press enter" )
