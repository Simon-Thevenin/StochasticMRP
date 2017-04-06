from ScenarioTreeNode import ScenarioTreeNode


class ScenarioTree:

    def __init__( self, instance = None, branchperlevel = [] ):
        self.Nodes = []
        self.NrBranches = branchperlevel
        self.RootNode =  ScenarioTreeNode( owner = self, instance = instance, time = -1, nrbranch = 1, proabibilty = 1 )
        if instance is None:
            self.NrLevel = -1
        else:
            self.NrLevel = instance.NrTimeBucket
        self.NrNode = ScenarioTreeNode.NrNode

    def ComputeVariableIdicies( self ):
        for n in self.Nodes:
            n.ComputeVariableIndex();

    def Display( self ):
        print "Print the tree: "
        self.RootNode.Display()

    #This function assemble the data in the tree, and return the list of leaves, which contain the scenarios
    def CreateAllScenario( self ):
        self.ComputeVariableIdicies()
        self.RootNode.CreateAllScenarioFromNode( )
        #return the set of leaves as they represent the scenario
        scenarioset = [ n for n in self.Nodes if len( n.Branches ) == 0 ]
        return scenarioset
