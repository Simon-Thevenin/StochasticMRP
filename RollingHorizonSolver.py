from Constants import Constants
from ScenarioTree import ScenarioTree
import time
from MIPSolver import MIPSolver
from DecentralizedMRP import DecentralizedMRP
import copy

from MRPSolution import MRPSolution

class RollingHorizonSolver:

    def __init__(self, instance, treestructure, model, seed, scenariogenerationmethod ):
        self.GlobalInstance = instance
        self.WindowSize = self.GlobalInstance.MaxLeadTime + 1

        self.Seed = seed
        self.Treestructure =treestructure
        self.Model = model
        self.ScenarioGenerationResolvePolicy = scenariogenerationmethod

        self.SubInstance = self.CreateSubInstances()
        self.RollingHorizonMIPs =  self.DefineMIPsRollingHorizonSimulation()

    #This function define a set of MIP, each MIP correspond to a slice of the horizon
    def DefineMIPsRollingHorizonSimulation(self):
        result = []

        # For each subinstance, Create a tree, and generate a MIP
        for instance in self.SubInstance:
            instance.PrintInstance()
            print "To be implemented"

            scenariotree = ScenarioTree(instance, self.Treestructure, self.Seed,
                                        averagescenariotree=False,
                                        scenariogenerationmethod=self.ScenarioGenerationResolvePolicy,
                                        model=self.Model)

            mipsolver = MIPSolver(instance, self.Model, scenariotree,
                                  self.EVPI,
                                  implicitnonanticipativity=(not self.EVPI),
                                  evaluatesolution=True,
                                  usesafetystock=self.UseSafetyStock)

            result.append( mipsolver )

        return result


    # Create the set of subinstance to solve in a rolling horizon approach
    def CreateSubInstances( self ):
            """ :type result: [ {MRPInstance} ]"""
            nrshift = self.GlobalInstance.NrTimeBucket - self.WindowSize

            result = [None for i in range(nrshift)]

            startwindow = -1
            for i in range(nrshift):
                startwindow += 1
                endwindow = startwindow + self.WindowSize

                result[i] = copy.deepcopy(self.GlobalInstance)
                result[i].NrTimeBucket = self.WindowSize
                result[i].ForecastedAverageDemand = [self.GlobalInstance.ForecastedAverageDemand[startwindow + t] for t in
                                                     range(result[i].NrTimeBucket)]
                result[i].ForcastedStandardDeviation = [self.GlobalInstance.ForcastedStandardDeviation[startwindow + t] for t
                                                        in range(result[i].NrTimeBucket)]
                result[i].NrTimeBucketWithoutUncertaintyBefore = max(0,
                                                                     self.GlobalInstance.NrTimeBucketWithoutUncertaintyBefore - startwindow)
                result[i].ComputeIndices()

            return result

    #This function simulate the use of the stochastic optimization approach for given scenario
    def ApplyRollingHorizonSimulation(self, scenario):
        quantity = [[0 for p in self.GlobalInstance.ProductSet] for t in self.GlobalInstance.TimeBucketSet]
        setups = [[0 for p in self.GlobalInstance.ProductSet] for t in self.GlobalInstance.TimeBucketSet]

        timetodecide = -1
        for mip in self.RollingHorizonMIPs:

            if Constants.Debug:
                print " Solve instance with time window [ %r, %r]"%( timetodecide, timetodecide + self.WindowSize )

            timedemandknownuntil = timetodecide - 1

            startinginventory = self.GetEndingInventoryAt(t, quantity)

            # Update the starting inventory, and the known Y values
            mip.UpdateStartingInventory(startinginventory)

            # Solve the MIP
            solution = mip.Solve()

            # Save the relevant values
            self.CopyFirstStageDecision( solution, setups, quantity )

            timetodecide += 1

        return setups, quantity

    #This function return the ending inventory at time t
    def GetEndingInventoryAt(self, t, givenquantity):

        Endininventory = [ 0 for p in self.Instance.ProductSet ]

        print "to be implemented "

        return Endininventory

    #This method update the inital state of the instance according to the last solved in the rolling horizon.
    def UpdateStartingInventory( self, startinginventory):
        """
        @class instance: {MRPInstance}
        """
        print "to be implemented"




    def CopyFirstStageDecision(self, solution, setups, quantity, time ):

        #Copy the Setup decision for the first day:
        for p in self.Instance.ProductSet:
            setups[time][p] = solution.Production[0][time][p]

        #Copy the production quantity for the first day:
        for p in self.Instance.ProductSet:
            quantity[time][p] = solution.ProductionQuantity[0][time][p]

