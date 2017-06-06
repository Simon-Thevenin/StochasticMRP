#from __future__ import absolute_import, division, print_function
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
#pass Debug to true to get some debug information printed

Instance = MRPInstance()
AverageInstance = MRPInstance()

#If UseNonAnticipativity is set to true a variable per scenario is generated, otherwise only the required variable a created.
UseNonAnticipativity = False
#ActuallyUseAnticipativity is set to False to compute the EPVI, otherwise, it is set to true to add the non anticipativity constraints
#UseInmplicitAnticipativity = False
#PrintScenarios is set to true if the scenario tree is printed in a file, this is usefull if the same scenario must be reloaded in a ater test.
PrintScenarios = False
ScenarioNr = -1
#The attribut model refers to the model which is solved. It can take values in "Average, YQFix, YFix,_Fix"
# which indicates that the avergae model is solve, the Variable Y and Q are fixed at the begining of the planning horizon, only Y is fix, or everything can change at each period
Model = "YFix"
Methode =  "Average"

ComputeAverageSolution = False
GenerateAsYFix = False

#How to generate a policy from the solution of a scenario tree
PolicyGeneration = "NearestNeighbor"

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

TestIdentifier = []
SeedArray = [ 2934, 875, 3545, 765, 546, 768, 242, 375, 142, 236, 788 ]

#This list contain the information obtained after solving the problem
SolveInformation = []
OutOfSampleTestResult = []
CompactSolveInformation = [ 0, 0, 0]
InSampleKPIStat= [ 0, 0, 0, 0, 0, 0, 0, 0 ]
EvaluateInfo = []

def PrintResult():
    Parameter =  [ UseNonAnticipativity, Model, ComputeAverageSolution, ScenarioSeed ]
    data = SolveInformation +  Parameter
    d = datetime.now()
    date = d.strftime('%m_%d_%Y_%H_%M_%S')
    myfile = open(r'./Test/SolveInfo/TestResult_%s_%r_%s_%s.csv' % (
        Instance.InstanceName,  Model, ScenarioSeed , date), 'wb')
    wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
    wr.writerow( data )
    myfile.close()


def PrintFinalResult():
    data = TestIdentifier + CompactSolveInformation + InSampleKPIStat + OutOfSampleTestResult
    d = datetime.now()
    date = d.strftime('%m_%d_%Y_%H_%M_%S')
    myfile = open(r'./Test/TestResult_%s_%r_%s_%s.csv' % (
        Instance.InstanceName,  Model, ScenarioSeed , date), 'wb')
    wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
    wr.writerow( data )
    myfile.close()

#This function creates the CPLEX model and solves it.
def MRP( treestructur = [ 1, 8, 8, 4, 2, 1, 0 ], averagescenario = False, recordsolveinfo = False ):

    global SolveInformation
    global CompactSolveInformation
    global InSampleKPIStat

    scenariotree = ScenarioTree( Instance, treestructur, ScenarioSeed,
                                 averagescenariotree=averagescenario,
                                 generateasYQfix= GenerateAsYFix,
                                 scenariogenerationmethod = ScenarioGeneration,
                                 generateRQMCForYQfix = ( Model  == Constants.ModelYQFix and ScenarioGeneration == Constants.RQMC ) )

    mipsolver = MIPSolver(Instance, Model, scenariotree, UseNonAnticipativity,
                          implicitnonanticipativity=True,
                          evaluatesolution = EvaluateSolution,
                          givenquantities = GivenQuantities,
                          givensetups = GivenSetup,
                          fixsolutionuntil = FixUntilTime )

    if Constants.Debug:
        Instance.PrintInstance()
    if PrintScenarios:
        mipsolver.PrintScenarioToFile(  )

    if Constants.Debug:
        print "Start to model in Cplex"
    mipsolver.BuildModel()
    if Constants.Debug:
        print "Start to solve instance %s with Cplex"% Instance.InstanceName;

    solution = mipsolver.Solve()
   # result = solution.TotalCost, [ [ sum( solution.Production.get_value( Instance.ProductName[ p], t, w ) *  for w in Instance.ScenarioSet ) for p in Instance.ProductSet ] for t in Instance.TimeBucketSet ]

    if Constants.Debug:
       #    solution.Print()
           description = "%r_%r" % ( Model, ScenarioSeed )
      #     solution.PrintToExcel( description )

    if recordsolveinfo:
        SolveInformation = mipsolver.SolveInfo

    CompactSolveInformation = [ CompactSolveInformation[0] + mipsolver.SolveInfo[3],
                                CompactSolveInformation[1] + mipsolver.SolveInfo[6],
                                CompactSolveInformation[2] +mipsolver.SolveInfo[7] ]
    return solution, mipsolver

def SolveAndEvaluateYQFix( average = False, nrevaluation = 2, nrscenario = 100, nrsolve = 1):
    global ScenarioSeed
    global Model
    global Methode
    global OutOfSampleTestResult
    global InSampleKPIStat

    if Constants.Debug:
        Instance.PrintInstance()

    treestructure = [1, nrscenario] +  [1] * ( Instance.NrTimeBucket - 1 ) +[ 0 ]
    method = "TwoStageYQFix"
    if average:
        treestructure = [1] + [1] * Instance.NrTimeBucket + [0]
        method = "Average"
        Methode = "Average"

    solutions = []

    for k in range( nrsolve ):
        ScenarioSeed = SeedArray[ k ]
        solution, mipsolver = MRP( treestructure, average, recordsolveinfo=True )
        PrintResult()
        solutions.append( solution )
        solution.ComputeStatistics()
        insamplekpisstate = solution.PrintStatistics( TestIdentifier, "InSample" , -1, 0, ScenarioSeed)

        for i in range(3 + Instance.NrLevel):
            InSampleKPIStat[i] = InSampleKPIStat[i] + insamplekpisstate[i]

    for i in range(3 + Instance.NrLevel):
        InSampleKPIStat[i] = InSampleKPIStat[i] / nrsolve

    evaluator = Evaluator( Instance, solutions  )
    OutOfSampleTestResult = evaluator.EvaluateYQFixSolution( TestIdentifier, nrevaluation,  method, Constants.ModelYQFix )


def SolveAndEvaluateYFix( method = "MIP", nrevaluation = 2, nrscenario = 1, nrsolve = 1):
    global GivenSetup
    global GivenQuantities
    global ScenarioSeed
    global Model
    global Methode
    global InSampleKPIStat
    global OutOfSampleTestResult

    if Constants.Debug:
        Instance.PrintInstance()

    treestructure = [1, 2, 2, 2, 1, 1, 1, 1, 1, 1, 0]

    if nrscenario == 8:
        if Instance.NrTimeBucket == 6 :
              treestructure = [1, 2, 2, 2, 1, 1, 1, 0]
             # treestructure = [1, 8, 4, 2, 1, 1, 1, 0 ]
        if Instance.NrTimeBucket == 8:
            treestructure = [1, 2, 2, 2, 2, 1, 1, 1, 1,  0]
        if Instance.NrTimeBucket == 9 :
              treestructure = [1, 2, 2, 2, 2, 1, 1, 1, 1, 1, 0 ]
        if Instance.NrTimeBucket == 10:
            treestructure = [1, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 0]
        if Instance.NrTimeBucket == 12 :
             treestructure = [1, 8, 4, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0 ]
        if Instance.NrTimeBucket == 15 :
             treestructure = [1, 4, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0 ]

    if nrscenario == 64:
        if Instance.NrTimeBucket == 6 :
              treestructure = [1, 4, 4, 4, 1, 1, 1, 0]
             # treestructure = [1, 8, 4, 2, 1, 1, 1, 0 ]
        if Instance.NrTimeBucket == 8:
            treestructure = [1, 4, 4, 4, 4, 1, 1, 1, 1,  0]
        if Instance.NrTimeBucket == 9 :
              treestructure = [1, 4, 4, 4, 4, 1, 1, 1, 1, 1, 0 ]
        if Instance.NrTimeBucket == 10:
            treestructure = [1, 4, 4, 4, 4, 4, 1, 1, 1, 1, 1, 0]
        if Instance.NrTimeBucket == 12 :
             treestructure = [1, 8, 4, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0 ]
        if Instance.NrTimeBucket == 15 :
             treestructure = [1, 4, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0 ]

    if nrscenario == 512:
        if Instance.NrTimeBucket == 6 :
             #treestructure = [1, 2, 2, 2, 1, 1, 1, 0]
             treestructure = [1, 8, 8, 8, 1, 1, 1, 0 ]
        if Instance.NrTimeBucket == 8:
            treestructure = [1, 8, 8, 8, 8, 1, 1, 1, 1,  0]
        if Instance.NrTimeBucket == 9 :
              treestructure = [1,8, 8, 8, 2, 1, 1, 1, 1, 1, 0 ]
        if Instance.NrTimeBucket == 10:
            treestructure = [1, 8, 8, 8, 8, 8, 1, 1, 1, 1, 1, 0]
        if Instance.NrTimeBucket == 12 :
             treestructure = [1, 8, 4, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0 ]
        if Instance.NrTimeBucket == 15 :
             treestructure = [1, 4, 2, 2, 2, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 0 ]

    if nrscenario == 1024:
        if Instance.NrTimeBucket == 6 :
             #treestructure = [1, 2, 2, 2, 1, 1, 1, 0]
             treestructure = [1, 32, 8, 4, 1, 1, 1, 0 ]
        if Instance.NrTimeBucket == 9 :
              treestructure = [1, 8, 4, 4, 2, 2, 2, 1, 1, 1, 0 ]
        if Instance.NrTimeBucket == 12 :
             treestructure = [1, 4, 4, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 0 ]
        if Instance.NrTimeBucket == 15 :
             treestructure = [1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 0 ]

    if nrscenario == 8192:
        if Instance.NrTimeBucket == 6 :
            treestructure = [1, 25, 25, 25, 1, 1, 1, 0 ]
        if Instance.NrTimeBucket == 9:
            treestructure = [1, 8, 4, 4, 4, 4, 4, 1, 1, 1, 0]
        if Instance.NrTimeBucket == 12 :
             treestructure = [1, 8, 4, 4, 4, 2, 2, 2, 2, 1, 1, 1, 1, 0 ]
        if Instance.NrTimeBucket == 15 :
             treestructure = [1, 4, 4, 4, 2, 2, 2, 2, 2, 2, 2, 1, 1, 1, 1, 1, 0 ]



    if average:
        treestructure = [1] + [1] * Instance.NrTimeBucket + [0]

    solutions = []
    for k in range(nrsolve):
        ScenarioSeed = SeedArray[k]
        if method == "MIP" or method == "Avergae":
            solution, mipsolver = MRP( treestructure, average, recordsolveinfo=True )
            solutions.append(solution)
            PrintResult()
            solution.ComputeStatistics()
            insamplekpisstate = solution.PrintStatistics(TestIdentifier, "InSample", -1, 0, ScenarioSeed)

            for i in range(3 + Instance.NrLevel):
                InSampleKPIStat[i] = InSampleKPIStat[i] + insamplekpisstate[i]
        if method == "SDDP":
            sddpsolver = SDDP( Instance )
            sddpsolver.Run()


    for i in range(3 + Instance.NrLevel):
        InSampleKPIStat[i] = InSampleKPIStat[i] / nrsolve

    evaluator = Evaluator( Instance, solutions, PolicyGeneration, ScenarioGeneration )
    OutOfSampleTestResult = evaluator.EvaluateYQFixSolution( TestIdentifier,nrevaluation, Methode, Constants.ModelYFix )

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

if __name__ == "__main__":
    instancename = ""
    try: 
        if len(sys.argv) == 1:
            instancename = raw_input("Enter the number (in [01;38]) of the instance to solve:")
        else:
            script, instancename, nrsolve, Model, method, generateasYQFix, policy, distribution, nrscenario, generationmethod,  nrevaluation  = sys.argv

        ScenarioGeneration = generationmethod
        TestIdentifier = [ instancename, Model, generateasYQFix, policy, distribution, nrscenario, generationmethod ]
        GenerateAsYFix = ( generateasYQFix == 'True' )
        PolicyGeneration = policy
        #ScenarioNr = scenarionr
        #Instance.ScenarioNr = scenarionr
        UseNonAnticipativity = True

        #if Model == "YFix" or Model == "YQFix":  UseInmplicitAnticipativity = True
        Instance.Average = False
        #Instance.BranchingStrategy = nrbranch

        Instance.LoadScenarioFromFile = False
        PrintScenarios = False

        Instance.DefineAsSuperSmallIntance()
        #Instance.ReadInstanceFromExelFile( instancename + "_" + distribution )

        #Instance.ReadFromFile( instancename, distribution )
        #Instance.SaveCompleteInstanceInExelFile()

        #Instance.DefineAsSuperSmallIntance()
    except KeyError:
        print "This instance does not exist. Instance should be in 01, 02, 03, ... , 38"
      
    #MRP() #[1, 2, 1, 1, 1, 1, 0 ])
   # ComputeVSS()
    average = ( method =='Average' )
   # ComputeAverageGeneraor()

    if Model == Constants.ModelYQFix:
         SolveAndEvaluateYQFix(  average = average, nrevaluation = int(nrevaluation), nrscenario = int(nrscenario), nrsolve = int( nrsolve ) )
    if Model == Constants.ModelYFix:
         SolveAndEvaluateYFix( method = method, nrevaluation = int(nrevaluation), nrscenario= int(nrscenario), nrsolve = int( nrsolve ) )

    CompactSolveInformation = [CompactSolveInformation[i] /  int( nrsolve ) for i in range( 3) ]
    PrintFinalResult()

  #  PrintResult()
  # end = raw_input( "press enter" )