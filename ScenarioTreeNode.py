import numpy as np

import matplotlib.pyplot as plt
#from MRPInstance import MRPInstance


class ScenarioTreeNode:
    NrNode = 0

    #Create the demand in a node following a normal distribution
    def CreateDemandNormalDistributiondemand( self, instance, nrdemand ):
        demandvector = [  np.random.normal( instance.AverageDemand[p], instance.StandardDevDemands[p], nrdemand ).clip(min=0).tolist()
                            if instance.StandardDevDemands[p] > 0 else [instance.AverageDemand[p] ] * nrdemand
                            for p in instance.ProductSet ]
        return demandvector

    # This function create a node for the instance and time given in argument
    #The node is associated to the time given in paramter.
    #nr demand is the number of demand scenario fo
    def __init__( self, owner = None, parent =None, instance = None, time = -1,  nrbranch = -1, demands = None, proabibilty = -1 ):
        owner.Nodes.append( self )
        self.Owner = owner;
        self.Parent = parent
        self.Instance = instance
        self.Branches = []
        t= time + 1
        if  instance is not None and  t < instance.NrTimeBucket:
            nextdemands = self.CreateDemandNormalDistributiondemand( instance, nrbranch )
            self.Branches = [ ScenarioTreeNode( owner = owner,
                                                parent = self,
                                                instance = instance,
                                                time = t,
                                                nrbranch = owner.NrBranches[ t +1 ],
                                                demands = [ nextdemands[ p ][ b ] for p in instance.ProductSet ],
                                                proabibilty = 1.0 / nrbranch ) for b in range( nrbranch ) ]

        self.Time = time
        # The probability associated with the node
        self.Probability = proabibilty
        # The demand for each product associated with the node of the sceanrio
        self.Demand = demands
        # An identifier of the node
        self.NodeNumber = ScenarioTreeNode.NrNode;
        ScenarioTreeNode.NrNode  = ScenarioTreeNode.NrNode  + 1;
        # The attribute DemandsInParitalScenario contains all the demand since the beginning of the time horizon in the partial scenario
        self.DemandsInScenario = []  # will be built later
        # The probability of the partial scenario ( take into account the paroability if parents )
        self.ProbabilityOfScenario = -1
        # The attribute below contains the index of the CPLEX variables (quanity, production, invenotry) associated with the node for each product at the relevant time.
        self.QuanitityVariable = [ ] # will be built later
        self.ProductionVariable = [] # will be built later
        self.InventoryVariable = []# will be built later
        self.BackOrderVariable = []# will be built later
        #The attributes below contain the list of variable for all time period of the scenario
        self.QuanitityVariableOfScenario = [ ] # will be built later
        self.ProductionVariableOfScenario = [] # will be built later
        self.InventoryVariableOfScenario = []# will be built later
        self.BackOrderVariableOfScenario = []# will be built later

    #This function compute the indices of the variables associated wiht each node of the tree
    def ComputeVariableIndex( self ):
        self.QuanitityVariable = [ ( self.Instance.StartQuantityVariableWithoutNonAnticipativity + self.Instance.NrProduct * ( self.NodeNumber -1 )  + p )  for p in self.Instance.ProductSet ]
        self.ProductionVariable = [ ( self.Instance.StartProdustionVariableWithoutNonAnticipativity + self.Instance.NrProduct * ( self.NodeNumber -1 )   + p )  for p in self.Instance.ProductSet ]
        self.InventoryVariable = [ ( self.Instance.StartInventoryVariableWithoutNonAnticipativity + self.Instance.NrProduct  * ( self.NodeNumber -1 )  + p )  for p in self.Instance.ProductSet ]
        self.BackOrderVariable = [ (self.Instance.StartBackorderVariableWithoutNonAnticipativity + self.Instance.NrProduct  * ( self.NodeNumber -1 )  + p ) for p in self.Instance.ProductSet ]

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
            self.DemandsInScenario.append( self.Demand )
            self.QuanitityVariableOfScenario.append( self.QuanitityVariable )
            self.ProductionVariableOfScenario.append( self.ProductionVariable )
            self.InventoryVariableOfScenario.append( self.InventoryVariable )
            self.BackOrderVariableOfScenario.append( self.BackOrderVariable )

            self.ProbabilityOfScenario = self.ProbabilityOfScenario * self.Probability
        else :
            self.ProbabilityOfScenario = 1

        # If the node is a not leave, run the method for the child
        for b in self.Branches:
            b.CreateAllScenarioFromNode( );