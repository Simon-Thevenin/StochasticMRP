from Constants import Constants
from ScenarioTree import ScenarioTree
import time
from MIPSolver import MIPSolver
from DecentralizedMRP import DecentralizedMRP
import copy

from MRPSolution import MRPSolution

class RollingHorizonSolver:

    def __init__(self, instance,  model, treestructure, seed, scenariogenerationmethod ):
        self.GlobalInstance = instance
        self.WindowSize = self.GlobalInstance.MaxLeadTime + 1

        self.Seed = seed
        self.Treestructure =treestructure
        self.Model = model
        self.ScenarioGenerationResolvePolicy = scenariogenerationmethod

        self.SubInstance = self.CreateSubInstances()
        self.RollingHorizonMIPs =  self.DefineMIPsRollingHorizonSimulation()

        self.Solution = MRPSolution.GetEmptySolution( instance )


    #This function define a set of MIP, each MIP correspond to a slice of the horizon
    def DefineMIPsRollingHorizonSimulation(self):
        result = []

        # For each subinstance, Create a tree, and generate a MIP
        for instance in self.SubInstance:
            instance.PrintInstance()
            treestructure =  copy.deepcopy(self.Treestructure)
            if self.Model == Constants.ModelYFix:
                treestructure =  [1] * instance.NrTimeBucketWithoutUncertaintyBefore  + treestructure
            else:
                treestructure = treestructure[:-1] + [1] * instance.NrTimeBucketWithoutUncertaintyBefore + [0]
            scenariotree = ScenarioTree(instance=instance, branchperlevel=treestructure, seed = self.Seed,
                                        averagescenariotree=False,
                                        scenariogenerationmethod=self.ScenarioGenerationResolvePolicy,
                                        model=self.Model)

            print "Check what happen with average SS"
            mipsolver = MIPSolver(instance, self.Model, scenariotree,
                                  False,
                                  implicitnonanticipativity=True,
                                  evaluatesolution=False,
                                  usesafetystock=(self.Model == Constants.AverageSS),
                                  rollinghorizon= True)
            mipsolver.BuildModel()
            result.append( mipsolver )

        return result


    # Create the set of subinstance to solve in a rolling horizon approach
    def CreateSubInstances( self ):
            """ :type result: [ {MRPInstance} ]"""
            nrshift = self.GlobalInstance.NrTimeBucket  - self.GlobalInstance.NrTimeBucketWithoutUncertaintyBefore

            result = [None for i in range(nrshift)]

            startwindow = -1
            previousnrperiodwithoutuncertaintybefore = 0
            for i in range(nrshift):
                startwindow += 1 + previousnrperiodwithoutuncertaintybefore
                nrperiodwithoutuncertaintybefore = max(0, self.GlobalInstance.NrTimeBucketWithoutUncertaintyBefore - startwindow)
                endwindow = startwindow + self.WindowSize + nrperiodwithoutuncertaintybefore

                result[i] = copy.deepcopy(self.GlobalInstance)
                result[i].NrTimeBucket = self.WindowSize + nrperiodwithoutuncertaintybefore
                result[i].ForecastedAverageDemand = [self.GlobalInstance.ForecastedAverageDemand[startwindow + t]
                                                     if startwindow + t < self.GlobalInstance.NrTimeBucket
                                                     else [0.0]*self.GlobalInstance.NrProduct
                                                     for t in range(result[i].NrTimeBucket)]
                result[i].ForcastedStandardDeviation = [self.GlobalInstance.ForcastedStandardDeviation[startwindow + t]
                                                        if startwindow + t < self.GlobalInstance.NrTimeBucket
                                                        else [0.0]*self.GlobalInstance.NrProduct
                                                        for t in range(result[i].NrTimeBucket) ]
                result[i].NrTimeBucketWithoutUncertaintyBefore = max(0,
                                                                     self.GlobalInstance.NrTimeBucketWithoutUncertaintyBefore - startwindow)
                result[i].ComputeIndices()

                previousnrperiodwithoutuncertaintybefore = nrperiodwithoutuncertaintybefore

            return result

    #This function simulate the use of the stochastic optimization approach for given scenario
    def ApplyRollingHorizonSimulation(self, scenario):
        self.Solution = MRPSolution.GetEmptySolution( self.GlobalInstance)

        lastInventory = [ 0 for p in self.GlobalInstance.ProductSet]

        timetodecide = 0
        for mip in self.RollingHorizonMIPs:

            if Constants.Debug:
                print " Solve instance with time window [ %r, %r]"%( timetodecide, timetodecide + self.WindowSize )

            timedemandknownuntil = timetodecide - 1

            startinginventory = self.GetEndingInventoryAt(timetodecide ,   scenario)
            print startinginventory
            wronginventory = False
            for  p in self.GlobalInstance.ProductSet:
                if ( not self.GlobalInstance.HasExternalDemand[p] ) and ( lastInventory[p]  < startinginventory[p] - 0.01 or lastInventory[p]  > startinginventory[p] +0.01  ):
                     wronginventory =  True

                if wronginventory:
                    print startinginventory
                    print lastInventory
                    raise NameError( "Inventory computation is wrong for product %s, real: %s computed: %s" %(p, lastInventory[p], startinginventory[p] ) )

            # Update the starting inventory, and the known Y values
            mip.UpdateStartingInventory(startinginventory)

            # Solve the MIP
            solution = mip.Solve()

            # Save the relevant values
            self.CopyFirstStageDecision( solution,  timetodecide )

            timetodecide += 1 + mip.Instance.NrTimeBucketWithoutUncertaintyBefore

            lastInventory =  [ solution.InventoryLevel[0][ mip.Instance.NrTimeBucketWithoutUncertaintyBefore+1][p]
                               + mip.Scenarios[0].Demands[mip.Instance.NrTimeBucketWithoutUncertaintyBefore+1][p]
                               + sum( solution.ProductionQuantity[0][mip.Instance.NrTimeBucketWithoutUncertaintyBefore+1][q] * self.GlobalInstance.Requirements[q][p]  for q in self.GlobalInstance.ProductSet)

                               for p in self.GlobalInstance.ProductSet]




        quantity = [[ round( self.Solution.ProductionQuantity[0][t][p], 2) for p in self.GlobalInstance.ProductSet] for t in self.GlobalInstance.TimeBucketSet]
        setups = [[ round(self.Solution.Production[0][t][p],0)  for p in self.GlobalInstance.ProductSet] for t in self.GlobalInstance.TimeBucketSet]

        print quantity
        print setups

        return setups, quantity

    #This function return the ending inventory at time t
    def GetEndingInventoryAt(self, t,  scenario):
        prevquanity = [ [ self.Solution.ProductionQuantity[0][t1][p1]
                          for p1 in self.GlobalInstance.ProductSet ]
                        for t1 in self.GlobalInstance.TimeBucketSet ]
        prevdemand = [ [ scenario.Demands[t1][p1]
                         for p1 in self.GlobalInstance.ProductSet ]
                       for t1 in self.GlobalInstance.TimeBucketSet ]
        projectedbackorder, Endininventory, currrentstocklevel = self.Solution.GetCurrentStatus(prevdemand,
                                                                                                prevquanity,
                                                                                                t)
        return Endininventory


    #This function save the frist stage decision in the solution of the MIP
    def CopyFirstStageDecision(self, solution, time ):

        if  solution.MRPInstance.NrTimeBucketWithoutUncertaintyBefore  > 0:
            periodstocopy =  range(solution.MRPInstance.NrTimeBucketWithoutUncertaintyBefore)  + [solution.MRPInstance.NrTimeBucketWithoutUncertaintyBefore ]
        else:
            periodstocopy = [time]
        for tau in periodstocopy:
            #Copy the Setup decision for the first day:
            for p in self.GlobalInstance.ProductSet:
                self.Solution.Production[0][tau][p] = solution.Production[0][tau - time ][p]

            #Copy the production quantity for the first day:
            for p in self.GlobalInstance.ProductSet:
                self.Solution.ProductionQuantity[0][tau][p] = solution.ProductionQuantity[0][tau - time][p]

