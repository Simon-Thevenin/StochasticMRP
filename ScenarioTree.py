from ScenarioTreeNode import ScenarioTreeNode
import cPickle as pickle
import numpy as np
import os
class ScenarioTree:
    #Constructor
    def __init__( self, instance = None, branchperlevel = [], seed = -1 ):
        self.Seed = seed
        np.random.seed( seed )
        self.Nodes = []
        self.Owner = instance
        self.NrBranches = branchperlevel
        ScenarioTreeNode.NrNode = 0
        self.RootNode =  ScenarioTreeNode( owner = self, instance = instance, time = -1, nrbranch = 1, proabibilty = 1 )
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
    def CreateAllScenario( self ):
        self.ComputeVariableIdicies()
        self.RootNode.CreateAllScenarioFromNode( )
        #return the set of leaves as they represent the scenario
        scenarioset = [ n for n in self.Nodes if len( n.Branches ) == 0 ]
        self.ComputeVariableIdicies()
        return scenarioset

    #Save the scenario tree in a file
    def SaveInFile( self, scearionr ):
        result = None
        filepath = './Instances/' + self.Owner.InstanceName + '_Scenario%s.pkl'%scearionr
        try:
          with open( filepath, 'wb') as output:
               pickle.dump(self, output, pickle.HIGHEST_PROTOCOL)
        except: 
          print "file %r not found" %(filepath)
