import pandas as pd
from MIPSolver import MIPSolver
from ScenarioTree import ScenarioTree
from Constants import Constants
import time
import math
from datetime import datetime
import csv
from scipy import stats
import numpy as np
from MRPSolution import MRPSolution
from decimal import Decimal, ROUND_HALF_DOWN
import pickle
import cplex

class Evaluator:

    def __init__( self, instance, solutions=None, sddps=None, policy = "", scenariogenerationresolve = "", treestructure =[], nearestneighborstrategy = "", optimizationmethod = "MIP" ):
        self.Instance = instance
        self.Solutions = solutions
        self.SDDPs = sddps
        self.NrSolutions = max( len( self.Solutions ), len(  self.SDDPs ) )
        self.Policy = policy
        self.StartSeedResolve = 84752390
        self.ScenarioGenerationResolvePolicy = scenariogenerationresolve
        self.MIPResolveTime = [ None for t in instance.TimeBucketSet  ]
        self.IsDefineMIPResolveTime = [False for t in instance.TimeBucketSet]
        self.ReferenceTreeStructure = treestructure
        self.NearestNeighborStrategy = nearestneighborstrategy
        self.OptimizationMethod = optimizationmethod



    #This function evaluate the performance of a set of solutions obtain with the same method (different solutions due to randomness in the method)
    def EvaluateYQFixSolution( self, testidentifier, evaluateidentificator, model, saveevaluatetab = False, filename = ""):
        # Compute the average value of the demand
        nrscenario = evaluateidentificator[2]
        start_time = time.time()
        Evaluated = [ -1 for e in range(nrscenario) ]

        OutOfSampleSolution = None
        mipsolver = None
        firstsolution = True
        nrerror = 0

        for n in range( self.NrSolutions ):
            if self.OptimizationMethod == Constants.MIP:
                sol = self.Solutions[n]
                sol.ComputeAverageS()
                seed = sol.ScenarioTree.Seed

            if self.OptimizationMethod == Constants.SDDP:
                sddp = self.SDDPs[n]
                seed = sddp.StartingSeed
            evaluatoinscenarios, scenariotrees =self.GetScenarioSet(seed, nrscenario)
            if self.OptimizationMethod == Constants.SDDP:
                self.ForwardPassOnScenarios( sddp, evaluatoinscenarios)
            firstscenario = True
            self.IsDefineMIPResolveTime = [False for t in self.Instance.TimeBucketSet]

            for indexscenario in range( nrscenario ):
                scenario = evaluatoinscenarios[indexscenario]
                scenariotree = scenariotrees[indexscenario]
                if self.OptimizationMethod == Constants.MIP:
                    givensetup, givenquantty = self.GetDecisionFromSolutionForScenario(sol, model, scenario)

                if self.OptimizationMethod == Constants.SDDP:
                    givensetup, givenquantty = self.GetDecisionFromSDDPForScenario(sddp, indexscenario)

                #Solve the MIP and fix the decision to the one given.
                if firstscenario:
                    #Defin the MIP
                    mipsolver = MIPSolver(self.Instance, model, scenariotree,
                                                      True,
                                                      implicitnonanticipativity=False,
                                                      evaluatesolution=True,
                                                      givenquantities=givenquantty,
                                                      givensetups=givensetup,
                                                      fixsolutionuntil=self.Instance.NrTimeBucket )
                    mipsolver.BuildModel()
                else:
                    #update the MIP
                    mipsolver.ModifyMipForScenario( scenariotree )
                    if model == Constants.ModelYFix:
                        mipsolver.ModifyMipForFixQuantity( givenquantty )

                mipsolver.Cplex.parameters.advance = 0
                mipsolver.Cplex.parameters.lpmethod = 2
                solution = mipsolver.Solve()
                #CPLEX should always find a solution due to complete recourse
                if solution == None:
                    if Constants.Debug:
                        mipsolver.Cplex.write("mrp.lp")
                        raise NameError("error at seed %d with given qty %r"%(indexscenario, givenquantty))
                        nrerror = nrerror +1
                else:
                    Evaluated[ indexscenario ] = solution.TotalCost

                    #Record the obtain solution in an MRPsolution  OutOfSampleSolution
                    if firstsolution:
                        if firstscenario:
                            OutOfSampleSolution = solution
                        else:
                            OutOfSampleSolution.Merge( solution )

                    firstscenario = False

                if firstsolution:
                    for s in OutOfSampleSolution.Scenarioset:
                        s.Probability = 1.0/ len(  OutOfSampleSolution.Scenarioset )

            OutOfSampleSolution.ComputeStatistics()
            KPIStat = OutOfSampleSolution.PrintStatistics( testidentifier, "OutOfSample", indexscenario, nrscenario, seed )
            firstsolution = False

        #Save the evaluation result in a file (This is used when the evaluation is parallelized)
        if saveevaluatetab:
            with open(filename+"Evaluator.txt", "w+") as fp:
                pickle.dump(Evaluated, fp)
            with open(filename+"KPIStat.txt", "w+") as fp:
                pickle.dump(KPIStat, fp)

        duration = time.time() - start_time
        print "Duration od evaluation: %r, outofsampl error"%duration# %r"%( duration, Evaluated )

    #This function return the setup decision and quantity to produce for the scenario given in argument
    def GetDecisionFromSolutionForScenario(self, sol, model, scenario):

        # The setups are fixed in the first stage
        givensetup = [[sol.Production[0][t][p] for p in self.Instance.ProductSet]
                        for t in self.Instance.TimeBucketSet]

        # For model YQFix, the quatities are fixed, and can be taken from the solution
        if model == Constants.ModelYQFix or model == Constants.Average:
            givenquantty = [[sol.ProductionQuantity[0][t][p]
                                     for p in self.Instance.ProductSet]
                                     for t in self.Instance.TimeBucketSet]

        # For model YFix, the quantities depend on the scenarion
        if model == Constants.ModelYFix:
            givenquantty = [[0 for p in self.Instance.ProductSet] for t in self.Instance.TimeBucketSet]

            previousnode = sol.ScenarioTree.RootNode
            #At each time period the quantity to produce is decided based on the demand known up to now
            for ti in self.Instance.TimeBucketSet:
                demanduptotimet = [[scenario.Demands[t][p] for p in self.Instance.ProductSet] for t in range(ti)]

                if self.Policy == Constants.NearestNeighbor:
                    givenquantty[ti], previousnode, error = sol.GetQuantityToOrder(self.NearestNeighborStrategy, ti,
                                                                                    demanduptotimet, givenquantty,
                                                                                    previousnode)
                if self.Policy == Constants.InferS:
                    givenquantty[ti], error = sol.GetQuantityToOrderS( ti,demanduptotimet, givenquantty )

                if self.Policy == Constants.Resolve:
                    givenquantty[ti], error = self.GetQuantityByResolve(demanduptotimet, ti, givenquantty, sol,
                                                                        givensetup, model)
        return givensetup, givenquantty

    #This method run a forward pass of the SDDP algorithm on the considered set of scenarios
    def ForwardPassOnScenarios(self, sddp, scenarios):
        sddp.EvaluationMode = True
        # Make a forward pass on the
        # Get the set of scenarios

        sddp.CurrentSetOfScenarios = scenarios
        sddp.ScenarioNrSet = len( scenarios )
        # Modify the number of scenario at each stage
        for stage in sddp.StagesSet:
            sddp.Stage[stage].SetNrScenario( len( scenarios ))
            #sddp.Stage[stage].CurrentScenarioNr = 0

        sddp.ForwardPass()

    # This function return the setup decision and quantity to produce for the scenario given in argument
    def GetDecisionFromSDDPForScenario(self, sddp, scenario):

        #Get the setup quantitities associated with the solultion
        givensetup = [[sddp.GetSetupFixedEarlier(p,t,scenario) for p in self.Instance.ProductSet]
                      for t in self.Instance.TimeBucketSet]

        givenquantty = [[sddp.GetQuantityFixedEarlier(p,t,scenario) for p in self.Instance.ProductSet]
                      for t in range( self.Instance.NrTimeBucket - self.Instance.NrTimeBucketWithoutUncertainty )]

        #Copy the quantity from the last stage
        givenquantty = givenquantty + sddp.Stage[self.Instance.NrTimeBucket - self.Instance.NrTimeBucketWithoutUncertainty ].QuantityValues[0]

        return givensetup, givenquantty

    def GetScenarioSet(self, solveseed, nrscenario):
        scenarioset = []
        treeset = []
        # Use an offset in the seed to make sure the scenario used for evaluation are different from the scenario used for optimization
        offset = solveseed + 999323

        for seed in range(offset, nrscenario + offset, 1):
            # Generate a random scenario
            ScenarioSeed = seed
            # Evaluate the solution on the scenario
            treestructure = [1] + [1] * self.Instance.NrTimeBucket + [0]
            scenariotree = ScenarioTree(self.Instance, treestructure, ScenarioSeed, evaluationscenario=True)
            scenario = scenariotree.GetAllScenarios(False)[0]
            scenarioset.append( scenario )
            treeset.append( scenariotree)
        return scenarioset, treeset

    def ComputeInformation( self, Evaluation, nrscenario ):
        Sum = sum( Evaluation[s][sol] for s in range( nrscenario ) for sol in range( self.NrSolutions ) )
        Average = Sum / nrscenario
        sumdeviation = sum(
            math.pow( ( Evaluation[s][sol] - Average), 2 ) for s in range(nrscenario) for sol in range( self.NrSolutions ) )
        std_dev = math.sqrt( ( sumdeviation / nrscenario ) )

        EvaluateInfo = [ nrscenario, Average, std_dev ]

        return EvaluateInfo

    def ComputeStatistic(self, Evaluated, nrscenario, testidentifier, evaluateidentificator, KPIStat, nrerror, model  ):
        mean = np.mean(Evaluated)
        variance = math.pow(np.std(Evaluated), 2)
        K = len(Evaluated)
        M = nrscenario
        variance2 = ((1.0 / K) * sum(  (1.0 / M) * sum(math.pow(Evaluated[k][seed], 2) for seed in range(M)) for k in range(K))) - math.pow(mean,  2)
        covariance = ( ((1.0 / K) * sum(math.pow(sum(Evaluated[k][seed] for seed in range(M)) / M, 2) for k in range(K))) - math.pow( mean, 2))
        term = stats.norm.ppf(1 - 0.05) * math.sqrt((variance + (covariance * (M - 1))) / (K * M))
        LB = mean - term
        UB = mean + term
        d = datetime.now()
        date = d.strftime('%m_%d_%Y_%H_%M_%S')

        EvaluateInfo = self.ComputeInformation(Evaluated, nrscenario)


        MinAverage = min((1.0 / M) * sum(Evaluated[k][seed] for seed in range(M)) for k in range(K))
        MaxAverage = max((1.0 / M) * sum(Evaluated[k][seed] for seed in range(M)) for k in range(K))

        general = testidentifier + evaluateidentificator + [mean, variance, covariance, LB, UB, MinAverage, MaxAverage,
                                                            nrerror]

        columnstab = ["Instance", "Distribution", "Model", "NrInSampleScenario", "Identificator", "Mean", "Variance",
                      "Covariance", "LB", "UB", "Min Average", "Max Average", "nrerror"]
        myfile = open(r'./Test/Bounds/TestResultOfEvaluated_%s_%r_%s_%s.csv' % (
            self.Instance.InstanceName, evaluateidentificator[0], model, date), 'wb')
        wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
        wr.writerow(general)
        myfile.close()
        # generaldf = pd.DataFrame(general, index=columnstab)
        # generaldf.to_excel(writer, "General")
        KPIStat = KPIStat[3:]
        EvaluateInfo = [mean, LB, UB, MinAverage, MaxAverage, nrerror] + KPIStat

        # writer.save()
        return EvaluateInfo


    def EvaluateSDDPMethod( self ):
        #Get the required number of scenario
        self.GetScenarioSet()

    def GetQuantityByResolve(self, demanduptotimet, time, givenquantty, solution, givensetup, model):
        result = [0 for p in self.Instance.ProductSet]
        error = 0

        if time == 0:  # return the quantity at the root of the node
            result = [solution.ScenarioTree.RootNode.Branches[0].QuantityToOrderNextTime[p] for p in self.Instance.ProductSet]
        else:
            treestructure = [1] + [self.ReferenceTreeStructure[t - time + 1] if (
            t >= time and (t < (self.Instance.NrTimeBucket - self.Instance.NrTimeBucketWithoutUncertainty))) else 1 for
                                   t in range(self.Instance.NrTimeBucket)] + [0]

            self.StartSeedResolve = self.StartSeedResolve + 1
            scenariotree = ScenarioTree(self.Instance, treestructure, self.StartSeedResolve,
                                        givenfirstperiod=demanduptotimet,
                                        scenariogenerationmethod=self.ScenarioGenerationResolvePolicy)
            quantitytofix = [[givenquantty[t][p] for p in self.Instance.ProductSet] for t in range(time)]
            if not self.IsDefineMIPResolveTime[time]:
                mipsolver = MIPSolver(self.Instance, model, scenariotree,
                                      True,
                                      implicitnonanticipativity=True,
                                      evaluatesolution=True,
                                      givenquantities=quantitytofix,
                                      givensetups=givensetup,
                                      fixsolutionuntil=(time - 1))

                mipsolver.BuildModel()
                self.MIPResolveTime[time] = mipsolver
                self.IsDefineMIPResolveTime[time] = True
            else:
                self.MIPResolveTime[time].ModifyMipForScenario(scenariotree)
                self.MIPResolveTime[time].ModifyMipForFixQuantity(quantitytofix, fixuntil=time)

            self.MIPResolveTime[time].Cplex.parameters.advance = 0
            self.MIPResolveTime[time].Cplex.parameters.lpmethod = 1  # Dual primal cplex.CPX_ALG_DUAL
            solution = self.MIPResolveTime[time].Solve()

            # Get the corresponding node:
            if not solution is None:
                result = [solution.ProductionQuantity[0][time][p] for p in
                          self.Instance.ProductSet]
            else:
                if Constants.Debug:
                    self.MIPResolveTime[time].Cplex.write("MRP-Re-Solve.lp")
                    raise NameError("Infeasible MIP at time %d in Re-solve see MRP-Re-Solve.lp" % time)

                error = 1

        return result, error