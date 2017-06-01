from ScenarioTreeNode import ScenarioTreeNode
from Scenario import Scenario
import cPickle as pickle
import numpy as np
import os
from Constants import Constants

class ScenarioTree:
    #Constructor
    def __init__( self, instance = None, branchperlevel = [], seed = -1, mipsolver = None, evaluationscenario = False, averagescenariotree = False, generateasYQfix = False, givenfirstperiod = [], scenariogenerationmethod = "MC", generateRQMCForYQfix = False ):
        self.Seed = seed
        np.random.seed( seed )
        self.Nodes = []
        self.Owner = mipsolver
        self.Instance = instance
        self.NrBranches = branchperlevel
        self.EvaluationScenrio = evaluationscenario
        self.AverageScenarioTree = averagescenariotree
        self.ScenarioGenerationMethod = scenariogenerationmethod
        ScenarioTreeNode.NrNode = 0
        #For some types of evaluation, the demand of the  first periods are given and the rest is stochastic
        self.GivenFirstPeriod = givenfirstperiod
        self.FollowGivenUntil = len(self.GivenFirstPeriod )
        #In case the scenario tree has to be the same aas the two stage (YQFix) scenario tree.
        self.GenerateasYQfix = generateasYQfix
        self.Distribution = instance.Distribution
        self.DemandToFollow = []
        #Generate the demand of YFix, then replicate them in the generation of the scenario tree
        if self.GenerateasYQfix :
            treestructure = [1,8] + [1] * (instance.NrTimeBucket-1) + [0]
            YQFixTree =   ScenarioTree( instance, treestructure, seed, scenariogenerationmethod=self.ScenarioGenerationMethod )
            YQFixSceanrios =  YQFixTree.GetAllScenarios( computeindex= False)
            self.DemandToFollow = [ [ [  YQFixSceanrios[w].Demands[t][p] for p in self.Instance.ProductSet ]
                                                                            for t in self.Instance.TimeBucketSet ]
                                                                               for w in range(len(YQFixSceanrios) )  ]

        self.DemandYQFixRQMC = []
        self.GenerateRQMCForYQFix = generateRQMCForYQfix
        if self.ScenarioGenerationMethod == Constants.RQMC and generateRQMCForYQfix:
            nrtimebuckets = self.Instance.NrTimeBucket - self.Instance.NrTimeBucketWithoutUncertainty
            avgvector = [  self.Instance.AverageDemand[p] for p in self.Instance.ProductWithExternalDemand for t in range( nrtimebuckets ) ]
            stdvector = [  self.Instance.StandardDevDemands[p] for p in self.Instance.ProductWithExternalDemand for t in range( nrtimebuckets ) ]
            dimension = len( self.Instance.ProductWithExternalDemand ) * (nrtimebuckets)
            nrscenarion = self.NrBranches[1]
            rqmcpoint01 = ScenarioTreeNode.RQMC01( nrscenarion , dimension  )
            rmcpoint = ScenarioTreeNode.TransformInverse( rqmcpoint01, nrscenarion, dimension, self.Instance.Distribution, avgvector, stdvector )
            self.DemandYQFixRQMC = [ [ [ rmcpoint[ self.Instance.ProductWithExternalDemandIndex[p] * nrtimebuckets + t ][s]
                                         if  self.Instance.HasExternalDemand[p]
                                         else 0.0
                                       for p in self.Instance.ProductSet ]
                                     for t in range( nrtimebuckets ) ]
                                    for s in range( nrscenarion )]

        self.RootNode =  ScenarioTreeNode( owner = self,
                                           instance = instance,
                                           mipsolver = self.Owner,
                                           time = -1, nrbranch = 1,
                                           proabibilty = 1,
                                           averagescenariotree = True )
        if instance is None:
            self.NrLevel = -1
        else:
            self.NrLevel = instance.NrTimeBucket
        self.NrNode = ScenarioTreeNode.NrNode
        self.Renumber()

    #This function number the node from highest level to lowest.
    def Renumber( self ):
        k = 1
        #Traverse the node per level
        nrlevel = max( n.Time for n in self.Nodes )
        for l in range( nrlevel + 1 ):
            #get the set of node in the level
            nodes = [ n for n in self.Nodes if n.Time == l ]
            for n in nodes:
                n.NodeNumber = k
                k = k + 1

    #Compute the index of the variable (one variable for each node of the tree)
    def ComputeVariableIdicies( self ):
        for n in self.Nodes:
            n.ComputeVariableIndex();

    #Print the scenario tree
    def Display( self ):
        print "Print the tree: "
        self.RootNode.Display()

    #This function assemble the data in the tree, and return the list of leaves, which contain the scenarios
    def GetAllScenarios( self, computeindex = True ):
        #A mip solver is required to compute the index, it is not always set
        if computeindex:
            self.ComputeVariableIdicies()
        self.RootNode.CreateAllScenarioFromNode( )
        #return the set of leaves as they represent the scenario
        scenarioset = [ n for n in self.Nodes if len( n.Branches ) == 0 ]

        scenarios = [ Scenario(owner=self,
                               demand=s.DemandsInScenario,
                               proabability=s.ProbabilityOfScenario,
                               quantityvariable=s.QuanitityVariableOfScenario,
                               productionvariable=s.ProductionVariableOfScenario,
                               inventoryvariable=s.InventoryVariableOfScenario,
                               backordervariable=s.BackOrderVariableOfScenario) for s in scenarioset ]

        return scenarios

    #Save the scenario tree in a file
    def SaveInFile( self, scearionr ):
        result = None
        filepath = './Instances/' + self.Instance.InstanceName + '_Scenario%s.pkl'%scearionr
        try:
          with open( filepath, 'wb') as output:
               pickle.dump(self, output, pickle.HIGHEST_PROTOCOL)
        except: 
          print "file %r not found" %(filepath)

    def FillQuantityToOrder(self, sol):
        for n in self.Nodes:
            if n.Time >= 0 and n.Time < self.Instance.NrTimeBucket :
                 n.QuantityToOrder = sol.get_values( [ n.QuanitityVariable[ p ] for p in self.Instance.ProductSet ] )
                 n.QuantityToOrder = [ round( n.QuantityToOrder[p], 2)for p in self.Instance.ProductSet ]