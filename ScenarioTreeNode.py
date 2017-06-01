import numpy as np
import matplotlib.pyplot as plt
from Constants import Constants
from Tool import Tool
import scipy as scipy

class ScenarioTreeNode:
    NrNode = 0

    #This function is used when the demand is gereqated using RQMC for YQFix
    #Return the demands  at time at position nrdemand in array DemandYQFixRQMC
    def GetDemandRQMCForYQFix( self, time, nrdemand, firstbranchid ):
            demandvector = [ [ self.Owner.DemandYQFixRQMC[firstbranchid + i][time][p]
                                 for i in range(nrdemand)]
                                      for p in self.Instance.ProductSet]
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
    @staticmethod
    def RQMC01( nrpoints, dimensionpoint ):
        randomizer = np.random.uniform( 0.0 , 10.0)
        result=[]
        #For dimension 3 only, and nr point in 2, 4, 8, 16, 32
        n = -1
        a = []
        #reurn the array given by the library
        if dimensionpoint == 1 and nrpoints == 1: n = 1; a = [1]
        if dimensionpoint == 1 and nrpoints == 2: n = 2; a = [1]
        if dimensionpoint == 1 and nrpoints == 4: n = 4; a = [1]
        if dimensionpoint == 1 and nrpoints == 8: n = 8; a = [1]
        if dimensionpoint == 1 and nrpoints == 16: n = 16; a = [1]
        if dimensionpoint == 1 and nrpoints == 32: n = 32; a = [1]
        if dimensionpoint == 1 and nrpoints == 50: n = 50; a = [1]
        if dimensionpoint == 1 and nrpoints == 100: n = 100; a = [1]
        if dimensionpoint == 3 and nrpoints == 1: n = 1; a = [1, 0, 0]
        if dimensionpoint == 3 and nrpoints == 2: n = 2; a = [1, 1, 1]
        if dimensionpoint == 3 and nrpoints == 4: n = 4; a = [1, 1, 1]
        if dimensionpoint == 3 and nrpoints == 8: n = 8; a = [1, 3, 1]
        if dimensionpoint == 3 and nrpoints == 16: n = 16; a = [1, 7, 5]
        if dimensionpoint == 3 and nrpoints == 32: n = 32; a = [1, 7, 5]
        if dimensionpoint == 3 and nrpoints == 50: n = 50; a = [1, 21, 19]
        if dimensionpoint == 3 and nrpoints == 100: n = 100; a = [1, 41, 27]
        if dimensionpoint == 9 and nrpoints == 1: n = 1; a = [1, 0, 0, 0, 0, 0, 0, 0, 0]
        if dimensionpoint == 9 and nrpoints == 2: n = 2; a = [1, 1, 1, 1, 1, 1, 1, 1, 1]
        if dimensionpoint == 9 and nrpoints == 4: n = 4; a = [1, 1, 1, 1, 1, 1, 1, 1, 1]
        if dimensionpoint == 9 and nrpoints == 8: n = 8; a = [1, 3, 1, 3, 1, 3, 1, 3, 1]
        if dimensionpoint == 9 and nrpoints == 16: n = 16; a = [1, 7, 5, 3, 5, 3, 7, 1, 1]
        if dimensionpoint == 9 and nrpoints == 32: n = 32; a = [1, 7, 5, 15, 9, 3, 11, 13, 1]
        if dimensionpoint == 9 and nrpoints == 50: n = 50; a = [1, 21, 19, 9, 11, 23, 17, 13, 7]
        if dimensionpoint == 9 and nrpoints == 100: n = 100; a = [1, 41, 27, 17, 11, 31, 13, 21, 43]
        result = [[ ( (i * aj % n) / float(n) + randomizer ) % 1 for aj in a] for i in range(n)]
        #result = [[ 0.1 for aj in a] for i in range(n)]

        return result

    # Apply the inverse of  the given distribution for each point (generated in [0,1]) in the set.
    @staticmethod
    def TransformInverse( points, nrpoints, dimensionpoint, distribution, average, std = 0 ):

        if distribution == Constants.Normal:
            result = [[ max( scipy.stats.norm.ppf( points[i][p], average[p], std[p]), 0.0) for i in range(nrpoints) ] for p in range(dimensionpoint) ]

        if distribution == Constants.SlowMoving:
            result = [[scipy.stats.poisson.ppf(points[i][p], average[p]) for i in range(nrpoints)] for p in range(dimensionpoint)]

        if distribution == Constants.Lumpy:
            result = [[scipy.stats.poisson.ppf( points[i][p] / 0.2, (average[p]) / 0.2 ) +1 if points[i][p] < 0.2 else 0 for i in range(nrpoints)] for p in range(dimensionpoint)]

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
            elif distribution == Constants.Lumpy:
                points = [ [ 0  for pt in range(nrpoints)] for p in range(dimensionpoint) ]
                for p in range(dimensionpoint):
                    for i in range(nrpoints):
                        if np.random.random_sample() >= 0.2 or average[p] == 0:
                            points[p][i] = 0;
                        else:
                            points[p][i] = np.round( np.random.poisson((average[p]) / 0.2, 1)[0] + 1, 0 );
            else:
                points = [np.round(
                    np.random.normal(average[p], std[p], nrpoints).clip(min=0.0),
                    0).tolist()
                                if std[p] > 0 else [float(average[p])] * nrpoints
                                for p in range( dimensionpoint )]
            #In monte Carlo, each point as the sam proability


        # Generate the points using RQMC
        if method == Constants.RQMC:
            points = [[0.0 for pt in range(nrpoints)] for p in range(dimensionpoint)]
            nrnonzero = sum( 1  for p in range( dimensionpoint ) if average[p] > 0 )
            idnonzero = [  p  for p in range( dimensionpoint ) if average[p] > 0 ]
            avg = [ average[prod] for prod in idnonzero ]
            stddev = [std[prod] for prod in idnonzero ]
            pointsin01 = ScenarioTreeNode.RQMC01(nrpoints, nrnonzero)
            rqmcpoints = ScenarioTreeNode.TransformInverse( pointsin01, nrpoints, nrnonzero, distribution, avg, stddev )

            for p in range( nrnonzero ):  # instance.ProductWithExternalDemand:
                    for i in range(nrpoints):
                        points[idnonzero[p]] [i]= float ( np.round( rqmcpoints[ p ][i], 0 ) )

        return points, proability

#Create the demand in a node following a normal distribution
    @staticmethod
    def CreateDemandNormalDistributiondemand( instance, nrdemand, average = False, scenariogenerationmethod = Constants.MonteCarlo ):
        demandvector = [  [  float(instance.AverageDemand[p])
                                 for i in range( nrdemand ) ]  for p in instance.ProductSet]

        probability =   [  float( 1/ max( nrdemand, 1))  for i in range( max( nrdemand, 1)  ) ]

        if not average:
            points, probability = ScenarioTreeNode.GeneratePoints( method= scenariogenerationmethod,
                                                                   nrpoints=nrdemand,
                                                                   dimensionpoint = instance.NrProduct ,
                                                                   distribution = instance.Distribution,
                                                                   average = [ instance.AverageDemand[p] for p in instance.ProductSet ],
                                                                   std = [ instance.StandardDevDemands[p] for p in instance.ProductSet ]  )

            demandvector = points

        return demandvector, probability

    # This function create a node for the instance and time given in argument
    #The node is associated to the time given in paramter.
    #nr demand is the number of demand scenario fo
    def __init__( self, owner = None, parent =None, firstbranchid = -1, instance = None, mipsolver = None, time = -1,  nrbranch = -1, demands = None, proabibilty = -1, averagescenariotree = False,  slowmoving = False  ):
        if owner is not None:
            owner.Nodes.append( self )
        self.Owner = owner;
        self.Parent = parent
        self.Instance = instance
        self.Branches = []
        # An identifier of the node
        self.NodeNumber = ScenarioTreeNode.NrNode;
        ScenarioTreeNode.NrNode  = ScenarioTreeNode.NrNode  + 1;
        self.FirstBranchID = firstbranchid
        if time > 1 :
            self.FirstBranchID = self.Parent.FirstBranchID
        t= time + 1

        if  instance is not None and  t <= instance.NrTimeBucket:
            nrscneartoconsider = max( nrbranch, 1)
            probabilities =  [  ( 1.0 / nrscneartoconsider )  for b in range( nrscneartoconsider )  ]
            if t == 0:
                nextdemands = []
                probabilities = [1]
            else:
                if self.Owner.GenerateasYQfix:
                    nextdemands = self.GetDemandAsYQFix( t-1, nrbranch )
                elif self.Owner.ScenarioGenerationMethod == Constants.RQMC and self.Owner.GenerateRQMCForYQFix and not time >= (self.Instance.NrTimeBucket - self.Instance.NrTimeBucketWithoutUncertainty ):
                    nextdemands = self.GetDemandRQMCForYQFix( t-1, nrbranch, firstbranchid )
                elif t <= self.Owner.FollowGivenUntil:
                    nextdemands = self.GetDemandToFollowFirstPeriods( t-1 )
                else:
                    nextdemands, probabilities = ScenarioTreeNode.CreateDemandNormalDistributiondemand(instance, nrbranch, averagescenariotree, self.Owner.ScenarioGenerationMethod )

            usaverageforbranch = t >= (self.Instance.NrTimeBucket - self.Instance.NrTimeBucketWithoutUncertainty ) or  self.Owner.AverageScenarioTree

            self.Branches = [ ScenarioTreeNode( owner = owner,
                                                parent = self,
                                                firstbranchid =  b ,
                                                instance = instance,
                                                time = t,
                                                nrbranch = owner.NrBranches[ t +1 ],
                                                demands = [ nextdemands[ p ][ b ]  for p in instance.ProductSet if t > 0 ],
                                                proabibilty =   probabilities[ b ]  ,
                                                averagescenariotree = usaverageforbranch,
                                                slowmoving = slowmoving ) for b in range( nrbranch ) ]

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
        self.QuanitityVariable = [] # will be built later
        self.ProductionVariable = [] # will be built later
        self.InventoryVariable = []# will be built later
        self.BackOrderVariable = []# will be built later
        #The attributes below contain the list of variable for all time period of the scenario
        self.QuanitityVariableOfScenario = [ ] # will be built later
        self.ProductionVariableOfScenario = [] # will be built later
        self.InventoryVariableOfScenario = []# will be built later
        self.BackOrderVariableOfScenario = []# will be built later
        self.QuantityToOrder = [] #After solving the MILP, the attribut contains the quantity to order at the node


    #This function compute the indices of the variables associated wiht each node of the tree
    def ComputeVariableIndex( self ):
        if self.Time < self.Instance.NrTimeBucket: #Do not associate Production or quantity variable to the last nodes
            self.QuanitityVariable = [ ( self.Owner.Owner.StartQuantityVariableWithoutNonAnticipativity +
                                         self.Instance.NrProduct * ( self.NodeNumber -1 )  + p )
                                         for p in self.Instance.ProductSet ]
            self.ProductionVariable = [ ( self.Owner.Owner.StartProductionVariableWithoutNonAnticipativity
                                          + self.Instance.NrProduct * ( self.NodeNumber -1 )   + p )
                                          for p in self.Instance.ProductSet ]

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

            # Add the demand of the the current node and update the probability
            Tool.AppendIfNotEmpty( self.DemandsInScenario, self.Demand )
            Tool.AppendIfNotEmpty( self.QuanitityVariableOfScenario, self.QuanitityVariable )
            Tool.AppendIfNotEmpty( self.ProductionVariableOfScenario, self.ProductionVariable )
            Tool.AppendIfNotEmpty( self.InventoryVariableOfScenario, self.InventoryVariable )
            Tool.AppendIfNotEmpty( self.BackOrderVariableOfScenario, self.BackOrderVariable )
            #Compute the probability of the scenario
            self.ProbabilityOfScenario = self.ProbabilityOfScenario * self.Probability
        else :
            self.ProbabilityOfScenario = 1

        # If the node is a not leave, run the method for the child
        for b in self.Branches:
            b.CreateAllScenarioFromNode( );