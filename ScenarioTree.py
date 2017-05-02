from ScenarioTreeNode import ScenarioTreeNode
from Scenario import Scenario
import cPickle as pickle
import numpy as np
import os
class ScenarioTree:
    #Constructor
    def __init__( self, instance = None, branchperlevel = [], seed = -1, mipsolver = None, averagescenariotree = False, slowmoving = False ):
        self.Seed = seed
        np.random.seed( seed )
        self.Nodes = []
        self.Owner = mipsolver
        self.Instance = instance
        self.NrBranches = branchperlevel
        ScenarioTreeNode.NrNode = 0
        self.Distribution = "Normal"
        if slowmoving:
                self.Distribution = "SlowMoving"
        self.RootNode =  ScenarioTreeNode( owner = self, instance = instance, mipsolver = self.Owner,  time = -1, nrbranch = 1, proabibilty = 1, averagescenariotree = averagescenariotree,  slowmoving = slowmoving )
        if instance is None:
            self.NrLevel = -1
        else:
            self.NrLevel = instance.NrTimeBucket
        self.NrNode = ScenarioTreeNode.NrNode

    #Compute the index of the variable (one variable for each node of the tree)
    def ComputeVariableIdicies( self ):
        for n in self.Nodes:
            n.ComputeVariableIndex();

    #Print the scenario tree
    def Display( self ):
        print "Print the tree: "
        self.RootNode.Display()

    #This function assemble the data in the tree, and return the list of leaves, which contain the scenarios
    def GetAllScenarios( self ):
        self.ComputeVariableIdicies()
        self.RootNode.CreateAllScenarioFromNode( )
        #return the set of leaves as they represent the scenario
        scenarioset = [ n for n in self.Nodes if len( n.Branches ) == 0 ]
        self.ComputeVariableIdicies()

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

