from ScenarioTreeNode import ScenarioTreeNode
from Scenario import Scenario
import cPickle as pickle
import numpy as np
from RQMCGenerator import RQMCGenerator
import os
from Constants import Constants
from ast import literal_eval
from matplotlib import pyplot as PLT

class ScenarioTree:
    #Constructor
    def __init__( self, instance = None, branchperlevel = [], seed = -1, mipsolver = None, evaluationscenario = False, averagescenariotree = False,  givenfirstperiod = [], scenariogenerationmethod = "MC", generateRQMCForYQfix = False, generateasYQfix = False, model = "YFix" ):
        self.Seed = seed
        np.random.seed( seed )
        self.Nodes = []
        self.Owner = mipsolver
        self.Instance = instance
        self.TreeStructure = branchperlevel
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
            treestructure = [1,2] + [1] * (instance.NrTimeBucket-1) + [0]
            YQFixTree =   ScenarioTree( instance, treestructure, seed, scenariogenerationmethod=self.ScenarioGenerationMethod )
            YQFixSceanrios =  YQFixTree.GetAllScenarios( computeindex= False)
            self.DemandToFollow = [ [ [  YQFixSceanrios[w].Demands[t][p] for p in self.Instance.ProductSet ]
                                                                            for t in self.Instance.TimeBucketSet ]
                                                                               for w in range(len(YQFixSceanrios) )  ]

        self.DemandYQFixRQMC = []
        self.GenerateRQMCForYQFix = generateRQMCForYQfix
        self.Model = model
        if self.ScenarioGenerationMethod == Constants.All and model == Constants.ModelYQFix:

            temporarytreestructur = [1, 8, 8, 8, 1, 1, 1, 0]
            temporaryscenariotree = ScenarioTree(self.Instance, temporarytreestructur, self.Seed,
                                        averagescenariotree=False,
                                        scenariogenerationmethod=Constants.All,
                                        generateRQMCForYQfix=False)
            temporaryscenarios = temporaryscenariotree.GetAllScenarios( False )
            self.DemandYQFixRQMC = [[[temporaryscenarios[s].Demands[t][p]
                                      if self.Instance.HasExternalDemand[p]
                                      else 0.0
                                      for p in self.Instance.ProductSet]
                                     for t in self.Instance.TimeBucketSet]
                                    for s in range(512)]

        if self.ScenarioGenerationMethod == Constants.RQMC and generateRQMCForYQfix:
             nrtimebuckets = self.Instance.NrTimeBucket - self.Instance.NrTimeBucketWithoutUncertainty
             avgvector = [  self.Instance.ForecastedAverageDemand[t][p] for p in self.Instance.ProductWithExternalDemand for t in range( nrtimebuckets ) ]
             stdvector = [  self.Instance.ForcastedStandardDeviation[t][p] for p in self.Instance.ProductWithExternalDemand for t in range( nrtimebuckets ) ]
             dimension = len( self.Instance.ProductWithExternalDemand ) * (nrtimebuckets)
             nrscenarion = self.NrBranches[1]
             rqmcpoint01 = RQMCGenerator.RQMC01( nrscenarion , dimension  )

             # for d in range(dimension):
             #     pts = [rqmcpoint01[p][d] for p in range(nrscenarion)]
             #     print "The point at dim %d at time : %r  " % (d, pts)
             #     with open('Histpoints%dt%d.csv' % (p, d), 'w+') as f:
             #         # v_hist = np.ravel(v)  # 'flatten' v
             #         fig = PLT.figure()
             #         ax1 = fig.add_subplot(111)
             #
             #         n, bins, patches = ax1.hist(pts, bins=100, normed=1, facecolor='green')
             #         PLT.show()

             rmcpoint = ScenarioTreeNode.TransformInverse( rqmcpoint01, nrscenarion, dimension, self.Instance.Distribution, avgvector, stdvector )


             # indices =  [[[self.Instance.ProductWithExternalDemandIndex[p] * nrtimebuckets + t
             #    if self.Instance.HasExternalDemand[p]
             #    else -1
             #               for s in range(nrscenarion)   ]
             #   for t in range(nrtimebuckets)]
             #   for p in self.Instance.ProductSet]
             #
             # print "Used indices %r"%indices


             self.DemandYQFixRQMC = [ [ [ rmcpoint[ self.Instance.ProductWithExternalDemandIndex[p] * nrtimebuckets + t ][s]
                                          if  self.Instance.HasExternalDemand[p]
                                          else 0.0
                                        for p in self.Instance.ProductSet ]
                                      for t in range( nrtimebuckets ) ]
                                     for s in range( nrscenarion )]

             # for p in self.Instance.ProductSet:
             #     for t in range(nrtimebuckets):
             #        pts = [self.DemandYQFixRQMC[ s][t][p] for s in range( nrscenarion ) ]
             #        print "The transformed point at dim %d at time %d : %r  " % (p,t, pts)
             #        with open('Histpoints%dt%d.csv' % (p, t), 'w+') as f:
             #            # v_hist = np.ravel(v)  # 'flatten' v
             #            fig = PLT.figure()
             #            ax1 = fig.add_subplot(111)
             #
             #            n, bins, patches = ax1.hist(pts, bins=100, normed=1, facecolor='green')
             #            PLT.show()


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
                               backordervariable=s.BackOrderVariableOfScenario,
                               nodesofscenario = s.NodesOfScenario) for s in scenarioset ]

        id = 0
        for s in scenarios:
            s.ScenarioId = id
            id = id +1

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

    #This function set the quantity to order at each node of the tree as found in the solution given in argument
    def FillQuantityToOrder(self, sol):
        for n in self.Nodes:
            if n.Time >= 0 and n.Time < self.Instance.NrTimeBucket :
                n.QuantityToOrder = sol.get_values( [ n.QuanitityVariable[ p ]for p in self.Instance.ProductSet ] )
                if n.Time >0:
                    n.InventoryLevel = sol.get_values([n.InventoryVariable[p] for p in self.Instance.ProductSet])
                    n.BackOrderLevel = sol.get_values([n.BackOrderVariable[ self.Instance.ProductWithExternalDemandIndex[p] ] for p in self.Instance.ProductWithExternalDemand])


    #This function set the quantity to order at each node of the tree as found in the solution given in argument
    def FillQuantityToOrderFromMRPSolution(self, sol, scenarios):
        scenarionr = -1
        for n in self.Nodes:
            if n.Time >= 0 and  n.Time < self.Instance.NrTimeBucket :
                scenarionr = n.OneOfScenario.ScenarioId
                n.QuantityToOrderNextTime =  [ sol.ProductionQuantity[scenarionr][n.Time  ][p]
                                            for p in self.Instance.ProductSet ]

                n.InventoryLevelNextTime = [ sol.InventoryLevel[scenarionr][n.Time ][p] if not self.Instance.HasExternalDemand[p] else float( 'nan' )
                                            for p in self.Instance.ProductSet ]

                if n.Time >= 1:
                    n.BackOrderLevelTime = [ sol.BackOrder[scenarionr][n.Time -1 ][self.Instance.ProductWithExternalDemandIndex[p]]
                                            for p in self.Instance.ProductWithExternalDemand ]

                    n.InventoryLevelTime = [ sol.InventoryLevel[scenarionr][n.Time -1 ][p]
                                             if  self.Instance.HasExternalDemand[p] else float( 'nan' )
                                            for p in self.Instance.ProductSet ]

