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

class Evaluator:

    def __init__( self, instance, solutions, policy = "" ):
        self.Instance = instance
        self.Solutions = solutions
        self.NrSolutions = len( self.Solutions )
        self.Policy = policy
        self.StartSeedResolve = 84752390



    def GetQuantityByResolve( self, demanduptotimet, time, givenquantty, solution, givensetup, model ):
        result = 0

        if time == 0: # return the quantity at the root of the node
            result = [ solution.ScenarioTree.RootNode.Branches[ 0 ].QuantityToOrder[ p ] for p in self.Instance.ProductSet ]
        else:
            treestructure = [ 1 ] + [ 1 ]*time + [ 8 ]*(self.Instance.NrTimeBucket - self.Instance.NrTimeBucketWithoutUncertainty -time) + [1]*self.Instance.NrTimeBucketWithoutUncertainty + [0]
            self.StartSeedResolve = self.StartSeedResolve + 1
            scenariotree = ScenarioTree( self.Instance, treestructure, self.StartSeedResolve, givenfirstperiod = demanduptotimet )
            quantitytofix = [ [ givenquantty[t][p] for p in self.Instance.ProductSet ]  for t in range( time ) ]
            mipsolver = MIPSolver( self.Instance, model, scenariotree,
                                   True,
                                   implicitnonanticipativity = True,
                                   evaluatesolution = True,
                                   givenquantities = quantitytofix,
                                   givensetups = givensetup,
                                   fixsolutionuntil = (time-1) )

            mipsolver.BuildModel()

            solution = mipsolver.Solve()
           # scenariotree.Owner = None

            #Get the corresponding node:
            result = [ solution.ProductionQuantity.loc[self.Instance.ProductName[p], (time, 0)] for p in self.Instance.ProductSet ]


        return result

    def EvaluateYQFixSolution( self, testidentifier, nrscenario, printidentificator, model):
        # Compute the average value of the demand
        start_time = time.time()
        Evaluated = [ [ -1 for sol in self.Solutions ] for e in range(nrscenario) ]
        index = 0
        givenquantty = []
        OutOfSampleSolution = None
        mipsolver = None
        firstsolution = True
        KPIStat = []
        for sol in self.Solutions:
          #  if not sol == self.Solutions[ 0  ] and not sol == self.Solutions[ 1  ]:
                if model == Constants.ModelYQFix:
                    givenquantty = [ [ sol.ProductionQuantity.ix[p, t].get_value( 0 )
                                       for p in self.Instance.ProductSet ]
                                        for t in self.Instance.TimeBucketSet ]

                givensetup = [[sol.Production.ix[p, t].get_value(0) for p in self.Instance.ProductSet]
                              for t in self.Instance.TimeBucketSet]

                #Use an offset in the seed to make sure the scenario used for evaluation are different from the scenario used for optimization
                offset = sol.ScenarioTree.Seed + 999323
                for seed in range(offset, nrscenario + offset, 1):
                    #Generate a random scenario
                    ScenarioSeed =  seed
                    #Evaluate the solution on the scenario
                    for t in [self.Instance.NrTimeBucket -1]:
                        FixUntilTime = t
                        treestructure = [1] + [1] * self.Instance.NrTimeBucket + [0]

                        scenariotree = ScenarioTree( self.Instance, treestructure, ScenarioSeed, evaluationscenario = True )

                        if model == Constants.ModelYFix:
                            scenario = scenariotree.GetAllScenarios( False ) [0]
                            givenquantty = [ [ 0 for p in self.Instance.ProductSet ]  for t in self.Instance.TimeBucketSet ]

                            previousnode = sol.ScenarioTree.RootNode
                            for ti in self.Instance.TimeBucketSet:
                                demanduptotimet = [ [ scenario.Demands[t][p] for p in self.Instance.ProductSet ] for t in range(ti) ]
                                if self.Policy == Constants.NearestNeighbor:
                                    givenquantty[ti], previousnode = sol.GetQuantityToOrderAC( demanduptotimet, ti, previousnode )
                                if self.Policy == Constants.Resolve:
                                    givenquantty[ti] = self.GetQuantityByResolve( demanduptotimet, ti, givenquantty, sol, givensetup, model )

                        givenquantty = [ [ round( givenquantty[t][p], 2) for p in self.Instance.ProductSet ]  for t in self.Instance.TimeBucketSet ]

                        if seed == offset:
                            mipsolver = MIPSolver(self.Instance, model, scenariotree,
                                                  True,
                                                  implicitnonanticipativity=False,
                                                  evaluatesolution=True,
                                                  givenquantities=givenquantty,
                                                  givensetups=givensetup,
                                                  fixsolutionuntil=FixUntilTime )
                            mipsolver.BuildModel()
                        else:
                            mipsolver.ModifyMipForScenario( scenariotree )
                            if model == Constants.ModelYFix:
                                mipsolver.ModifyMipForFixQuantity( givenquantty )

                        solution = mipsolver.Solve()
                        if solution == None:
                            print "error at seed %d with given qty %r"%(seed, givenquantty)
                            mipsolver.Cplex.write("mrp.lp")

                        Evaluated[ seed - offset ][ index ] = solution.TotalCost

                        if firstsolution:
                            if seed == offset:
                                OutOfSampleSolution = solution
                            else:
                                OutOfSampleSolution.Merge( solution )

                index = index +1

                if firstsolution:
                    if nrscenario > 1:
                        OutOfSampleSolution.ReshapeAfterMerge()
                    OutOfSampleSolution.ComputeStatistics()
                    KPIStat = OutOfSampleSolution.PrintStatistics( testidentifier, "OutOfSample", offset, nrscenario, sol.ScenarioTree.Seed )
                    #print "Evaluation of YQ: %r" % Evaluated
                firstsolution = False

        mean = np.mean( Evaluated )
        variance = math.pow( np.std( Evaluated ), 2 )
        K = len( self.Solutions )
        M = nrscenario
        variance2 = ( (1.0 / K) * sum( (1.0 / M) * sum( math.pow( Evaluated[seed][k], 2 ) for seed in range(M)) for k in range(K)) )  - math.pow(mean, 2)
        covariance = ( ( (1.0 / K ) * sum( math.pow( sum(  Evaluated[seed][k] for seed in range( M ) ) / M, 2 ) for k in range( K ) )  )  - math.pow( mean, 2) )
        term =  stats.norm.ppf( 1-0.05) *  math.sqrt( ( variance  + ( covariance * (M-1) ) ) / ( K * M)  )
        LB = mean - term
        UB = mean + term
        d = datetime.now()
        date = d.strftime('%m_%d_%Y_%H_%M_%S')

        EvaluateInfo = self.ComputeInformation( Evaluated, nrscenario )
        duration = time.time() - start_time

        MinAverage = min( (1.0 / M) * sum( Evaluated[seed][k] for seed in range(M) ) for k in range(K) )
        MaxAverage = max((1.0 / M) * sum(Evaluated[seed][k] for seed in range(M)) for k in range(K) )

        general = testidentifier + [self.Instance.InstanceName, printidentificator, mean, variance, covariance, LB, UB, MinAverage, MaxAverage ]


        columnstab = ["Instance","Distribution", "Model", "NrInSampleScenario", "Identificator","Mean", "Variance", "Covariance", "LB", "UB", "Min Average", "Max Average"]
        myfile = open(r'./Test/Bounds/TestResultOfEvaluated_%s_%r_%s_%s.csv' % (
                                     self.Instance.InstanceName, printidentificator, model, date ), 'wb')
        wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
        wr.writerow(general)
        myfile.close()
       # generaldf = pd.DataFrame(general, index=columnstab)
       # generaldf.to_excel(writer, "General")
        EvaluateInfo = [mean, LB, UB, MinAverage, MaxAverage ] + KPIStat
        #writer.save()
        return EvaluateInfo


    def ComputeInformation( self, Evaluation, nrscenario ):
        Sum = sum( Evaluation[s][sol] for s in range( nrscenario ) for sol in range( self.NrSolutions ) )
        Average = Sum / nrscenario
        sumdeviation = sum(
            math.pow( ( Evaluation[s][sol] - Average), 2 ) for s in range(nrscenario) for sol in range( self.NrSolutions ) )
        std_dev = math.sqrt( ( sumdeviation / nrscenario ) )

        EvaluateInfo = [ nrscenario, Average, std_dev ]

        return EvaluateInfo