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

    def __init__( self, instance, solutions ):
        self.Instance = instance
        self.Solutions = solutions
        self.NrSolutions = len( self.Solutions )

    def EvaluateYQFixSolution( self, nrscenario, printidentificator, model):
        # Compute the average value of the demand
        start_time = time.time()
        Evaluated = [ [ -1 for sol in self.Solutions ] for e in range(nrscenario) ]
        index = 0
        givenquantty = []
        OutOfSampleSolution = None
        mipsolver = None
        firstsolution = True
        for sol in self.Solutions:
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
                            givenquantty[ti], previousnode = sol.GetQuantityToOrderAC( demanduptotimet, ti, previousnode )
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


                    solution = mipsolver.Solve()
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
                OutOfSampleSolution.PrintStatistics( "OutOfSample", offset, nrscenario, sol.ScenarioTree.Seed )
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

     #   writer = pd.ExcelWriter( './Test/Bounds/TestResultOfEvaluated_%s_%r_%s_%s.xlsx' % (
     #                                self.Instance.InstanceName, printidentificator, model, date ) )
     #   evvaluationdataframe = pd.DataFrame(Evaluated)

     #   evvaluationdataframe.to_excel( writer, "Evaluation" )
        EvaluateInfo = self.ComputeInformation( Evaluated, nrscenario )
        duration = time.time() - start_time

        MinAverage = min( (1.0 / M) * sum( Evaluated[seed][k] for seed in range(M) ) for k in range(K) )
        MaxAverage = max((1.0 / M) * sum(Evaluated[seed][k] for seed in range(M)) for k in range(K) )

        general = [self.Instance.InstanceName, model, printidentificator, mean, variance, covariance, LB, UB, MinAverage, MaxAverage ]


        columnstab = ["Instance name", "Model", "Identificator","Mean", "Variance", "Covariance", "LB", "UB", "Min Average", "Max Average"]
        myfile = open(r'./Test/Bounds/TestResultOfEvaluated_%s_%r_%s_%s.csv' % (
                                     self.Instance.InstanceName, printidentificator, model, date ), 'wb')
        wr = csv.writer(myfile, quoting=csv.QUOTE_ALL)
        wr.writerow(general)
        myfile.close()
       # generaldf = pd.DataFrame(general, index=columnstab)
       # generaldf.to_excel(writer, "General")

        #writer.save()
        return [duration] + EvaluateInfo


    def ComputeInformation( self, Evaluation, nrscenario ):
        Sum = sum( Evaluation[s][sol] for s in range( nrscenario ) for sol in range( self.NrSolutions ) )
        Average = Sum / nrscenario
        sumdeviation = sum(
            math.pow( ( Evaluation[s][sol] - Average), 2 ) for s in range(nrscenario) for sol in range( self.NrSolutions ) )
        std_dev = math.sqrt( ( sumdeviation / nrscenario ) )

        EvaluateInfo = [ nrscenario, Average, std_dev ]

        return EvaluateInfo