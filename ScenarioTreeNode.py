import numpy as np
import math
#import matplotlib.pyplot as plt
from Constants import Constants
from Tool import Tool
from RQMCGenerator import RQMCGenerator
import scipy as scipy
#from matplotlib import pyplot as PLT

class ScenarioTreeNode:
    NrNode = 0

    # This function create a node for the instance and time given in argument
    # The node is associated to the time given in paramter.
    # nr demand is the number of demand scenario fo
    def __init__(self, owner=None, parent=None, firstbranchid=0, instance=None, mipsolver=None, time=-1, nrbranch=-1,
                 demands=None, proabibilty=-1, averagescenariotree=False):
        if owner is not None:
            owner.Nodes.append(self)
        self.Owner = owner;
        self.Parent = parent
        self.Instance = instance
        self.Branches = []
        # An identifier of the node
        self.NodeNumber = ScenarioTreeNode.NrNode;
        ScenarioTreeNode.NrNode = ScenarioTreeNode.NrNode + 1;
        self.FirstBranchID = firstbranchid
        if time > 1:
            self.FirstBranchID = self.Parent.FirstBranchID
        t = time + 1

        if instance is not None and t <= instance.NrTimeBucket:
            nrscneartoconsider = max(nrbranch, 1)
            probabilities = [(1.0 / nrscneartoconsider) for b in range(nrscneartoconsider)]
            if t == 0:
                nextdemands = []
                probabilities = [1]
            else:
                # if self.Owner.GenerateasYQfix:
                #    nextdemands = self.GetDemandAsYQFix( t-1, nrbranch )
                if (self.Owner.ScenarioGenerationMethod == Constants.RQMC and self.Owner.GenerateRQMCForYQFix and not time >= (
                    self.Instance.NrTimeBucket - self.Instance.NrTimeBucketWithoutUncertainty)) \
                    or ( self.Owner.ScenarioGenerationMethod == Constants.All and self.Owner.Model == Constants.ModelYQFix ):
                    nextdemands = self.GetDemandRQMCForYQFix(t - 1, nrbranch, firstbranchid)
                elif t <= self.Owner.FollowGivenUntil:
                    nextdemands = self.GetDemandToFollowFirstPeriods(t - 1)
                else:
                    nextdemands, probabilities = ScenarioTreeNode.CreateDemandNormalDistributiondemand(instance, t - 1,
                                                                                                       nrbranch,
                                                                                                       averagescenariotree,
                                                                                                       self.Owner.ScenarioGenerationMethod)

            usaverageforbranch = t >= (
            self.Instance.NrTimeBucket - self.Instance.NrTimeBucketWithoutUncertainty) or self.Owner.AverageScenarioTree

            nextfirstbranchid = [self.FirstBranchID for b in range(nrbranch)]
            if t == 1:
                nextfirstbranchid = [b for b in range(nrbranch)]

            self.Branches = [ScenarioTreeNode(owner=owner,
                                              parent=self,
                                              firstbranchid=nextfirstbranchid[b],
                                              instance=instance,
                                              time=t,
                                              nrbranch=owner.NrBranches[t + 1],
                                              demands=[nextdemands[p][b] for p in instance.ProductSet if t > 0],
                                              proabibilty=probabilities[b],
                                              averagescenariotree=usaverageforbranch) for b in range(nrbranch)]

        self.Time = time
        # The probability associated with the node
        self.Probability = proabibilty
        # The demand for each product associated with the node of the sceanrio
        self.Demand = demands
        # The attribute DemandsInParitalScenario contains all the demand since the beginning of the time horizon in the partial scenario
        self.DemandsInScenario = []  # will be built later
        # The probability of the partial scenario ( take into account the paroability if parents )
        self.ProbabilityOfScenario = -1
        # The attribute below contains the index of the CPLEX variables (quanity, production, invenotry) associated with the node for each product at the relevant time.
        self.QuanitityVariable = []  # will be built later
        self.ProductionVariable = []  # will be built later
        self.InventoryVariable = []  # will be built later
        self.BackOrderVariable = []  # will be built later
        # The attributes below contain the list of variable for all time period of the scenario
        self.QuanitityVariableOfScenario = []  # will be built later
        self.ProductionVariableOfScenario = []  # will be built later
        self.InventoryVariableOfScenario = []  # will be built later
        self.BackOrderVariableOfScenario = []  # will be built later
        self.NodesOfScenario = []  # will be built later
        self.QuantityToOrderNextTime = []  # After solving the MILP, the attribut contains the quantity to order at the node
        self.InventoryLevelNextTime = []  # After solving the MILP, the attribut contains the inventory level at the node
        self.BackOrderLevelNextTime = []  # After solving the MILP, the attribut contains the back order level at the node
        self.InventoryLevelTime = []  # After solving the MILP, the attribut contains the inventory level at the node
        self.BackOrderLevelTime = []  # After solving the MILP, the attribut contains the back order level at the node

        self.Scenario = None

        self.OneOfScenario = None
    #This function is used when the demand is gereqated using RQMC for YQFix
    #Return the demands  at time at position nrdemand in array DemandYQFixRQMC
    def GetDemandRQMCForYQFix( self, time, nrdemand, firstbranchid ):
            demandvector = [ [ self.Owner.DemandYQFixRQMC[firstbranchid + i][time][p]
                                 for i in range(nrdemand)]
                                      for p in self.Instance.ProductSet]
            #print "firstbranchid + i][time][p] [%r][%r][%r] " %( firstbranchid , time, p )
            # for p in self.Instance.ProductSet:
            #
            #         pts = [self.Owner.DemandYQFixRQMC[s][time][p] for s in range(nrdemand)]
            #         print " CONSTRUCTING THE TREE The transformed point at dim %d at time %d : %r  " % (p, time, pts)
            #         with open('Histpoints%dt%d.csv' % (p, time), 'w+') as f:
            #             # v_hist = np.ravel(v)  # 'flatten' v
            #             fig = PLT.figure()
            #             ax1 = fig.add_subplot(111)
            #
            #             n, bins, patches = ax1.hist(pts, bins=100, normed=1, facecolor='green')
            #             PLT.show()
            return demandvector

    #This function is used when the demand to use are the one generated for YQFix, which are stored in an array DemandToFollow
    #Return the demand of time at position nrdemand in array DemandTo follow
    def GetDemandAsYQFix( self, time, nrdemand ):
            demandvector = [ [ self.Owner.DemandToFollow[i][time][p]
                                 for i in range(nrdemand)]
                                      for p in self.Instance.ProductSet]
            return demandvector

    #This function is used when the demand of the first periods are given, and only the end of the scenario tree has to be generated.
    #The demand of the first period are stored in a table GivenFirstPeriod.
    #This function returns the given demand at time
    def GetDemandToFollowFirstPeriods(self, time):
             demandvector = [[self.Owner.GivenFirstPeriod[time][p]
                                 for i in [0]]
                                for p in self.Instance.ProductSet]
             return demandvector

    #This method generate a set of points in [0,1] using RQMC. The points are generated with the library given on the website of P. Lecuyer


    # Apply the inverse of  the given distribution for each point (generated in [0,1]) in the set.
    @staticmethod
    def TransformInverse( points, nrpoints, dimensionpoint, distribution, average, std = 0 ):

        if distribution == Constants.Normal or distribution == Constants.NonStationary:
            result = [[ float( max( np.floor( scipy.stats.norm.ppf( points[i][p], average[p], std[p]) ), 0.0) ) if average[p] > 0 else 0.0 for i in range(nrpoints) ] for p in range(dimensionpoint) ]

        if distribution == Constants.Binomial:
            n = 7
            prob = 0.5
            result = [[scipy.stats.binom.ppf(points[i][p], n, prob) for i in range(nrpoints)] for p in range(dimensionpoint)]


        if distribution == Constants.SlowMoving:
            result = [[scipy.stats.poisson.ppf(points[i][p], average[p]) for i in range(nrpoints)] for p in range(dimensionpoint)]

        if distribution == Constants.Lumpy:
            result = [[scipy.stats.poisson.ppf( ( points[i][p] - 0.8 ) / 0.2, (average[p]) / 0.2 ) +1 if points[i][p] > 0.8 else 0 for i in range(nrpoints)] for p in range(dimensionpoint)]

        if distribution == Constants.Uniform:
            result = [[0.0 if points[i][p] < 0.5 else 1.0
                       for i in range(nrpoints)] for p in range(dimensionpoint)]

        return result

    #This method generate a set of nrpoint according to the method and given distribution.
    @staticmethod
    def GeneratePoints( method, nrpoints, dimensionpoint, distribution, average, std = [] ):
        points = []
        proability = [ 1.0 / max( nrpoints, 1) for pt in range( max( nrpoints, 1) ) ]
        #Generate the points using MonteCarlo
        if method == Constants.MonteCarlo:
            #For each considered distribution create an array with nrpoints random points for each distribution
            if distribution == Constants.SlowMoving:
                points = [ [ 0  for pt in range(nrpoints) ] for p in range(dimensionpoint) ]
                for p in range(dimensionpoint):#instance.ProductWithExternalDemand:
                    for i in range(nrpoints):
                        if average[p] > 0:
                            points[p][i] = np.round(  np.random.poisson(average[p], 1)[0], 0 );

            elif distribution == Constants.Binomial:
                n = 7
                prob = 0.5
                points = [[0 for pt in range(nrpoints)] for p in range(dimensionpoint)]
                for p in range(dimensionpoint):  # instance.ProductWithExternalDemand:
                    for i in range(nrpoints):
                        if average[p] > 0:
                            points[p][i] = np.round(np.random.binomial(n, prob,1)[0], 0);


            elif distribution == Constants.Lumpy:
                points = [ [ 0  for pt in range(nrpoints)] for p in range(dimensionpoint) ]
                for p in range(dimensionpoint):
                    for i in range(nrpoints):
                        randompoint = scipy.random.uniform(0, 1)
                        if randompoint < 0.8 or average[p] == 0:
                            points[p][i] = 0;
                        else:
                            points[p][i] = scipy.stats.poisson.ppf( (randompoint - 0.8 ) / 0.2, (average[p]) / 0.2 ) +1
            elif distribution == Constants.Uniform:
                points = [[0.0 if(  average[p] <= 0 or np.random.uniform(0,1) < 0.5 ) else 1.0
                               for i in range(nrpoints)] for p in range(dimensionpoint)]
            else:
                points = [ np.floor( np.random.normal(average[p], std[p], nrpoints).clip(min=0.0) ).tolist()
                                     if std[p] > 0 else [float(average[p])] * nrpoints
                                     for p in range( dimensionpoint )]
            #In monte Carlo, each point as the same proability


        # Generate the points using RQMC
        if method == Constants.RQMC:
            points = [[0.0 for pt in range(nrpoints)] for p in range(dimensionpoint)]
            nrnonzero = sum( 1  for p in range( dimensionpoint ) if average[p] > 0 )
            idnonzero = [  p  for p in range( dimensionpoint ) if average[p] > 0 ]
            avg = [ average[prod] for prod in idnonzero ]
            stddev = [std[prod] for prod in idnonzero ]
            pointsin01 = RQMCGenerator.RQMC01(nrpoints, nrnonzero)

            rqmcpoints = ScenarioTreeNode.TransformInverse( pointsin01, nrpoints, nrnonzero, distribution, avg, stddev )



            for p in range( nrnonzero ):  # instance.ProductWithExternalDemand:
                    for i in range(nrpoints):
                        points[idnonzero[p]] [i]= float ( np.round( rqmcpoints[ p ][i], 0 ) )

        if method == "all" and distribution <> Constants.Binomial:
            points = [[0.0 for pt in range(nrpoints)] for p in range(dimensionpoint)]
            nrnonzero = sum(1 for p in range(dimensionpoint) if average[p] > 0)
            idnonzero = [p for p in range(dimensionpoint) if average[p] > 0]

            nonzeropoints = [[0, 0, 0, 0, 1, 1, 1, 1], [0, 0, 1, 1, 0, 0, 1, 1], [0, 1, 0, 1, 0, 1, 0, 1]]
            for p in range(nrnonzero):  # instance.ProductWithExternalDemand:
                for i in range(nrpoints):
                    points[idnonzero[p]][i] = nonzeropoints[p][i]

        if method == "all" and distribution == Constants.Binomial:
            points = [[0.0 for pt in range(nrpoints)] for p in range(dimensionpoint)]
            nrnonzero = sum(1 for p in range(dimensionpoint) if average[p] > 0)
            idnonzero = [p for p in range(dimensionpoint) if average[p] > 0]
            if nrnonzero > 1 or nrpoints <> 8:
                raise NameError( "binomial implemented only for dimension 1 and 8 points not %r -%r" %(nrnonzero, nrpoints) )

            nonzeropoints = [range(0,8 )]
            n = 7
            prob = 0.5
            proability = [ scipy.stats.binom.pmf(p, n, prob) for p in nonzeropoints[0]]
            for p in range(nrnonzero):  # instance.ProductWithExternalDemand:
                for i in range(nrpoints):
                    points[idnonzero[p]][i] = nonzeropoints[p][i]

        return points, proability

#Create the demand in a node following a normal distribution
    @staticmethod
    def CreateDemandNormalDistributiondemand( instance, time, nrdemand, average = False, scenariogenerationmethod = Constants.MonteCarlo ):
        demandvector = [  [  float(instance.ForecastedAverageDemand[time][p])
                                 for i in range( nrdemand ) ]  for p in instance.ProductSet]

        probability =   [  float( 1/ max( nrdemand, 1))  for i in range( max( nrdemand, 1)  ) ]

        if not average:
            points, probability = ScenarioTreeNode.GeneratePoints( method= scenariogenerationmethod,
                                                                   nrpoints=nrdemand,
                                                                   dimensionpoint = instance.NrProduct ,
                                                                   distribution = instance.Distribution,
                                                                   average = [ instance.ForecastedAverageDemand[time][p] for p in instance.ProductSet ],
                                                                   std = [ instance.ForcastedStandardDeviation[time][p] for p in instance.ProductSet ]  )

            demandvector = points

        return demandvector, probability


    #This function compute the indices of the variables associated wiht each node of the tree
    def ComputeVariableIndex( self ):

        if self.NodeNumber == 0:
            self.ProductionVariable = [(self.Owner.Owner.StartProductionVariableWithoutNonAnticipativity
                                        + self.Instance.NrProduct * (t) + p)
                                       for p in self.Instance.ProductSet for t in self.Instance.TimeBucketSet]

        if self.Time < self.Instance.NrTimeBucket: #Do not associate Production or quantity variable to the last nodes
            self.QuanitityVariable = [ ( self.Owner.Owner.StartQuantityVariableWithoutNonAnticipativity +
                                         self.Instance.NrProduct * ( self.NodeNumber -1 )  + p )
                                         for p in self.Instance.ProductSet ]
            #self.ProductionVariable = [(self.Owner.Owner.StartProductionVariableWithoutNonAnticipativity
            #                            + self.Instance.NrProduct * (self.NodeNumber - 1) + p)
            #                           for p in self.Instance.ProductSet ]

        if self.Time > 0 : #use ( self.NodeNumber -2 ) because thee is no inventory variable for the first node and for the root node
            self.InventoryVariable = [ ( self.Owner.Owner.StartInventoryVariableWithoutNonAnticipativity
                                         + self.Instance.NrProduct  * ( self.NodeNumber -2 )  + p )
                                       for p in self.Instance.ProductSet ]
            self.BackOrderVariable = [ ( self.Owner.Owner.StartBackorderVariableWithoutNonAnticipativity
                                         + len( self.Instance.ProductWithExternalDemand )  * ( self.NodeNumber -2 )
                                         + self.Instance.ProductWithExternalDemandIndex[ p ] )
                                         for p in self.Instance.ProductWithExternalDemand ]

    #This function display the tree
    def Display( self ):
        print "Demand of node( %d ): %r" %( self.NodeNumber, self.Demand )
        print "Probability of branch ( %d ): %r" %( self.NodeNumber, self.Probability )
        print "QuanitityVariable of node( %d ): %r" %( self.NodeNumber, self.QuanitityVariable )
        print "ProductionVariable of node( %d ): %r" %( self.NodeNumber, self.ProductionVariable )
        print "InventoryVariable of node( %d ): %r" %( self.NodeNumber, self.InventoryVariable )
        print "BackOrderVariable of node( %d ): %r" %( self.NodeNumber, self.BackOrderVariable )
        for b in self.Branches:
            b.Display()

    # This function aggregate the data of a node: It will contain the list of demand, and variable in the partial scenario
    def CreateAllScenarioFromNode( self ):
		# copy the demand and probability of the parent:
        if self.Parent is not None :
            self.DemandsInScenario = self.Parent.DemandsInScenario[ : ]
            self.ProbabilityOfScenario = self.Parent.ProbabilityOfScenario
            self.QuanitityVariableOfScenario = self.Parent.QuanitityVariableOfScenario[ : ]
            self.ProductionVariableOfScenario = self.Parent.ProductionVariableOfScenario[ : ]
            self.InventoryVariableOfScenario = self.Parent.InventoryVariableOfScenario[ : ]
            self.BackOrderVariableOfScenario = self.Parent.BackOrderVariableOfScenario[ : ]
            self.NodesOfScenario = self.Parent.NodesOfScenario[:]

            # Add the demand of the the current node and update the probability
            Tool.AppendIfNotEmpty( self.DemandsInScenario, self.Demand )
            Tool.AppendIfNotEmpty( self.QuanitityVariableOfScenario, self.QuanitityVariable )
            Tool.AppendIfNotEmpty( self.ProductionVariableOfScenario, self.ProductionVariable )
            Tool.AppendIfNotEmpty( self.InventoryVariableOfScenario, self.InventoryVariable )
            Tool.AppendIfNotEmpty( self.BackOrderVariableOfScenario, self.BackOrderVariable )
            self.NodesOfScenario.append(self)
            #Compute the probability of the scenario
            self.ProbabilityOfScenario = self.ProbabilityOfScenario * self.Probability
        else :
            self.ProbabilityOfScenario = 1

        # If the node is a not leave, run the method for the child
        for b in self.Branches:
            b.CreateAllScenarioFromNode( );

    def GetDistanceBasedOnStatus(self, inventory, backorder ):
        distance = 0
        if self.Time >0:
            for p in self.Instance.ProductSet:

                # If the distance is smaller than the best, the scenariio becomes the closest
                nodeinventory = 0
                realinventory =  0
                if self.Instance.HasExternalDemand[p]:
                    pindex =self.Instance.ProductWithExternalDemandIndex[p]
                    nodeinventory =   self.InventoryLevelTime[p] - self.BackOrderLevelTime[pindex]
                    realinventory = inventory[p] - backorder[pindex]
                else:
                    nodeinventory = self.Parent.InventoryLevelNextTime[p]
                    realinventory = inventory[p]

                nodeorderdeliverynext = self
                for i in range(self.Instance.Leadtimes[p] ):
                    if  nodeorderdeliverynext.Time >= 0:
                        nodeorderdeliverynext = nodeorderdeliverynext.Parent
                    else:
                        nodeorderdeliverynext = None

                if not nodeorderdeliverynext is None and len(nodeorderdeliverynext.QuantityToOrderNextTime ) >0:
                    nodeinventory = nodeinventory+nodeorderdeliverynext.QuantityToOrderNextTime[p]

                distance = distance + math.pow( nodeinventory - realinventory, 2)

        if Constants.Debug:
            print "for node %r distance based on status %r"%(self.NodeNumber, distance)
        return math.sqrt( distance )


    def GetDistanceBasedOnDemand(self, demands):
        distance = 0
        if self.Time > 0:
            for p in self.Instance.ProductSet:
                # If the distance is smaller than the best, the scenariio becomes the closest
                distance = distance + math.pow(self.Demand[p] - demands[p], 2)

        if Constants.Debug:
            print "for node %r distance based on demand %r" % (self.NodeNumber, distance)
        return math.sqrt( distance )

    #Return true if the quantity proposed in the node are above the current level of inventory
    def IsQuantityFeasible(self, levelofinventory):
        sumvector = [sum( self.QuantityToOrderNextTime[p] * self.Instance.Requirements[p][q]  for p in self.Instance.ProductSet) for q in self.Instance.ProductSet]

        result = all( levelofinventory[q] + 0.1  >= sumvector[q] for q in self.Instance.ProductSet )

        differencevector = [ sumvector[q] - levelofinventory[q]  for q in self.Instance.ProductSet]

        if Constants.Debug:
            print "for node %r feasible: %r - SumVect: %r" % (self.NodeNumber, result, differencevector)

        return result

    #return the quantity to which the stock is brought
    def GetS(self, p):

        result = 0
        node = self
        # plus initial inventory
        result += self.Instance.StartingInventories[p]

        while node is not None and node.Time >= 0:

            result += node.QuantityToOrderNextTime[p]
              # minus internal  demand
            result -= sum( node.QuantityToOrderNextTime[q] * self.Instance.Requirements[q][p] for q in self.Instance.ProductSet )
            #minus external demand
            if node.Time > 0:
                result -= node.Demand[p]
            node = node.Parent

        if node.Time >= 0:
            print "ATTTENTION REMOVE tAHT if IT DOESNOT WORK %r %r" % ( node.InventoryLevelTime, self.Instance.TotalRequirement)

            result = node.QuantityToOrderNextTime[p]

            result += sum( node.InventoryLevelTime[q] * self.Instance.TotalRequirement[q][p]
                           for q in self.Instance.ProductSet if self.Instance.HasExternalDemand[q]) #self.Instance.StartingInventories[p]

        return result