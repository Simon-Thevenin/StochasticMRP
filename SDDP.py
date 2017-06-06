from Constants import Constants
from MRPSolution import MRPSolution
from SDDPStage import SDDPStage
from ScenarioTree import ScenarioTree
import time
# This class contains the attributes and methodss allowing to define the SDDP algorithm.
class SDDP:

    #return the object stage associated with the decision stage given in paramter
    def GetSDDPStage(self, decisionstage):
        result = None
        if decisionstage >= 0:
            result = self.Stage[decisionstage]
        return result

    #Fill the links predecessor and next of each object stage
    def LinkStages(self):
        previousstage = None
        for stage in self.Stage:
            stage.PreviousSDDPStage = previousstage
            if not previousstage is None:
                previousstage.NextSDDPStage = stage
            previousstage = stage

    def __init__(self, instance):
        self.Instance = instance
        self.StagesSet = range( self.Instance.NrTimeBucket + 1 )
        self.CurrentIteration = 0
        self.CurrentLowerBound = 0
        self.CurrentUpperBound = Constants.Infinity
        self.StartOfAlsorithm = time.time()
        self.CurrentSetOfScenarios = []
        self.ScenarioNrSet = []
        self.CurrentScenarioSeed = 0
        self.Stage = [ SDDPStage( owner=self, decisionstage = t) for t in self.StagesSet ]
        self.LinkStages()

    #This function make the forward pass of SDDP
    def ForwardPass(self):
        if Constants.Debug:
            print "Start forward pass"
        for t in self.StagesSet:
            #Run the forward pass at each stage t
            self.Stage[t].RunForwardPassMIP()


    #This function make the backward pass of SDDP
    def BackwardPass(self):
        if Constants.Debug:
            print "Start Backward pass"

        for t in reversed( range( 1, len( self.StagesSet ) ) ):
            #Build or update the MIP of stage t
            self.Stage[t].GernerateCut();

            if t>= 1:
                # Re-run the MIP to take into account the just added cut
                self.Stage[t].Cplex.solve();


    #This function generates the scenarios for the current iteration of the algorithm
    def GenerateScenarios(self, nrscenario ):
        if Constants.Debug:
            print "Start generation of new scenarios"

        #Generate a scenario tree
        treestructure = [ 1, nrscenario ] + [1] * ( self.Instance.NrTimeBucket - 1 ) + [0]
        scenariotree = ScenarioTree( self.Instance, treestructure, self.CurrentScenarioSeed )

        #Get the set of scenarios
        self.CurrentSetOfScenarios = scenariotree.GetAllScenarios( computeindex= False )
        self.ScenarioNrSet = range( len(  self.CurrentSetOfScenarios ) )

        #Modify the number of scenario at each stage
        for stage in self.StagesSet:
            self.Stage[ stage ].SetNrScenario( len(  self.CurrentSetOfScenarios ) )

    #This function return the quanity of product to produce at time which has been decided at an earlier stage
    def GetQuantityFixedEarlier(self, product, time, scenario):
        result = 0
        return result

    # This function return the inventory quanity of product to produce at time which has been decided at an earlier stage
    def GetInventoryFixedEarlier(self, product, time, scenario):
        result = 0
        return result

        # This function return the backordered quantity of product which has been decided at an earlier stage
    def GetBackorderFixedEarlier(self, product, time, scenario):
        result = 0
        return result

    #This function return the value of the setup variable of product to produce at time which has been decided at an earlier stage
    def GetSetupFixedEarlier(self, product, time, scenario):
        result = 0
        return result

    #This function return the demand of product at time in scenario
    def GetDemandQuantity(self, product, time, scenario):
        result = 0
        return result

    #This funciton update the lower bound based on the last forward pass
    def UpdateLowerBound(self):
            self.CurrentLowerBound = 0

    #This funciton update the upper bound based on the last forward pass
    def UpdateUpperBound(self):
            self.CurrentUpperBound = Constants.Infinity

    #This function check if the stopping criterion of the algorithm is met
    def CheckStoppingCriterion(self):
        duration = time.time() - self.StartOfAlsorithm
        timalimiteached = ( duration > Constants.AlgorithmTimeLimit )
        optimalitygap = self.CurrentUpperBound - self.CurrentLowerBound
        optimalitygapreached = ( optimalitygap < Constants.AlgorithmOptimalityTolerence )
        iterationlimitreached = ( self.CurrentIteration > Constants.SDDPIterationLimit )
        result = optimalitygapreached or timalimiteached or iterationlimitreached
        if Constants.Debug:
            print "Iteration: %d, Duration: %d, LB: %d, UB: %d, Gap: %d " %(self.CurrentIteration, duration, self.CurrentLowerBound, self.CurrentUpperBound, optimalitygap)

        return result

    #This funciton compute the solution of the scenario given in argument (used after to have run the algorithm, and the cost to go approximation are built)
    def ComputeSolutionForScenario(self, scenario):
        solution = MRPSolution()
        return solution

    #This function runs the SDDP algorithm
    def Run(self):
        if Constants.Debug:
            print "Start the SDDP algorithm"

        self.StartOfAlsorithm = time.time()

        while not self.CheckStoppingCriterion():
            self.GenerateScenarios( 1 )
            self.ForwardPass()
            self.UpdateLowerBound()
            self.UpdateUpperBound()
            self.BackwardPass()
            self.CurrentIteration = self.CurrentIteration + 1

        if Constants.Debug:
            print "End of the SDDP algorithm"