#import pandas as pd
#from matplotlib import pyplot as PLT
from MIPSolver import MIPSolver
from ScenarioTree import ScenarioTree
from Constants import Constants
from DecentralizedMRP import DecentralizedMRP
from RollingHorizonSolver import RollingHorizonSolver
import time
import math
from datetime import datetime
import csv
from scipy import stats
import numpy as np
import itertools
#from MRPSolution import MRPSolution
#from decimal import Decimal, ROUND_HALF_DOWN
import pickle
#from matplotlib import pyplot as PLT

class Evaluator:

    def __init__( self, instance, solutions=None, sddps=None, policy = "", evpi =False, scenariogenerationresolve = "", treestructure =[], nearestneighborstrategy = "", optimizationmethod = "MIP", evaluateaverage = False, usesafetystock = False, evpiseed = -1, model = "YQFix", timehorizon = 1, yeuristicyfix = False ):
        self.Instance = instance
        self.Solutions = solutions
        self.SDDPs = sddps
        self.NrSolutions = max( len( self.Solutions ), len(  self.SDDPs ) )
        self.Policy = policy
        self.StartSeedResolve = 84752390

        self.ScenarioGenerationResolvePolicy = scenariogenerationresolve
        self.EVPI = evpi
        if evpi:
            self.EVPISeed = evpiseed

        self.MIPResolveTime = [ None for t in instance.TimeBucketSet  ]
        self.IsDefineMIPResolveTime = [False for t in instance.TimeBucketSet]
        self.ReferenceTreeStructure = treestructure
        self.NearestNeighborStrategy = nearestneighborstrategy
        self.OptimizationMethod = optimizationmethod
        self.EvaluateAverage = evaluateaverage
        self.UseSafetyStock = usesafetystock
        self.Model = model
        self.YeuristicYfix = yeuristicyfix
        if policy == Constants.RollingHorizon:
            self.RollingHorizonSolver = RollingHorizonSolver( self.Instance,  self.Model , self.ReferenceTreeStructure,
                                                              self.StartSeedResolve, self.ScenarioGenerationResolvePolicy,
                                                              timehorizon, usesafetystock, self  )


    #This function evaluate the performance of a set of solutions obtain with the same method (different solutions due to randomness in the method)
    def EvaluateYQFixSolution( self, testidentifier, evaluateidentificator, saveevaluatetab = False, filename = "", evpi = False):

        # Compute the average value of the demand
        nrscenario = evaluateidentificator[2]
        allscenario = evaluateidentificator[4]
        start_time = time.time()
        Evaluated = [ -1 for e in range(nrscenario) ]
        Probabilities = [ -1 for e in range(nrscenario) ]
        OutOfSampleSolution = None
        mipsolver = None
        firstsolution = True
        nrerror = 0



        for n in range( self.NrSolutions ):
                sol = None
                if not evpi and not self.Policy == Constants.RollingHorizon:
                    if self.OptimizationMethod == Constants.MIP:
                        sol = self.Solutions[n]
                        if self.Model == Constants.ModelYFix and not sol.IsPartialSolution:
                            sol.ComputeAverageS()
                        seed = sol.ScenarioTree.Seed
                else:
                    if  evpi:
                        seed = self.EVPISeed
                    else:
                        seed = self.StartSeedResolve


                if self.OptimizationMethod == Constants.SDDP:
                    sddp = self.SDDPs[n]
                    seed = sddp.StartingSeed
                evaluatoinscenarios, scenariotrees =self.GetScenarioSet(seed, nrscenario, allscenario)
                if self.OptimizationMethod == Constants.SDDP:
                    self.ForwardPassOnScenarios( sddp, evaluatoinscenarios)
                firstscenario = True
                self.IsDefineMIPResolveTime = [False for t in self.Instance.TimeBucketSet]

                average = 0
                totalproba = 0
                for indexscenario in range( nrscenario ):
                    scenario = evaluatoinscenarios[indexscenario]
                    scenariotree = scenariotrees[indexscenario]

                    if not evpi:
                        if self.OptimizationMethod == Constants.MIP:
                            givensetup, givenquantty = self.GetDecisionFromSolutionForScenario(sol,  scenario)

                        if self.OptimizationMethod == Constants.SDDP:
                            givensetup, givenquantty = self.GetDecisionFromSDDPForScenario(sddp, indexscenario)
                            # Solve the MIP and fix the decision to the one given.
                            if Constants.Debug:
                                for t in self.Instance.TimeBucketSet:
                                    print "Quantity:%r" % givenquantty[t]
                                    print "Demand:%r" % scenario.Demands[t]

                    else:
                        givensetup = []
                        givenquantty = []


                    if firstscenario:
                        #Defin the MIP
                        if not evpi:
                            mipsolver = MIPSolver(self.Instance, Constants.ModelYQFix, scenariotree,
                                                              evpi=False,
                                                              implicitnonanticipativity=False,
                                                              evaluatesolution=True,
                                                              givenquantities=givenquantty,
                                                              givensetups=givensetup,
                                                              fixsolutionuntil=self.Instance.NrTimeBucket)
                        else:
                            mipsolver = MIPSolver(self.Instance, self.Model, scenariotree,
                                                  evpi=True )
                        mipsolver.BuildModel()
                    else:
                        #update the MIP
                        mipsolver.ModifyMipForScenarioTree( scenariotree )
                        if not self.Policy == Constants.Fix and not evpi:
                            mipsolver.ModifyMipForFixQuantity( givenquantty )

                        if self.Policy == Constants.RollingHorizon:
                            mipsolver.ModifyMIPForSetup(givensetup)


                    mipsolver.Cplex.parameters.advance = 0
                    #mipsolver.Cplex.parameters.lpmethod = 2
                    mipsolver.Cplex.parameters.lpmethod.set(mipsolver.Cplex.parameters.lpmethod.values.barrier)


                    solution = mipsolver.Solve()


                    #CPLEX should always find a solution due to complete recourse
                    if solution == None:
                        if Constants.Debug:
                            mipsolver.Cplex.write("mrp.lp")
                            print givensetup
                            print givenquantty
                            raise NameError("error at seed %d with given qty %r"%(indexscenario, givenquantty))
                            nrerror = nrerror +1
                    else:
                        Evaluated[ indexscenario ] = solution.TotalCost
                        if allscenario ==  0:
                            scenario.Probability = 1.0 / float( nrscenario )
                        Probabilities[ indexscenario ] = scenario.Probability
                        average +=  solution.TotalCost * scenario.Probability
                        totalproba += scenario.Probability
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

        duration = time.time() - start_time
        if Constants.Debug:
            print "Duration od evaluation: %r, outofsampl cost:%r total proba:%r" % (duration, average, totalproba)  # %r"%( duration, Evaluated )
        self.EvaluationDuration = duration

        KPIStat = OutOfSampleSolution.PrintStatistics( testidentifier, "OutOfSample", indexscenario, nrscenario, seed, duration, False )
        firstsolution = False

        #Save the evaluation result in a file (This is used when the evaluation is parallelized)
        if saveevaluatetab:
                with open(filename+"Evaluator.txt", "w+") as fp:
                    pickle.dump(Evaluated, fp)

                with open(filename + "Probabilities.txt", "w+") as fp:
                    pickle.dump(Probabilities, fp)

                with open(filename+"KPIStat.txt", "w+") as fp:
                    pickle.dump(KPIStat, fp)

        if Constants.PrintDetailsExcelFiles:
            namea = "_".join(str(elm) for elm in testidentifier)
            nameb = "_".join(str(elm) for elm in evaluateidentificator)
            OutOfSampleSolution.PrintToExcel(namea+nameb+".xlsx")



    #This function return the setup decision and quantity to produce for the scenario given in argument
    def GetDecisionFromSolutionForScenario(self, sol,  scenario):

        givenquantty = [[0 for p in self.Instance.ProductSet] for t in self.Instance.TimeBucketSet]
        givensetup = [[0 for p in self.Instance.ProductSet] for t in self.Instance.TimeBucketSet]
        if self.Policy == Constants.RollingHorizon:
            givensetup, givenquantty = self.RollingHorizonSolver.ApplyRollingHorizonSimulation( scenario )


        else:
            # The setups are fixed in the first stage
            givensetup = [[ (sol.Production[0][t][p] ) for p in self.Instance.ProductSet]
                            for t in self.Instance.TimeBucketSet]

            # For model YQFix, the quatities are fixed, and can be taken from the solution
            if self.Policy == Constants.Fix:
                givenquantty = [[ sol.ProductionQuantity[0][t][p]
                                         for p in self.Instance.ProductSet]
                                         for t in self.Instance.TimeBucketSet]

            # For model YFix, the quantities depend on the scenarion
            else:
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
                         givenquantty[ti], error = self.GetQuantityByResolve(demanduptotimet, ti, givenquantty, sol,  givensetup)

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
        givenquantty = givenquantty + sddp.Stage[self.Instance.NrTimeBucket - self.Instance.NrTimeBucketWithoutUncertainty ].QuantityValues[scenario]

        return givensetup, givenquantty

    def GetScenarioSet(self, solveseed, nrscenario, allscenarios):
        scenarioset = []
        treeset = []
        # Use an offset in the seed to make sure the scenario used for evaluation are different from the scenario used for optimization
        offset = solveseed + 999323


        #Uncoment to generate all the scenario if a  distribution with smallll support is used
        if allscenarios==1:
            if Constants.Debug:
                    print "Generate all the scenarios"

            scenariotree = ScenarioTree(self.Instance, [1]+ [1]*self.Instance.NrTimeBucketWithoutUncertaintyBefore + [ 8, 8, 8, 8, 0], offset,
                                         scenariogenerationmethod=Constants.All,
                                         model= Constants.ModelYFix)
            scenarioset = scenariotree.GetAllScenarios(False)

            for s in range( len( scenarioset ) ):
                tree = ScenarioTree(self.Instance, [1, 1, 1, 1, 1, 1, 1, 1, 0], offset,
                                            model=Constants.ModelYFix,
                                    givenfirstperiod=  scenarioset[s].Demands )
                treeset.append( tree )

        else:
            for seed in range(offset, nrscenario + offset, 1):
                # Generate a random scenario
                ScenarioSeed = seed
                # Evaluate the solution on the scenario
                treestructure = [1] + [1] * self.Instance.NrTimeBucket + [0]

                scenariotree = ScenarioTree(self.Instance, treestructure, ScenarioSeed, evaluationscenario=True,
                                            scenariogenerationmethod="MC")
                scenario = scenariotree.GetAllScenarios(False)[0]

                scenarioset.append(scenario)
                treeset.append(scenariotree)


        return scenarioset, treeset

    def ComputeInformation( self, Evaluation, nrscenario ):
        Sum = sum( Evaluation[s][sol] for s in range( nrscenario ) for sol in range( self.NrSolutions ) )
        Average = Sum / nrscenario
        sumdeviation = sum(
            math.pow( ( Evaluation[s][sol] - Average), 2 ) for s in range(nrscenario) for sol in range( self.NrSolutions ) )
        std_dev = math.sqrt( ( sumdeviation / nrscenario ) )

        EvaluateInfo = [ nrscenario, Average, std_dev ]

        return EvaluateInfo

    def ComputeStatistic(self, Evaluated, Probabilities, nrscenario, testidentifier, evaluateidentificator, KPIStat, nrerror  ):

        mean = float( sum( np.dot(Evaluated[k], Probabilities[k]) for k in range( len(Evaluated) ) ) / float( len(Evaluated) ) )
        K =  len(Evaluated)
        M = nrscenario
        variancepondere = (1.0 / K) * \
                           sum(   Probabilities[k][seed] * math.pow(Evaluated[k][seed]- mean, 2)
                                   for seed in range(M)
                                   for k in range(K))


        variance2 = ((1.0 / K) * sum(  (1.0 / M) * sum(math.pow(Evaluated[k][seed], 2) for seed in range(M)) for k in range(K))) - math.pow(mean,  2)
        covariance = 0

        for seed in range(M):
            step = 1
            for k in range(K):
                step *=   (Evaluated[k][seed] - mean)
            covariance +=   Probabilities[0][seed] * 1/K *step

        term =  stats.norm.ppf(1 - 0.05) * math.sqrt(max( ( (variancepondere + (covariance * (M - 1))) / (K * M)), 0.0) )
        LB = mean - term
        UB = mean + term
        d = datetime.now()
        date = d.strftime('%m_%d_%Y_%H_%M_%S')

        EvaluateInfo = self.ComputeInformation(Evaluated, nrscenario)


        MinAverage = min((1.0 / M) * sum(Evaluated[k][seed] for seed in range(M)) for k in range(K))
        MaxAverage = max((1.0 / M) * sum(Evaluated[k][seed] for seed in range(M)) for k in range(K))

        if Constants.PrintDetailsExcelFiles:
            general = testidentifier + evaluateidentificator + [mean, variance2, covariance, LB, UB, MinAverage, MaxAverage,
                                                            nrerror]

            columnstab = ["Instance", "Distribution", "Model", "NrInSampleScenario", "Identificator", "Mean", "Variance",
                      "Covariance", "LB", "UB", "Min Average", "Max Average", "nrerror"]
            myfile = open(r'./Test/Bounds/TestResultOfEvaluated_%s_%r_%s_%s.csv' % (
                            self.Instance.InstanceName, evaluateidentificator[0], self.Model, date), 'wb')
            wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
            wr.writerow(general)
            myfile.close()

        KPIStat = KPIStat[6:] #The first values in KPIStats are not interesting for out of sample evalution (see MRPSolution::PrintStatistics)
        EvaluateInfo = [mean, LB, UB, MinAverage, MaxAverage, nrerror] + KPIStat

        return EvaluateInfo


    def EvaluateSDDPMethod( self ):
        #Get the required number of scenario
        self.GetScenarioSet()

    def GetQuantityByResolve(self, demanduptotimet, time, givenquantty, solution, givensetup ):
        result = [0 for p in self.Instance.ProductSet]
        error = 0
        # decentralized = DecentralizedMRP(self.Instance)
        # safetystock = decentralized.ComputeSafetyStock()
        # print safetystock
        # demanduptotimet = [  [  float(self.Instance.ForecastedAverageDemand[t][p]) + safetystock[t][p]
        #                            for p in self.Instance.ProductSet] for t in range( time ) ]
        if time <= self.Instance.NrTimeBucketWithoutUncertaintyBefore:  # return the quantity at the root of the node
           # result = [solution.ScenarioTree.RootNode.Branches[0].QuantityToOrderNextTime[p] for p in self.Instance.ProductSet]

            result = [solution.ProductionQuantity[0][time][p]  for p in self.Instance.ProductSet]

        else:
            quantitytofix = [[givenquantty[t][p] for p in self.Instance.ProductSet] for t in range(time)]


            if self.Model in [ Constants.L4L, Constants.EOQ, Constants.POQ, Constants.SilverMeal]:
                result = self.ResolveRule(quantitytofix,  givensetup, demanduptotimet , time)
            else:
                result, error = self.ResolveMIP(quantitytofix , givensetup, demanduptotimet, time )



        return result, error

    def ResolveRule(self, quantitytofix,  givensetup, demanduptotimet, time):

        decentralizedmrp = DecentralizedMRP(self.Instance)
        solution = decentralizedmrp.SolveWithSimpleRule( self.Model, givensetup, quantitytofix, time-1, demanduptotimet)

        result = [solution.ProductionQuantity[0][time][p] for p in self.Instance.ProductSet]
        return result



    def ResolveMIP(self, quantitytofix,  givensetup, demanduptotimet, time):
            if not self.IsDefineMIPResolveTime[time]:
                treestructure = [1] \
                                + [self.ReferenceTreeStructure[t - ( time - self.Instance.NrTimeBucketWithoutUncertaintyBefore)+ 1]
                                   if (  t >= time and (t < (self.Instance.NrTimeBucket - self.Instance.NrTimeBucketWithoutUncertaintyAfter)))
                                   else 1 for
                                    t in range(self.Instance.NrTimeBucket)] \
                                + [0]
                if self.Model == Constants.ModelYQFix:
                    treestructure = [1] \
                                    + [self.ReferenceTreeStructure[1]
                                       if (t == time )
                                       else 1 for
                                       t in range(self.Instance.NrTimeBucket)] \
                                    + [0]

                if self.Model == Constants.ModelYQFix and self.ScenarioGenerationResolvePolicy == Constants.All :
                    nrstochasticperiod = self.Instance.NrTimeBucket - time
                    treestructure = [1] \
                                + [ int( math.pow(8,nrstochasticperiod) )
                                   if (  t == time and (t < (self.Instance.NrTimeBucket - self.Instance.NrTimeBucketWithoutUncertaintyAfter)  ) )
                                   else 1
                                   for t in range(self.Instance.NrTimeBucket)] \
                                + [0]

                self.StartSeedResolve = self.StartSeedResolve + 1
                scenariotree = ScenarioTree(self.Instance, treestructure, self.StartSeedResolve,
                                            averagescenariotree = self.EvaluateAverage,
                                            givenfirstperiod=demanduptotimet,
                                            scenariogenerationmethod=self.ScenarioGenerationResolvePolicy,
                                            model= self.Model)

                mipsolver = MIPSolver(self.Instance, self.Model, scenariotree,
                                      self.EVPI,
                                      implicitnonanticipativity=( not self.EVPI),
                                      evaluatesolution=True,
                                      givenquantities=quantitytofix,
                                      givensetups=givensetup,
                                      fixsolutionuntil=(time -1 ), #time lower or equal
                                      demandknownuntil =  time,
                                      usesafetystock= self.UseSafetyStock)
                #time stricty lower



                # scenario = mipsolver.Scenarios
                # for s in scenario:
                #     print s.Probability
                # demands = [ [ [ scenario[w].Demands[t][p] for w in mipsolver.ScenarioSet ] for p in self.Instance.ProductSet ] for t in self.Instance.TimeBucketSet ]
                # for t in self.Instance.TimeBucketSet:
                #       for p in self.Instance.ProductWithExternalDemand:
                #           print "The demands for product %d at time %d : %r" %(p, t, demands[t][p] )
                #           with open('Histp%dt%d.csv'%(p, t), 'w+') as f:
                #                 #v_hist = np.ravel(v)  # 'flatten' v
                #                fig = PLT.figure()
                #                ax1 = fig.add_subplot(111)
                #                n, bins, patches = ax1.hist(demands[t][p], bins=100,  facecolor='green')
                #                PLT.show()
                #

                mipsolver.BuildModel()
                self.MIPResolveTime[time] = mipsolver
                self.IsDefineMIPResolveTime[time] = True
            else:

                self.MIPResolveTime[time].ModifyMipForScenario(demanduptotimet, time)
                self.MIPResolveTime[time].ModifyMipForFixQuantity(quantitytofix, fixuntil=time)

            #self.MIPResolveTime[time].Cplex.parameters.advance = 0
            #self.MIPResolveTime[time].Cplex.parameters.lpmethod = 1  # Dual primal cplex.CPX_ALG_DUAL

            # scenario = mipsolver.Scenarios
            # demands = [[[scenario[w].Demands[t][p] for w in mipsolver.ScenarioSet] for p in self.Instance.ProductSet] for t
            #            in self.Instance.TimeBucketSet]
            # for t in self.Instance.TimeBucketSet:
            #     for p in self.Instance.ProductWithExternalDemand:
            #         print "The demands for product %d at time %d : %r" % (p, t, demands[t][p])
            #         with open('Histp%dt%d.csv' % (p, t), 'w+') as f:
            #             # v_hist = np.ravel(v)  # 'flatten' v
            #             fig = PLT.figure()
            #             ax1 = fig.add_subplot(111)
            #             n, bins, patches = ax1.hist(demands[t][p], bins=100, normed=1, facecolor='green')
            #             PLT.show()
            self.MIPResolveTime[time].Cplex.parameters.advance = 1
            #self.MIPResolveTime[time].Cplex.parameters.lpmethod = 2
            self.MIPResolveTime[time].Cplex.parameters.lpmethod.set(self.MIPResolveTime[time].Cplex.parameters.lpmethod.values.barrier)

            solution = self.MIPResolveTime[time].Solve( createsolution = False)



            #if time == 4:
            #    solution = self.MIPResolveTime[time].Solve()
            #    solution.PrintToExcel("ResolutionTems4")

            if Constants.Debug:
                print "End solving"


            #self.MIPResolveTime[time].Cplex.write("MRP-Re-Solve.lp")
            # Get the corresponding node:
            error = 0
            sol = self.MIPResolveTime[time].Cplex.solution
            if sol.is_primal_feasible():
                array = [self.MIPResolveTime[time].GetIndexQuantityVariable(p, time, 0) for p in self.Instance.ProductSet];

                result = sol.get_values(array)
                if Constants.Debug:
                    print result
                #result = [solution.ProductionQuantity[0][time][p] for p in
                #          self.Instance.ProductSet]
            else:
                if Constants.Debug:
                    self.MIPResolveTime[time].Cplex.write("MRP-Re-Solve.lp")
                    raise NameError("Infeasible MIP at time %d in Re-solve see MRP-Re-Solve.lp" % time)

                error = 1

            return result, error