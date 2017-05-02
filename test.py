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
#pass Debug to true to get some debug information printed
Debug = False
Instance = MRPInstance()
AverageInstance = MRPInstance()

#If UseNonAnticipativity is set to true a variable per scenario is generated, otherwise only the required variable a created.
UseNonAnticipativity = False
#ActuallyUseAnticipativity is set to False to compute the EPVI, otherwise, it is set to true to add the non anticipativity constraints
ActuallyUseAnticipativity = False
#PrintScenarios is set to true if the scenario tree is printed in a file, this is usefull if the same scenario must be reloaded in a ater test.
PrintScenarios = False
ScenarioNr = -1
#The attribut model refers to the model which is solved. It can take values in "Average, YQFix, YFix,_Fix"
# which indicates that the avergae model is solve, the Variable Y and Q are fixed at the begining of the planning horizon, only Y is fix, or everything can change at each period
Model = "Average"

#The variable UseSlowMoving is set to True if the scenario are genrated with a slow moving distribution
UseSlowMoving = False

ComputeAverageSolution = False

#When a solution is obtained, it is recorded in Solution. This is used to compute VSS for instance.
Solution = None
#Evaluate solution is true, the solution in the variable "GivenQuantities" is given to CPLEX to compute the associated costs
EvaluateSolution = False
FixUntilTime = 0
GivenQuantities =[]
VSS = []
ScenarioSeed = 1

#This list contain the information obtained after solving the problem
SolveInformation = []

EvaluateInfo = []

def PrintResult():
    Parameter =  [ UseNonAnticipativity, ActuallyUseAnticipativity, Model, UseSlowMoving, ComputeAverageSolution, ScenarioSeed ]
    data = SolveInformation + EvaluateInfo + Parameter
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

    scenariotree = ScenarioTree( Instance, treestructur, ScenarioSeed, averagescenariotree=averagescenario, slowmoving= UseSlowMoving )

    mipsolver = MIPSolver(Instance, Model, scenariotree, UseNonAnticipativity,
                          implicitnonanticipativity=ActuallyUseAnticipativity,
                          evaluatesolution = EvaluateSolution,
                          givensolution = GivenQuantities,
                          fixsolutionuntil = FixUntilTime,
                          debug=Debug)



    if Debug:
        Instance.PrintInstance()
    if PrintScenarios:
        mipsolver.PrintScenarioToFile(  )

    if Debug:
        print "Start to model in Cplex"
    mipsolver.BuildModel()
    if Debug:
        print "Start to solve instance %s with Cplex"% Instance.InstanceName;

    solution = mipsolver.Solve()
   # result = solution.TotalCost, [ [ sum( solution.Production.get_value( Instance.ProductName[ p], t, w ) *  for w in Instance.ScenarioSet ) for p in Instance.ProductSet ] for t in Instance.TimeBucketSet ]

    if Debug:
            solution.Print()
            description = "%r_%r" % ( Model, Instance.BranchingStrategy )
            solution.PrintToExcel( description )

    if recordsolveinfo:
        SolveInformation = mipsolver.SolveInfo

    return solution



def SolveAndEvaluateYQFix( average = False, nrevaluation = 2):

    if Debug:
        Instance.PrintInstance()

    treestructure = [1, 8, 4, 2, 2, 2, 0]
    if Instance.NrTimeBucket == 6 :
         treestructure = [1, 16, 8, 8, 4, 2, 0 ]
    if Instance.NrTimeBucket == 7 :
         treestructure = [1, 16, 8, 4, 2, 2, 2, 0 ]
    if Instance.NrTimeBucket == 8 :
         treestructure = [1, 8, 8, 4, 2, 2, 2, 2, 0 ]
    if Instance.NrTimeBucket == 9 :
         treestructure = [1, 8, 4, 4, 2, 2, 2, 2, 2, 0 ]
    if Instance.NrTimeBucket == 10 :
         treestructure = [1, 4, 2, 2, 2, 2, 2, 2, 2, 2, 0 ]
    method = "TwoStageYQFix"
    if average:
        treestructure = [1] * Instance.NrTimeBucket + [0]
        method = "Average"


    solution = MRP( treestructure, average, recordsolveinfo=True )
    givenquantty = [ [  solution.ProductionQuantity.ix[ p, t ].get_value(0) for p in Instance.ProductSet ]
                           for t in Instance.TimeBucketSet ]

    EvaluateYQFixSolution( givenquantty, nrevaluation, method )

def EvaluateYQFixSolution( givenquantty, nrscenario, solutionname):
    # Compute the average value of the demand
    global Instance
    global FixUntilTime
    global EvaluateSolution
    global GivenQuantities
    global ScenarioSeed
    global EvaluateInfo
    SavedInstance = Instance

    GivenQuantities = givenquantty

    Instance = SavedInstance
    EvaluateSolution = True

    Evaluated = [ [ -1 for t in [1] ] for e in range( nrscenario ) ]
    #Use an offset in the seed to make sure the scenario used for evaluation are different from the scenario used for optimization
    offset = 100
    for seed in range(offset, nrscenario + offset, 1):
        #Generate a random scenario
        ScenarioSeed =  seed
        #Evaluate the solution on the scenario
        for t in [Instance.NrTimeBucket -1]: #Instance.TimeBucketSet:
            FixUntilTime = t

            solutionofYQ =  MRP( [1] * Instance.NrTimeBucket + [0] )
            Evaluated[ seed - offset ][0] = solutionofYQ.TotalCost

            Instance = SavedInstance
            #print "Evaluation of YQ: %r" % Evaluated
    Sum = sum( Evaluated[s][0] for s in range( nrscenario ) )
    Average = Sum / nrscenario
    sumdeviation =  sum( math.pow( ( Evaluated[s][0] - Average ), 2  )  for s in range( nrscenario ) )
    std_dev = math.sqrt( ( sumdeviation / nrscenario) )
    EvaluateInfo = [ nrscenario, Average, std_dev ]
    evvaluationdataframe = pd.DataFrame( Evaluated ) #, index=range(offset, nrscenario + offset), )
    d = datetime.now()
    date = d.strftime('%m_%d_%Y_%H_%M_%S')
    #myfile = open(
    #    r'./Test/TestResultOfEvaluated_%s_%r_%s_%s.csv' % (Instance.InstanceName, solutionname, Model, date),
    #    'wb')
    #wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)

    writer = pd.ExcelWriter( './Test/TestResultOfEvaluated_%s_%r_%s_%s.xlsx'% (Instance.InstanceName, solutionname, Model, date) )
    evvaluationdataframe.to_excel( writer, "Evaluation" )

    writer.save()
    #wr.writerow()
    #wr.save()

def ComputeAverageGeneraor():
    offset=1000
    nrscenario = 10000
    Average = [ 0  ] * Instance.NrProduct
    data = [0] * nrscenario
    for myseed in range(offset, nrscenario + offset, 1):
        #Generate a random scenario
        tree = ScenarioTree(  instance = Instance, branchperlevel = [1] * Instance.NrTimeBucket + [0] , seed = myseed, mipsolver = None, averagescenariotree = False, slowmoving = True )
        mipsolver = MIPSolver(Instance, Model, tree, UseNonAnticipativity,
                              implicitnonanticipativity=ActuallyUseAnticipativity,
                              evaluatesolution=EvaluateSolution,
                              givensolution=GivenQuantities,
                              fixsolutionuntil=FixUntilTime,
                              debug=Debug)
        scenarios = tree.GetAllScenarios()

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
def ReadCompleteInstanceFromFile( name, nrbranch ):
        result = None
        filepath = '/tmp/thesim/%s_%r.pkl'%( name, nrbranch )

        try:
            with open(filepath, 'rb') as input:
                result = pickle.load(input)
            return result
        except:
            print "file %r not found" % (filepath)



if __name__ == "__main__":
    instancename = ""
    try: 
        if len(sys.argv) == 1:
            instancename = raw_input("Enter the number (in [01;38]) of the instance to solve:")
        else:
            script, instancename, scenarioseed, Model, nrevaluation, avg, distribution  = sys.argv

        UseSlowMoving = distribution == "SlowMoving"
        ScenarioSeed = int( scenarioseed )
        #ScenarioNr = scenarionr
        #Instance.ScenarioNr = scenarionr
        UseNonAnticipativity = True
        ActuallyUseAnticipativity = True
        Instance.Average = False
        #Instance.BranchingStrategy = nrbranch

        Instance.LoadScenarioFromFile = False
        PrintScenarios = False
        Instance.ReadInstanceFromExelFile( instancename )

        #Instance.ReadFromFile( instancename )
        #Instance.SaveCompleteInstanceInExelFile()

        #Instance.DefineAsSuperSmallIntance()
        #Instance.SaveCompleteInstanceInExelFile()
    except KeyError:
        print "This instance does not exist. Instance should be in 01, 02, 03, ... , 38"
      
    #MRP() #[1, 2, 1, 1, 1, 1, 0 ])
   # ComputeVSS()
    average = avg =='True'
   # ComputeAverageGeneraor()
   # end = raw_input( "press enter" )
    SolveAndEvaluateYQFix(  average = average, nrevaluation = int( nrevaluation ) )
    PrintResult()