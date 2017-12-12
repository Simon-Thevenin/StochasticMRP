#from __future__ import absolute_import, division, print_function
#from __future__ import division
#print "Attention matplt is avctivee"
#from matplotlib import pyplot as PLT


import cplex

from MRPInstance import MRPInstance


from MRPSolution import MRPSolution


from Solver import Solver
import csv
from datetime import datetime
#from matplotlib import pyplot as plt

import cPickle as pickle
from Constants import Constants
from Evaluator import Evaluator
import argparse



import subprocess

#pass Debug to true to get some debug information printed
#
#
# clusters = ScenarioTreeNode.GeneratePoints( "MC", 50, 2, "Normal", [10,10], std = [5,5] )
# from pylab import *
#
# for k in range(len(clusters[0][0])):
#     x = clusters[0][0][k]
#     y = clusters[0][1][k]
#     xlim(0, 20)
#     ylim(0, 20)
#     plot(x, y, '+', color=(0,0,0) )
# show() # or savefig(<filename>)

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
NrScenario = -1

#The attribut model refers to the model which is solved. It can take values in "Average, YQFix, YFix,_Fix"
# which indicates that the avergae model is solve, the Variable Y and Q are fixed at the begining of the planning horizon, only Y is fix, or everything can change at each period
Model = "YFix"
Method = "MIP"
ComputeAverageSolution = False
Rule = "L4L"


#How to generate a policy from the solution of a scenario tree
PolicyGeneration = "NearestNeighbor"
NearestNeighborStrategy = ""
NrEvaluation = 500
TimeHorizon = 1
ScenarioGeneration = "MC"
#When a solution is obtained, it is recorded in Solution. This is used to compute VSS for instance.
Solution = None
#Evaluate solution is true, the solution in the variable "GivenQuantities" is given to CPLEX to compute the associated costs
EvaluateSolution = False
AllScenario = 0

VSS = []
ScenarioSeed = 1
SeedIndex = -1
TestIdentifier = []
EvaluatorIdentifier = []

MIPSetting = ""

UseNonAnticipativity = True
SeedArray = [ 2934, 875, 3545, 765, 546, 768, 242, 375, 142, 236, 788 ]

#This list contain the information obtained after solving the problem
SolveInformation = []
OutOfSampleTestResult = []
InSampleKPIStat= []# 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0  ]
EvaluateInfo = []

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
    data = TestIdentifier + EvaluatorIdentifier + InSampleKPIStat + OutOfSampleTestResult
    d = datetime.now()
    date = d.strftime('%m_%d_%Y_%H_%M_%S')
    if Constants.Debug:
        print "print the test result ./Test/TestResult_%s_%s.csv" % (GetTestDescription(), GetEvaluateDescription())
    myfile = open(r'./Test/TestResult_%s_%s.csv' % (GetTestDescription(), GetEvaluateDescription()), 'wb')
    wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
    wr.writerow( data )
    myfile.close()



def GetTestDescription():
    result = JoinList( TestIdentifier)
    return result

def JoinList(list):
    result = "_".join( str(elm) for elm in list)
    return result

def GetEvaluateDescription():
    result = JoinList(EvaluatorIdentifier)
    return result




def PrintSolutionToFile( solution  ):
    testdescription = GetTestDescription()
    if Constants.PrintSolutionFileToExcel:
        solution.PrintToExcel(testdescription)
    else:
        solution.PrintToPickle(testdescription)





def Solve():

    solver = Solver (Instance, TestIdentifier, mipsetting=MIPSetting, testdescription= GetTestDescription(), evaluatesol = EvaluateSolution, treestructure=GetTreeStructure())

    solution = solver.Solve()

    PrintTestResult()
    PrintSolutionToFile(solution)
    RunEvaluation()
    GatherEvaluation()

def GetPreviouslyFoundSolution():
    result = []
    for s in SeedArray:
        try:
            TestIdentifier[5] = s
            filedescription = GetTestDescription()
            solution = MRPSolution()
            solution.ReadFromFile( filedescription )
            result.append( solution )

        except IOError:
            if Constants.Debug:
                print "No solution found for seed %d"%s

    return result

def ComputeInSampleStatistis():
    global InSampleKPIStat
    solutions = GetPreviouslyFoundSolution()
    lengthinsamplekpi = -1

    for solution in solutions:
        if not Constants.PrintOnlyFirstStageDecision:
            solution.ComputeStatistics()
        insamplekpisstate = solution.PrintStatistics(TestIdentifier, "InSample", -1, 0, ScenarioSeed, -1, True )
        lengthinsamplekpi = len(insamplekpisstate)
        InSampleKPIStat = [0] * lengthinsamplekpi
        for i in range(lengthinsamplekpi):
                InSampleKPIStat[i] = InSampleKPIStat[i] + insamplekpisstate[i]

    for i in range(lengthinsamplekpi):
        InSampleKPIStat[i] = InSampleKPIStat[i] / len( solutions )

def Evaluate():
    ComputeInSampleStatistis()
    global OutOfSampleTestResult
    solutions = GetPreviouslyFoundSolution()
    evaluator = Evaluator( Instance, solutions, [], PolicyGeneration, ScenarioGeneration, treestructure=GetTreeStructure(), nearestneighborstrategy= NearestNeighborStrategy, model=Model, timehorizon= TimeHorizon )
    OutOfSampleTestResult = evaluator.EvaluateYQFixSolution( TestIdentifier, EvaluatorIdentifier )
    PrintFinalResult()

def GetEvaluationFileName():
    result = "/tmp/thesim/Evaluations/" + GetTestDescription() + GetEvaluateDescription()
    #result = "./Evaluations/" + GetTestDescription() + GetEvaluateDescription()
    return result

#Define the tree  structur do be used
def GetTreeStructure( ):
        treestructure = []
        nrtimebucketconsidered = Instance.NrTimeBucket
        if PolicyGeneration == Constants.RollingHorizon:
            nrtimebucketconsidered = Instance.MaxLeadTime + TimeHorizon
        if Model == Constants.Average or Model == Constants.AverageSS:
            treestructure = [1, 1] + [1] * (nrtimebucketconsidered - 1) + [0]

        if Model == Constants.ModelYQFix:
            treestructure = [1, int(NrScenario)] + [1] * (nrtimebucketconsidered- 1) + [0]

        if Model == Constants.ModelYFix or Model ==Constants.ModelHeuristicYFix:
            treestructure = [1, 1] + [1] * (nrtimebucketconsidered - 1) + [0]
            stochasticparttreestructure = [1, 1] + [1] * (nrtimebucketconsidered- 1) + [0]
            if PolicyGeneration == Constants.RollingHorizon:
                nrtimebucketstochastic = nrtimebucketconsidered
            else:
                nrtimebucketstochastic = Instance.NrTimeBucket - Instance.NrTimeBucketWithoutUncertaintyBefore - Instance.NrTimeBucketWithoutUncertaintyAfter

            if NrScenario == "4":
                if nrtimebucketstochastic == 1:
                    stochasticparttreestructure = [4]
                if nrtimebucketstochastic == 2:
                    stochasticparttreestructure = [4, 1]
                if nrtimebucketstochastic == 3:
                    stochasticparttreestructure = [4, 1, 1]
                if nrtimebucketstochastic == 4:
                    stochasticparttreestructure = [4, 1, 1, 1]
                if nrtimebucketstochastic == 5:
                    stochasticparttreestructure = [4, 1, 1, 1, 1]


            if NrScenario == "4096":
                if nrtimebucketstochastic == 4:
                    stochasticparttreestructure = [8, 8, 8, 8]

            if NrScenario == "2":
                if nrtimebucketstochastic == 4:
                    stochasticparttreestructure = [2, 1, 1, 1]

            if NrScenario == "4b":
                if nrtimebucketstochastic == 4:
                    stochasticparttreestructure = [2, 1, 1, 2]


            if NrScenario == "6400a":
                if nrtimebucketstochastic == 3:
                    stochasticparttreestructure = [200, 32, 1]
                if nrtimebucketstochastic == 4:
                    stochasticparttreestructure = [200, 32, 1, 1]
                if nrtimebucketstochastic == 5:
                    stochasticparttreestructure = [200, 32, 1, 1, 1]

            if NrScenario == "6400b":
                if nrtimebucketstochastic == 3:
                    stochasticparttreestructure = [50, 32, 4]
                if nrtimebucketstochastic == 4:
                    stochasticparttreestructure = [50, 8, 4, 4]
                if nrtimebucketstochastic == 5:
                    stochasticparttreestructure = [50, 8, 4, 2, 2]
                if nrtimebucketstochastic == 6:
                    stochasticparttreestructure = [50, 8, 4, 2, 2, 2]

            if NrScenario == "6400c":
                if nrtimebucketstochastic == 3:
                    stochasticparttreestructure = [20, 20, 16]
                if nrtimebucketstochastic == 4:
                    stochasticparttreestructure = [10, 10, 8, 8]
                if nrtimebucketstochastic == 5:
                    stochasticparttreestructure = [8, 8, 5, 5, 4]

            if NrScenario == "800":
                if nrtimebucketstochastic == 3:
                    stochasticparttreestructure = [25, 8, 4]
                if nrtimebucketstochastic == 4:
                    stochasticparttreestructure = [25, 4, 4, 2]
                if nrtimebucketstochastic == 5:
                    stochasticparttreestructure = [25, 4, 4, 2, 1]

            if NrScenario == "1600":
                if nrtimebucketstochastic == 3:
                    stochasticparttreestructure = [25, 16, 4]
                if nrtimebucketstochastic == 4:
                    stochasticparttreestructure = [25, 4, 4, 4]
                if nrtimebucketstochastic == 5:
                    stochasticparttreestructure = [25, 4, 4, 2, 2]

            if NrScenario == "3200":
                if nrtimebucketstochastic == 3:
                    stochasticparttreestructure = [50, 16, 4]
                if nrtimebucketstochastic == 4:
                    stochasticparttreestructure = [25, 8, 4, 4]
                if nrtimebucketstochastic == 5:
                    stochasticparttreestructure = [25, 8, 4, 2, 2]

            if NrScenario == "12800":
                if nrtimebucketstochastic == 3:
                    stochasticparttreestructure = [50, 32, 8]
                if nrtimebucketstochastic == 4:
                    stochasticparttreestructure = [50, 8, 8, 4]
                if nrtimebucketstochastic == 5:
                    stochasticparttreestructure = [50, 8, 8, 2, 2]

            if NrScenario == "25600":
                if nrtimebucketstochastic == 3:
                    stochasticparttreestructure = [50, 32, 16]
                if nrtimebucketstochastic == 4:
                    stochasticparttreestructure = [50, 16, 8, 4]
                if nrtimebucketstochastic == 5:
                    stochasticparttreestructure = [50, 8, 8, 4, 2]

            if NrScenario == "51200b":
                if nrtimebucketstochastic == 3:
                    stochasticparttreestructure = [50, 32, 32]
                if nrtimebucketstochastic == 4:
                    stochasticparttreestructure = [50, 32, 8, 4]
                if nrtimebucketstochastic == 5:
                    stochasticparttreestructure = [50, 16, 8, 4, 2]

            if NrScenario == "102400b":
                if nrtimebucketstochastic == 3:
                    stochasticparttreestructure = [100, 32, 32]
                if nrtimebucketstochastic == 4:
                    stochasticparttreestructure = [50, 32, 8, 8]
                if nrtimebucketstochastic == 5:
                    stochasticparttreestructure = [50, 16, 8, 4, 4]

            if NrScenario == "153600":
                if nrtimebucketstochastic == 3:
                    stochasticparttreestructure = [100, 48, 32]
                if nrtimebucketstochastic == 4:
                    stochasticparttreestructure = [75, 32, 8, 8]
                if nrtimebucketstochastic == 5:
                    stochasticparttreestructure = [75, 16, 8, 4, 4]

            if NrScenario == "204800":
                if nrtimebucketstochastic == 3:
                    stochasticparttreestructure = [100, 64, 32]
                if nrtimebucketstochastic == 4:
                    stochasticparttreestructure = [50, 32, 16, 8]
                if nrtimebucketstochastic == 5:
                    stochasticparttreestructure = [50, 16, 8, 8, 4]

            if NrScenario == "102400":
                if nrtimebucketstochastic == 3:
                    stochasticparttreestructure = [100, 64, 16]
                if nrtimebucketstochastic == 4:
                    stochasticparttreestructure = [100, 32, 8, 4]
                if nrtimebucketstochastic == 5:
                    stochasticparttreestructure = [50, 16, 8, 4, 4]

            if not  PolicyGeneration == Constants.RollingHorizon:
                k = 0
                for i in range(Instance.NrTimeBucketWithoutUncertaintyBefore + 1,
                               nrtimebucketconsidered  - Instance.NrTimeBucketWithoutUncertaintyAfter + 1):
                    treestructure[i] = stochasticparttreestructure[k]
                    k += 1
            else:
                treestructure = stochasticparttreestructure
        return treestructure

def EvaluateSingleSol(  ):
   # ComputeInSampleStatistis()
    global OutOfSampleTestResult
    global Model
    tmpmodel = Model
   # solutions = GetPreviouslyFoundSolution()
    filedescription = GetTestDescription()

    solution = MRPSolution()

    if not EVPI and not PolicyGeneration == Constants.RollingHorizon: #In evpi mode, a solution is computed for each scenario
        solution.ReadFromFile(filedescription)


    MIPModel = Model
    if Model == Constants.Average or Model == Constants.AverageSS:
        MIPModel = Constants.ModelYQFix
    if Model == Constants.ModelHeuristicYFix:
        MIPModel = Constants.ModelYFix
        Model = Constants.ModelYFix

    evaluator = Evaluator( Instance, [solution], [], PolicyGeneration, evpi=EVPI,
                          scenariogenerationresolve=ScenarioGeneration, treestructure=GetTreeStructure(),
                          nearestneighborstrategy=NearestNeighborStrategy, evaluateaverage=(Model == Constants.Average or Model == Constants.AverageSS), usesafetystock = (Model == Constants.AverageSS),
                          evpiseed=SeedArray[0],
                          model = MIPModel,
                          timehorizon=TimeHorizon )

    OutOfSampleTestResult = evaluator.EvaluateYQFixSolution( TestIdentifier, EvaluatorIdentifier, saveevaluatetab= True, filename = GetEvaluationFileName(), evpi=EVPI  )

    Model = tmpmodel
    GatherEvaluation()

def GatherEvaluation():
    global ScenarioSeed
    currentseedvalue = ScenarioSeed
    evaluator = Evaluator(Instance, [], [], "", ScenarioGeneration, treestructure=GetTreeStructure(), model = Model)
    EvaluationTab = []
    KPIStats = []
    nrfile = 0
    #Creat the evaluation table
    for seed in SeedArray:
        try:
            ScenarioSeed = seed
            filename =  GetEvaluationFileName()
            TestIdentifier[5] = seed
            #print "open file %rEvaluator.txt"%filename
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
        OutOfSampleTestResult =      evaluator.ComputeStatistic(EvaluationTab, NrEvaluation, TestIdentifier,EvaluatorIdentifier, KPIStat, -1)
        if Method == Constants.MIP and not EVPI:
            ComputeInSampleStatistis()
        PrintFinalResult()
    ScenarioSeed = currentseedvalue
    TestIdentifier[5] = currentseedvalue


#


# #This function compute some statistic about the genrated trees. It is usefull to check if the generator works as expected.
# def ComputeAverageGeneraor():
#     offset=1000
#     nrscenario = 10000
#     Average = [ 0  ] * Instance.NrProduct
#     data = [0] * nrscenario
#     for myseed in range(offset, nrscenario + offset, 1):
#         #Generate a random scenario
#         tree = ScenarioTree(  instance = Instance, branchperlevel = [1] * Instance.NrTimeBucket + [0] , seed = myseed, mipsolver = None, averagescenariotree = False, slowmoving = True )
#         mipsolver = MIPSolver(Instance, Model, tree, UseNonAnticipativity,
#                               implicitnonanticipativity=True,
#                               evaluatesolution=EvaluateSolution,
#                               givensolution=GivenQuantities,
#                               fixsolutionuntil=FixUntilTime )
#
#         scenarios = tree.GetAllScenarios( True )
#
#         data[myseed - offset] = scenarios[0].Demands[0][7]
#         for p in Instance.ProductSet:
#             Average[p] = Average[p] + scenarios[0].Demands[0][p]
#
#     for p in Instance.ProductSet:
#         Average[p] = Average[p] / nrscenario
#
#     print Average



def parseArguments():
    # Create argument parser
    parser = argparse.ArgumentParser()
    # Positional mandatory arguments
    parser.add_argument("Action", help="Evaluate, Solve, VSS, EVPI", type=str)
    parser.add_argument("Instance", help="Cname of the instance.", type=str)
    parser.add_argument("Model", help="Average/YQFix/YFiz .", type=str)
    parser.add_argument("NrScenario", help="the number of scenario used for optimization", type=str)
    parser.add_argument("ScenarioGeneration", help="MC,/RQMC.", type=str)
    parser.add_argument("-s", "--ScenarioSeed", help="The seed used for scenario generation", type=int, default= -1 )

    # Optional arguments
    parser.add_argument("-p", "--policy", help="NearestNeighbor", type=str, default="_")
    parser.add_argument("-n", "--nrevaluation", help="nr scenario used for evaluation.", type=int, default=500)
    parser.add_argument("-m", "--method", help="method used to solve", type=str, default="MIP")
    parser.add_argument("-f", "--fixuntil", help="Use with VSS action, howmany periods are fixed", type=int, default=0)
    parser.add_argument("-e", "--evpi", help="if true the evpi model is consdiered",  default=False, action='store_true')
    parser.add_argument("-c", "--mipsetting", help="test a specific mip solver parameter",  default="")
    parser.add_argument("-t", "--timehorizon", help="the time horizon used in shiting window.", type=int, default=1)
    parser.add_argument("-a", "--allscenario", help="generate all possible scenario.", type=int, default=0)
    # Print version
    parser.add_argument("--version", action="version", version='%(prog)s - Version 1.0')

    # Parse arguments
    args = parser.parse_args()

    global Action
    global InstanceName
    global Model
    global PolicyGeneration
    global NrScenario
    global ScenarioGeneration
    global ScenarioSeed

    global PolicyGeneration
    global NrEvaluation
    global SeedIndex
    global NearestNeighborStrategy
    global Method
    global FixUntilTime
    global EVPI
    global MIPSetting
    global TimeHorizon
    global AllScenario

    Action = args.Action
    InstanceName = args.Instance
    Model = args.Model
    Method = args.method
    NrScenario = args.NrScenario
    ScenarioGeneration = args.ScenarioGeneration
    ScenarioSeed = SeedArray[ args.ScenarioSeed ]
    SeedIndex = args.ScenarioSeed
    PolicyGeneration = args.policy
    FixUntilTime = args.fixuntil
    EVPI = args.evpi
    MIPSetting = args.mipsetting
    TimeHorizon = args.timehorizon
    AllScenario = args.allscenario
    if EVPI:
        PolicyGeneration ="EVPI"
        NearestNeighborStrategy = "EVPI"

    NearestNeighborStrategy = ""
    if PolicyGeneration in ["NNDAC", "NNSAC", "NND", "NNS" ]:
        PolicyGeneration = "NN"
        NearestNeighborStrategy = args.policy
    else:
        NearestNeighborStrategy = PolicyGeneration #to have something in the table of results
    NrEvaluation = args.nrevaluation

    SetTestIdentifierValue()
    return args

def SetTestIdentifierValue():
    global TestIdentifier
    global EvaluatorIdentifier
    TestIdentifier = [InstanceName, Model, Method, ScenarioGeneration, NrScenario, ScenarioSeed, EVPI]
    EvaluatorIdentifier = [PolicyGeneration, NearestNeighborStrategy, NrEvaluation, TimeHorizon, AllScenario]

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
    if Constants.LauchEvalAfterSolve :
        policyset = ["Re-solve"]# "NNSAC", "NNDAC", "Re-solve"]
        if Model == Constants.ModelYQFix or Model == Constants.Average or Model == Constants.AverageSS or  Constants.IsRule(Model):
                policyset = ["Fix", "Re-solve"]

        perfectsenarioset = [0]
        if Instance.Distribution == Constants.Binomial:
            perfectsenarioset = [0, 1]
        for policy in policyset:
            for perfectset in perfectsenarioset:
                if Constants.RunEvaluationInSeparatedJob:
                    jobname = "./Jobs/job_evaluate_%s_%s_%s_%s_%s_%s_%s" % (
                        TestIdentifier[0],  TestIdentifier[1],   TestIdentifier[4], TestIdentifier[3],  TestIdentifier[2],  policy, SeedIndex)
                    subprocess.call( ["qsub", jobname]  )
                else:
                    global PolicyGeneration
                    global NearestNeighborStrategy
                    global AllScenario
                    global NrEvaluation
                    PolicyGeneration = policy
                    NearestNeighborStrategy = policy
                    AllScenario = perfectsenarioset
                    if AllScenario == 1:
                        NrEvaluation = 4096
                    else:
                        NrEvaluation = 5000
                    SetTestIdentifierValue()


                    EvaluateSingleSol()

# #This function runs the evaluation jobs when the method is solved for the 5 seed:
# def RunEvaluationIfAllSolve(  ):
#     #Check among the available files, if one of the sceed is not solve
#     solutions = GetPreviouslyFoundSolution()
#     if len( solutions ) >= 5 :
#         policyset = ["NNDAC", "NNSAC", "NND", "NNS", "Resolve"]
#         if Model == Constants.ModelYQFix or Model == Constants.Average or Model == Constants.AverageSS or  Constants.IsRule(Model):
#             policyset = ["Fix", "Resolve"]
#
#
#         for policy in policyset:
#             if Constants.RunEvaluationInSeparatedJob:
#                 jobname = "./Jobs/job_evaluate_%s_%s_%s_%s_%s_%s_%s" % (
#                     TestIdentifier[0], TestIdentifier[1],  TestIdentifier[4],
#                     TestIdentifier[3], TestIdentifier[2], policy, SeedIndex)
#                 subprocess.call( ["qsub", jobname]  )
#             else:
#                 global PolicyGeneration
#                 global NearestNeighborStrategy
#                 PolicyGeneration = policy
#                 NearestNeighborStrategy = policy
#                 SetTestIdentifierValue()
#                 EvaluateSingleSol()
#
# def RunTestsAndEvaluation():
#     global ScenarioSeed
#     global SeedIndex
#     for s in range( 5 ):
#         SeedIndex = s
#         ScenarioSeed = SeedArray[ s ]
#         TestIdentifier[6] = ScenarioSeed
#         if Model == Constants.ModelYQFix:
#             SolveYQFix()
#         if Model == Constants.ModelYFix:
#             SolveYFix()
#         EvaluateSingleSol()
#
# # Compute the value of VSS as  defined in the paper: "The value of the stochastic solution in multistage problems" Laureano F. Escudero  Araceli Garin  Maria Merino  Gloria Perez
# def ComputeVSS( ):
#
#     global GivenQuantities
#     global GivenSetup
#     global EvaluateSolution
#     global FixUntilTime
#
#     print "Compute VSS"
#     # Get the YQFix solution
#     #TestIdentifier[2] = Constants.ModelYQFix
#     filedescription = GetTestDescription()
#     yqfixsolution = MRPSolution()
#     yqfixsolution.ReadFromFile(filedescription)
#     oldtest2 = TestIdentifier[2]
#     oldtest3 = TestIdentifier[3]
#     oldtest4 = TestIdentifier[4]
#     oldtest5 = TestIdentifier[5]
#
#     # Get the average value solution
#     TestIdentifier[2] = Constants.Average
#     TestIdentifier[3] = Constants.MIP
#     TestIdentifier[4] = Constants.MonteCarlo
#     TestIdentifier[5] = 1
#     filedescription = GetTestDescription()
#     averagesolution = MRPSolution()
#     averagesolution.ReadFromFile(filedescription)
#
#
#     TestIdentifier[2] = oldtest2
#     TestIdentifier[3] = oldtest3
#     TestIdentifier[4] = oldtest4
#     TestIdentifier[5] = oldtest5
#     EvaluateSolution = True
#     # Run the MIP with the additional constraint to fix the average solution up to the first fixuntiltime stages
#     treestructure = GetTreeStructure()
#
#     # Get the setup quantitities associated with the solultion
#     GivenSetup = [[averagesolution.Production[0][t][p]  for p in averagesolution.MRPInstance.ProductSet] for t in averagesolution.MRPInstance.TimeBucketSet]
#
#     GivenQuantities = [[averagesolution.ProductionQuantity[0][t][p] for p in averagesolution.MRPInstance.ProductSet]
#                         for t in averagesolution.MRPInstance.TimeBucketSet ]
#
#
#     if FixUntilTime == 0:
#         GivenSetup = []
#         GivenQuantities = []
#         EvaluateSolution = False
#
#     if TestIdentifier[2] == Constants.ModelYQFix and  FixUntilTime > 0:
#         FixUntilTime = Instance.NrTimeBucket
#
#     solution, mipsolver = MRP(treestructure, False, recordsolveinfo=True)
#
#     # Something need to be printed....
#     Parameter =  [ UseNonAnticipativity, Model, ComputeAverageSolution, ScenarioSeed]
#     data = TestIdentifier + SolveInformation +  Parameter + [ FixUntilTime , solution.TotalCost - yqfixsolution.TotalCost ]
#     d = datetime.now()
#     date = d.strftime('%m_%d_%Y_%H_%M_%S')
#     myfile = open(r'./Test/VSS/TestResult_%s_%s.csv' % (GetTestDescription(), FixUntilTime  ), 'wb')
#     wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
#     wr.writerow( data )
#     myfile.close()
#    # PrintTestResult()
#    # PrintFinalResult()

def GenerateInstances( ):

    csvfile = open("./Instances/InstanceNameTemp.csv", 'rb')
    data_reader = csv.reader(csvfile, delimiter=",", skipinitialspace=True)
    instancecreated = []
    instancenameslist = []
    for row in data_reader:
        instancenameslist.append(row)
    instancenameslist = ["01", "02", "04"] #instancenameslist[0]
    # for InstanceName in instancenameslist:
    #     #Distribution = "NonStationary"
    #     for Distribution in ["SlowMoving", "Normal", "Lumpy", "NonStationary"]:
    #      #     "NonStationary"]:
    #         possiblerateofknown = [50]
    #         if Distribution == "NonStationary":
    #             possiblerateofknown = [50, 75, 90]
    #         for rateknown in possiblerateofknown:
    #             for backordercost in [2, 4]:
    #                 for cap in [2, 5]:
    #                 #for holdingcost in ["n", "l", "l2"]:
    #                     leadtimes = 0
    #                     holdingcost="n"
    #     #            for leadtimes in [0,1,2,3,4,5]:
    #                     Instance.ReadFromFile(InstanceName, Distribution, backordercost,
    #                                           25, e=holdingcost, rk = rateknown,
    #                                           leadtimestructure = leadtimes ,
    #                                           lostsale = 10 *backordercost,
    #                                           capacity=cap)
    #                     Instance.SaveCompleteInstanceInExelFile()
    #                     instancecreated = instancecreated + [Instance.InstanceName]

    # Instance.ReadFromFile("01", "Normal", 4, 25, e="n", rk=50, leadtimestructure=0, lostsale=40, longtimehoizon = True, capacity=2)
    # Instance.SaveCompleteInstanceInExelFile()
    # instancecreated = instancecreated + [Instance.InstanceName]
    #
    # Instance.ReadFromFile("K0014313", "NonStationary", 2, 25, e="n", rk=50, leadtimestructure=0, lostsale=20, longtimehoizon = True)
    # Instance.SaveCompleteInstanceInExelFile()
    # instancecreated = instancecreated + [Instance.InstanceName]
    #
    #
    # Instance.ReadFromFile("01", "SlowMoving", 2, 25, e="n", rk=50, leadtimestructure=0, lostsale=20, capacity= 5, longtimehoizon = True )
    # Instance.SaveCompleteInstanceInExelFile()
    # instancecreated = instancecreated + [Instance.InstanceName]
    # # #
    # Instance.ReadFromFile("02", "Normal", 2, 25, e="n", rk=50, leadtimestructure=0, lostsale=20, capacity= 2, longtimehoizon = True )
    # Instance.SaveCompleteInstanceInExelFile()
    # instancecreated = instancecreated + [Instance.InstanceName]
    # # #
    # Instance.ReadFromFile("01",  "Lumpy", 2, 25, e="n", rk=50, leadtimestructure=0, lostsale=20, capacity= 5, longtimehoizon = True )
    # Instance.SaveCompleteInstanceInExelFile()
    # instancecreated = instancecreated + [Instance.InstanceName]
    # # #
    # Instance.ReadFromFile("04", "NonStationary", 2, 25, e="n", rk=50, leadtimestructure=0, lostsale=20, capacity= 2, longtimehoizon = True )
    # Instance.SaveCompleteInstanceInExelFile()
    # instancecreated = instancecreated + [Instance.InstanceName]
    #  #
    # Instance.ReadFromFile("02", "SlowMoving", 2, 25, e="n", rk=50, leadtimestructure=0, lostsale=20, capacity= 2, longtimehoizon = True )
    # Instance.SaveCompleteInstanceInExelFile()
    # instancecreated = instancecreated + [Instance.InstanceName]
    # # #
    # Instance.ReadFromFile("01", "Normal", 4, 25, e="n", rk=50, leadtimestructure=0, lostsale=40, capacity= 5, longtimehoizon = True )
    # Instance.SaveCompleteInstanceInExelFile()
    # instancecreated = instancecreated + [Instance.InstanceName]
    # # #
    # Instance.ReadFromFile("02", "Lumpy", 4, 25, e="n", rk=50, leadtimestructure=0, lostsale=40, capacity= 2, longtimehoizon = True )
    # Instance.SaveCompleteInstanceInExelFile()
    # instancecreated = instancecreated + [Instance.InstanceName]
    # # #
    # Instance.ReadFromFile("04", "NonStationary", 4, 25, e="n", rk=50, leadtimestructure=0, lostsale=40, capacity= 5, longtimehoizon = True )
    # Instance.SaveCompleteInstanceInExelFile()
    # instancecreated = instancecreated + [Instance.InstanceName]
    #  #
    # Instance.ReadFromFile("04", "SlowMoving", 4, 25, e="n", rk=50, leadtimestructure=0, lostsale=40, capacity= 2, longtimehoizon = True )
    # Instance.SaveCompleteInstanceInExelFile()
    # instancecreated = instancecreated + [Instance.InstanceName]
    # #  #
    # Instance.ReadFromFile("04", "Normal", 4, 25, e="n", rk=50, leadtimestructure=0, lostsale=40, capacity= 5, longtimehoizon = True )
    # Instance.SaveCompleteInstanceInExelFile()
    # instancecreated = instancecreated + [Instance.InstanceName]
    # # #
    # Instance.ReadFromFile("K0014313", "NonStationary", 2, 25, e="n", rk=50, leadtimestructure=0, lostsale=20, longtimehoizon = True)
    # Instance.SaveCompleteInstanceInExelFile()
    # instancecreated = instancecreated + [Instance.InstanceName]
    # # #
    # Instance.ReadFromFile("G5047424", "NonStationary", 4, 25, e="n", rk=75, leadtimestructure=0, lostsale=40, longtimehoizon = True)
    # Instance.SaveCompleteInstanceInExelFile()
    # instancecreated = instancecreated + [Instance.InstanceName]
    # # #
    # Instance.ReadFromFile("G0041535", "NonStationary", 2, 25, e="l", rk=25, leadtimestructure=1, lostsale=20, longtimehoizon = True)
    # Instance.SaveCompleteInstanceInExelFile()
    # Instancecreated = instancecreated + [Instance.InstanceName]
    # # #
    # Instance.ReadFromFile("K5014141", "NonStationary", 4, 25, e="l", rk=50, leadtimestructure=1, lostsale=40, longtimehoizon = True)
    # Instance.SaveCompleteInstanceInExelFile()
    # instancecreated = instancecreated + [Instance.InstanceName]
    # # #
    # Instance.ReadFromFile("G0047232", "NonStationary", 2, 25, e="n", rk=25, leadtimestructure=0, lostsale=20, longtimehoizon = True)
    # Instance.SaveCompleteInstanceInExelFile()
    # instancecreated = instancecreated + [Instance.InstanceName]
    # # #
    # Instance.ReadFromFile("K0014232", "NonStationary", 2, 25, e="n", rk=50, leadtimestructure=0, lostsale=20, longtimehoizon = True)
    # Instance.SaveCompleteInstanceInExelFile()
    # instancecreated = instancecreated + [Instance.InstanceName]
    # # #
    # Instance.ReadFromFile("G5047141", "NonStationary", 4, 25, e="n", rk=75, leadtimestructure=0, lostsale=40, longtimehoizon = True)
    # Instance.SaveCompleteInstanceInExelFile()
    # instancecreated = instancecreated + [Instance.InstanceName]
    # # #
    # Instance.ReadFromFile("G0041535", "NonStationary", 2, 25, e="n", rk=50, leadtimestructure=1, lostsale=20, longtimehoizon = True)
    # Instance.SaveCompleteInstanceInExelFile()
    # instancecreated = instancecreated + [Instance.InstanceName]
    # # #
    # Instance.ReadFromFile("K5014424", "NonStationary", 4, 25, e="l", rk=50, leadtimestructure=1, lostsale=40, longtimehoizon = True)
    # Instance.SaveCompleteInstanceInExelFile()
    # instancecreated = instancecreated + [Instance.InstanceName]
    # # #
    # Instance.ReadFromFile("G0047313", "NonStationary", 2, 25, e="n", rk=25, leadtimestructure=0, lostsale=20, longtimehoizon = True)
    # Instance.SaveCompleteInstanceInExelFile()
    # instancecreated = instancecreated + [Instance.InstanceName]

    Instance.ReadFromFile("K0011111", "Binomial", 2, 25, e="n", rk=50, leadtimestructure=0, lostsale=20, longtimehoizon = False)
    Instance.SaveCompleteInstanceInExelFile()
    instancecreated = instancecreated + [Instance.InstanceName]

    Instance.ReadFromFile("K0011121", "Binomial", 2, 25, e="n", rk=50, leadtimestructure=0, lostsale=20, longtimehoizon = False)
    Instance.SaveCompleteInstanceInExelFile()

    Instance.ReadFromFile("K0011211", "Binomial", 2, 25, e="n", rk=50, leadtimestructure=0, lostsale=20, longtimehoizon = False)
    Instance.SaveCompleteInstanceInExelFile()
    instancecreated = instancecreated + [Instance.InstanceName]

    Instance.ReadFromFile("K0011221", "Binomial", 2, 25, e="n", rk=50, leadtimestructure=0, lostsale=20, longtimehoizon = False)
    Instance.SaveCompleteInstanceInExelFile()
    instancecreated = instancecreated + [Instance.InstanceName]

    Instance.ReadFromFile("K0011311", "Binomial", 2, 25, e="n", rk=50, leadtimestructure=0, lostsale=20, longtimehoizon = False)
    Instance.SaveCompleteInstanceInExelFile()
    instancecreated = instancecreated + [Instance.InstanceName]

    Instance.ReadFromFile("K0011321", "Binomial", 2, 25, e="n", rk=50, leadtimestructure=0, lostsale=20, longtimehoizon = False)
    Instance.SaveCompleteInstanceInExelFile()
    instancecreated = instancecreated + [Instance.InstanceName]

    Instance.ReadFromFile("K0011411", "Binomial", 2, 25, e="n", rk=50, leadtimestructure=0, lostsale=20, longtimehoizon = False)
    Instance.SaveCompleteInstanceInExelFile()
    instancecreated = instancecreated + [Instance.InstanceName]

    Instance.ReadFromFile("K0011421", "Binomial", 2, 25, e="n", rk=50, leadtimestructure=0, lostsale=20, longtimehoizon = False)
    Instance.SaveCompleteInstanceInExelFile()
    instancecreated = instancecreated + [Instance.InstanceName]

    Instance.ReadFromFile("K0011511", "Binomial", 2, 25, e="n", rk=50, leadtimestructure=0, lostsale=20, longtimehoizon = False)
    Instance.SaveCompleteInstanceInExelFile()
    instancecreated = instancecreated + [Instance.InstanceName]

    Instance.ReadFromFile("K0011521", "Binomial", 2, 25, e="n", rk=50, leadtimestructure=0, lostsale=20, longtimehoizon = False)
    Instance.SaveCompleteInstanceInExelFile()
    instancecreated = instancecreated + [Instance.InstanceName]

    csvfile = open("./Instances/InstancesToSolve.csv", 'wb')
    data_rwriter = csv.writer(csvfile, delimiter=",", skipinitialspace=True)
    data_rwriter.writerow(instancecreated)



if __name__ == "__main__":
    instancename = ""
    try:
        args = parseArguments()

        Instance.ReadInstanceFromExelFile( InstanceName )
        #GenerateInstances()


    except KeyError:
        print "This instance does not exist. Instance should be in 01, 02, 03, ... , 38"


    if Action == Constants.Solve:
        Solve()



    if Action == Constants.Evaluate:
        if ScenarioSeed == -1:
            Evaluate()
        else:
            EvaluateSingleSol()

