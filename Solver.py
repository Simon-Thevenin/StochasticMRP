from Constants import Constants
from ScenarioTree import ScenarioTree
import time
from MIPSolver import MIPSolver
from DecentralizedMRP import DecentralizedMRP
import copy

from MRPSolution import MRPSolution

class Solver:

    # Constructor
    def __init__( self, instance, testidentifier, mipsetting, testdescription, evaluatesol, treestructure ):
        self.Instance = instance

        self.TestIdentifier = testidentifier
        self.InstanceName = testidentifier[0]
        self.Model = testidentifier[1]
        self.Method = testidentifier[2]
        self.ScenarioGeneration = testidentifier[3]
        self.NrScenario = testidentifier[4]
        self.ScenarioSeed = testidentifier[5]
        self.EVPI = testidentifier[6]
        self.GivenSetup = []
        self.MIPSetting = mipsetting
        self.UseSS = False
        self.TestDescription = testdescription
        self.EvaluateSolution = evaluatesol
        self.TreeStructure = treestructure

    #This method call the right method
    def Solve(self):
        solution = None
        if self.Model  == Constants.ModelYQFix or self.Model == Constants.Average or self.Model == Constants.AverageSS:
            solution = self.SolveYQFix()

        if self.Model  == Constants.ModelYFix:
            solution = self.SolveYFix()

        if self.Model  == Constants.ModelHeuristicYFix:
            solution = self.SolveYFixHeuristic()

        if Constants.IsRule(self.Model ):
            solution = self.SolveWithRule()

        return solution

    #This function creates the CPLEX model and solves it.
    def MRP( self, treestructur = [ 1, 8, 8, 4, 2, 1, 0 ], averagescenario = False, recordsolveinfo = False, yfixheuristic = False, warmstart = False ):
        scenariotree = ScenarioTree( self.Instance, treestructur, self.ScenarioSeed,
                                         averagescenariotree=averagescenario,
                                         scenariogenerationmethod = self.ScenarioGeneration,
                                         model= self.Model)

        MIPModel = self.Model
        if self.Model == Constants.Average:
            MIPModel = Constants.ModelYQFix

        mipsolver = MIPSolver( self.Instance, MIPModel, scenariotree, evpi = self.EVPI,
                                    implicitnonanticipativity=(not self.EVPI),
                                    evaluatesolution = self.EvaluateSolution,
                                    yfixheuristic= yfixheuristic,
                                    givensetups = self.GivenSetup,
                                    mipsetting = self.MIPSetting,
                                    warmstart = warmstart,
                                    usesafetystock= self.UseSS,
                                    logfile= self.TestDescription)
        if Constants.Debug:
            self.Instance.PrintInstance()

        if Constants.PrintScenarios:
            mipsolver.PrintScenarioToFile(  )

        if Constants.Debug:
            print "Start to model in Cplex"
        mipsolver.BuildModel()
        if Constants.Debug:
            print "Start to solve instance %s with Cplex"% self.Instance.InstanceName;


        # scenario = mipsolver.Scenarios
        # for s in scenario:
        #     print s.Probability
        # demands = [ [ [ scenario[w].Demands[t][p] for w in mipsolver.ScenarioSet ] for p in Instance.ProductSet ] for t in Instance.TimeBucketSet ]
        # for t in Instance.TimeBucketSet:
        #       for p in Instance.ProductWithExternalDemand:
        #           print "The demands for product %d at time %d : %r" %(p, t, demands[t][p] )
        #           with open('Histp%dt%d.csv'%(p, t), 'w+') as f:
        #                 #v_hist = np.ravel(v)  # 'flatten' v
        #                fig = PLT.figure()
        #                ax1 = fig.add_subplot(111)
        #                n, bins, patches = ax1.hist(demands[t][p], bins=100,  facecolor='green')
        #                PLT.show()

        solution = mipsolver.Solve()

        if recordsolveinfo:
            SolveInformation = mipsolver.SolveInfo

        return solution, mipsolver

    #Solve the two-stage version of the problem
    def SolveYQFix( self ):
        tmpmodel = self.Model
        start = time.time()

        if Constants.Debug:
            self.Instance.PrintInstance()

        average = False
        nrscenario = int(self.NrScenario)
        if self.Model == Constants.Average or self.Model == Constants.AverageSS:
            average = True
            nrscenario = 1

            if self.Model == Constants.AverageSS:
                 self.UseSS = True
                 self.Model = Constants.Average

        treestructure = [1, nrscenario] +  [1] * ( self.Instance.NrTimeBucket - 1 ) +[ 0 ]
        solution, mipsolver = self.MRP( treestructure, average, recordsolveinfo=True )

        end = time.time()
        solution.TotalTime = end - start

        self.Model = tmpmodel

        return solution

    #Solve the problem with rule based heurisitcs (L4L, EOQ, POQ, Silver-Meal)
    def SolveWithRule( self ):
        decentralizedmrp = DecentralizedMRP( self.Instance)
        solution = decentralizedmrp.SolveWithSimpleRule( self.Model )
        return solution

    # Run the method Heuristic YFix: First solve the 2-stage problem to fix the Y variables, then solve the multi-stages problem on large scenario tree.
    def SolveYFixHeuristic( self ):

        start = time.time()
        treestructure = [1, 500] + [1] * (self.Instance.NrTimeBucket - 1) + [0]
        self.Model = Constants.ModelYQFix
        chosengeneration = self.ScenarioGeneration
        self.ScenarioGeneration = Constants.RQMC
        solution, mipsolver = self.MRP(treestructure, False, recordsolveinfo=True)
        self.GivenSetup = [[solution.Production[0][t][p] for p in self.Instance.ProductSet] for t in self.Instance.TimeBucketSet]

        if Constants.Debug:
            self.Instance.PrintInstance()

        self.ScenarioGeneration = chosengeneration
        self.Model = Constants.ModelYFix

        solution, mipsolver = self.MRP(self.TreeStructure,
                                  averagescenario=False,
                                  recordsolveinfo=True,
                                  yfixheuristic=True)

        end = time.time()
        solution.TotalTime = end - start
        return solution


    #This function solve the multi-stage stochastic optimization model
    def SolveYFix( self ):
        start = time.time()

        if Constants.Debug:
            self.Instance.PrintInstance()


        treestructure = [1, 200] + [1] * (self.Instance.NrTimeBucket - 1) + [0]
        self.Model = Constants.ModelYQFix
        chosengeneration = self.ScenarioGeneration
        self.ScenarioGeneration = "RQMC"
        solution, mipsolver = self.MRP(treestructure, False, recordsolveinfo=True)
        self.GivenSetup =  [[solution.Production[0][t][p] for p in self.Instance.ProductSet] for t in self.Instance.TimeBucketSet]
        self.ScenarioGeneration = chosengeneration
        self.Model = Constants.ModelYFix


        if self.Method == "MIP" :
                solution, mipsolver = self.MRP(self.TreeStructure, averagescenario=False, recordsolveinfo=True, warmstart = True)

        if self.Method == "SDDP":
             sddpsolver = self.SDDP( self.Instance,
                                     self.ScenarioSeed,
                                     nrscenarioperiteration = int(self.NrScenario),
                                     generationmethod = self.ScenarioGeneration  )
             sddpsolver.Run()

             SolveInformation = sddpsolver.SolveInfo
             evaluator = self.Evaluator( self.Instance, [], [sddpsolver], optimizationmethod = Constants.SDDP)


             OutOfSampleTestResult = evaluator.EvaluateYQFixSolution( self.TestIdentifier, self.EvaluatorIdentifier, self.Model,
                                                                      saveevaluatetab=True, filename=self.GetEvaluationFileName())

        end = time.time()
        solution.TotalTime = end - start
        return solution



