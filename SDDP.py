from Constants import Constants
from MRPSolution import MRPSolution
from SDDPStage import SDDPStage
import time
# This class contains the attributes and methodss allowing to define the SDDP algorithm.
class SDDP:


    def GetSDDPStage(self, time):
        result = None
        if time >= 0:
            result = self.Stage[time]
        return result

    def LinkStages(self):
        previousstage = None
        for stage in self.Stage:
            stage.PreviousSDDPStage = previousstage
            if not previousstage is None:
                previousstage.NextSDDPStage = stage
            previousstage = stage

    def __init__(self, instance):
        self.Instance = instance
        self.Stage = [ SDDPStage( owner=self, decisionstage = t) for t in self.Instance.TimeBucketSet ]
        self.LinkStages()
        self.CurrentIteration = 0
        self.CurrentLowerBound = 0
        self.CurrentUpperBound = Constants.Infinity
        self.StartOfAlsorithm = time.time()

    #This function make the forward pass of SDDP
    def ForwardPass(self):
        if Constants.Debug:
            print "Start forward pass"
        for t in self.Instance.TimeBucketSet:
            #Build or update the MIP of stage t
            self.Stage[t].BuildMIP();
            #Run The MIP
            self.Stage[t].Cplex.solve();

    #This function make the backward pass of SDDP
    def BackwardPass(self):
        if Constants.Debug:
            print "Start Backward pass"

        for t in reversed( range( 1, self.Instance.NrTimeBucket) ):
            #Build or update the MIP of stage t
            self.Stage[t].GernerateCut();

            if t>= 1:
                # Re-run the MIP to take into account the just added cut
                self.Stage[t].Cplex.solve();


    #This function generates the scenarios for the current iteration of the algorithm
    def GenerateScenarios(self):
        if Constants.Debug:
            print "Start generation of new scenarios"

    #This function return the quanity of product to produce at time which has been decided at an earlier stage
    def GetQuantityFixedEarlier(self, product, time, scenario):
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
        optimalitygapreached = ( ( self.CurrentUpperBound - self.CurrentLowerBound ) < Constants.AlgorithmOptimalityTolerence )
        result = optimalitygapreached or timalimiteached
        if Constants.Debug:
            print "Iteration: %d, Duration: %d, LB: %d, UB: %d " %(self.CurrentIteration, duration, self.CurrentLowerBound, self.CurrentUpperBound)

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
            self.GenerateScenarios()
            self.ForwardPass()
            self.UpdateLowerBound()
            self.UpdateUpperBound()
            self.BackwardPass()
            self.CurrentIteration = self.CurrentIteration + 1

        if Constants.Debug:
            print "End of the SDDP algorithm"