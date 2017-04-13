import pandas as pd
import openpyxl as opxl
import itertools as itools
import math
from ScenarioTree import ScenarioTree
from Scenario import Scenario
import cPickle as pickle
import os

class MRPInstance:

    FileName = "./Instances/MSOM-06-038-R2.xls"

    #This function print the instance on the screen
    def PrintInstance( self ):
        print "instance: %s" %self.InstanceName
        print "instance with %d products and %d time buckets" % ( self.NrProduct, self.NrTimeBucket );
        print "requirements: \n %r" % (pd.DataFrame( self.Requirements, index = self.ProductName, columns = self.ProductName ) );
        print "CapacityConsumptions: \n %r" % (pd.DataFrame( self.CapacityConsumptions, index = self.ProductName ) );
        aggregated = [ self.Leadtimes, self.StartingInventories, self.InventoryCosts,
                       self.SetupCosts, self.BackorderCosts]
        col = [ "Leadtimes", "StartingInventories", "InventoryCosts", "SetupCosts", "BackorderCosts" ]
        print "Per product data: \n %r" % ( pd.DataFrame( aggregated, columns = self.ProductName, index = col ).transpose() );
        self.DemandScenarioTree.Display()
        # Print the set of scenario
        print "Print the scenarios:"
        for s in self.Scenarios:
            s.DisplayScenario()

    #This function print the scenario of the instance in an excel file
    def PrintScenarioToFile( self ):
        #writer = pd.ExcelWriter( "./Instances/" + self.InstanceName + "_Scenario.xlsx",
        #                                engine='openpyxl' )
        #for s in self.Scenarios:
        #    s.PrintScenarioToExcel( writer )
        #writer.save()
        self.DemandScenarioTree.SaveInFile()

    #This function define the current instance as a  small one, used to test the model
    def DefineAsSmallIntance(self ):
        self.InstanceName = "SmallIntance"
        self.ProductName = [ "P1", "P2", "P3", "P4", "P5" ]
        self.NrProduct = 5
        self.NrTimeBucket = 6
        self.NrResource = 5
        self.Requirements = [ [ 0, 1, 1, 0, 0 ],
                              [ 0, 0, 0, 1, 0 ],
                              [ 0, 0, 0, 0, 0 ],
                              [  0, 0, 0, 0, 1 ],
                              [ 0, 0, 0, 0, 0 ] ]
        self.Leadtimes = [0, 1, 1, 1, 1]
        self.StandardDevDemands = [ 5, 0, 0, 0, 0 ]
        self.AverageDemand = [ 10, 0, 0, 0, 0 ]
        self.StartingInventories = [10.0, 100.0, 100.0, 100.0, 100.0]
        self.InventoryCosts = [15.0, 4.0, 3.0, 2.0, 1.0]
        self.SetupCosts = [10000.0, 1.0, 1.0, 1.0, 1.0]
        self.BackorderCosts = [100000.0, 0.0, 0.0, 0.0, 0.0]  # for now assume no external demand for components
        self.CapacityConsumptions = [ [0.01, 0.0, 0.0, 0.0, 0.0],
                                      [0.0, 0.02, 0.0, 0.0, 0.0],
                                      [0.0, 0.0, 0.01, 0.0, 0.0],
                                      [0.0, 0.0, 0.0, 0.01, 0.0],
                                      [0.0, 0.0, 0.0, 0.0, 0.04] ]
        self.ComputeInstanceData()

     # This function defines a very small instance, this is usefull for debugging.
    def DefineAsSuperSmallIntance(self ):

        self.InstanceName = "SuperSmallIntance"
        self.ProductName = [ "P1", "P2" ]
        self.NrProduct = 2
        self.NrTimeBucket = 3
        self.NrResource = 2
        self.Requirements = [ [ 0, 1 ],
                              [ 0, 0 ] ]
        self.Leadtimes = [ 0, 1 ]
        self.StandardDevDemands = [ 5, 0 ]
        self.AverageDemand = [ 10, 0 ]
        self.StartingInventories = [ 10.0, 10.0 ]
        self.InventoryCosts = [ 10.0, 5.0 ]
        self.SetupCosts = [ 5.0, 5.0 ]
        self.BackorderCosts = [ 10000.0, 0.0 ]  # for now assume no external demand for components
        self.CapacityConsumptions = [ [ 0.0001, 0.0 ],
                                      [ 0.0, 0.002 ] ]

        self.ComputeInstanceData()

    #This function compute the data required to solve the instance ( indices of the variable, cretae the scenarios, level in the supply chain, .... )
    def ComputeInstanceData(self):
        self.ComputeIndices()
        self.ComputeLevel()
        self.ComputeMaxLeadTime()
        self.NrScenario = len( self.Scenarios )
        self.ComputeIndices()
        self.NrScenario, self.Scenarios = self.CreateAllScenario( )
        # update indices to take into account the scenario
        self.ComputeIndices()
        self.ComputeHasExternalDemand()
        self.RequieredProduct = [ [ q for q in self.ProductSet  if self.Requirements[ q ][ p ] > 0.0 ] 
                                                                    for p in self.ProductSet ]
    #Constructor
    def __init__( self ):
        self.InstanceName = ""
        self.NrProduct = -1
        self.NrTimeBucket = -1
        self.NrResource = -1
        self.NrScenario = -1
        self.ProductSet = []
        self.TimeBucketSet = []
        self.ScenarioSet = []
        self.AverageDemand = []
        self.StandardDevDemands = []
        self.Requirements = []
        self.Leadtimes = []
        self.StartingInventories = []
        self.InventoryCosts = []
        self.SetupCosts = []
        self.BackorderCosts = []
        self.CapacityConsumptions = []
        self.HasExternalDemand = []
        #The set of product which are required for production of each product.
        self.RequieredProduct = [] 
        # Define some attributes and functions which help to et the index of the variable.
        # the attributs nrquantiyvariables, nrinventoryvariable, nrproductionvariable, and nrbackordervariable gives the number
        # of variable of each type
        self.NrQuantiyVariables = 0
        self.NrInventoryVariable = 0
        self.NrProductionVariable = 0
        self.NrBackorderVariable = 0
        # The variable startquantityvariable, startinventoryvariable, startprodustionvariable, and startbackordervariable gives
        # the index at which each variable type start
        self.StartQuantityVariable = 0
        self.StartInventoryVariable = 0
        self.StartProdustionVariable = 0
        self.StartBackorderVariable = 0

        # The attribut below correspond to the index of the variable when the non atticiaptivity constraint
        #  are not added and the noon requireed variables are not added
        self.NrQuantiyVariablesWithoutNonAnticipativity = 0
        self.NrInventoryVariableWithoutNonAnticipativity  = 0
        self.NrProductionVariableWithoutNonAnticipativity  = 0
        self.NrBackorderVariableWithoutNonAnticipativity  = 0
        self.StartQuantityVariableWithoutNonAnticipativity  = 0
        self.StartInventoryVariableWithoutNonAnticipativity  = 0
        self.StartProdustionVariableWithoutNonAnticipativity  = 0
        self.StartBackorderVariableWithoutNonAnticipativity  = 0

        #Compute the index of the variable if two stage is used
        self.NrQuantiyVariablesTwoStages  = 0
        self.NrInventoryVariableTwoStages = 0
        self.NrProductionVariableTwoStages = 0
        self.NrBackorderVariableTwoStages = 0
        self.StartQuantityVariableTwoStages = 0
        self.StartInventoryVariableTwoStages = 0
        self.StartProdustionVariableTwoStages = 0
        self.StartBackorderVariableTwoStages = 0

        self.ProductName = ""
        #Compute some statistic about the instance
        self.MaxLeadTime = -1
        self.NrLevel = -1
        self.Level = [] # The level of each product in the bom
        self.MaxLeadTimeProduct = [] #The maximum leadtime to the component for each product
        self.DemandScenarioTree = ScenarioTree( instance = self )
        self.Scenarios = []

        #If this is true, a single scenario with average demand is generated
        self.Average = False
        self.LoadScenarioFromFile = False
        self.NrScenarioPerBranch = 3

    #Compute the lead time from a product to its component with the largest sum of lead time
    def ComputeMaxLeadTime( self ):
        self.MaxLeadTimeProduct = [ 0 for p in self.ProductSet ]
        levelset = sorted( set(  self.Level ), reverse=True )
        for l in levelset:
            prodinlevel = [ p for p in self.ProductSet if  self.Level[ p ] == l ]
            for p in prodinlevel:
                parents = [ q for q in self.ProductSet if self.Requirements[ p ][ q ] > 0 ]
                if len( parents ) > 0 :
                    self.MaxLeadTimeProduct[ p ] = max( [ self.MaxLeadTimeProduct [ q ] for q in parents ] );
                self.MaxLeadTimeProduct[p] =  self.MaxLeadTimeProduct[p] + self.Leadtimes[ p ]
        self.MaxLeadTime = max( self.MaxLeadTimeProduct[p] for p in self.ProductSet )

    #This function compute at which level each node is in the supply chain
    def ComputeLevel( self ) :
        #Maximum lead time and maximum number of level.
        #Get the set of nodes without children
        currentlevelset = [ p for p in self.ProductSet if sum( self.Requirements[ q ][ p ]
                                                              for q in self.ProductSet  ) == 0 ];
        currentlevel = 1
        self.Level = [ 0 for p in self.ProductSet ]
        while len(currentlevelset) > 0 :
            nextlevelset = []
            for p in currentlevelset:
                self.Level[ p ] = currentlevel
                childrenofp = [ q for q in self.ProductSet
                                   if self.Requirements[ p ][ q ] == 1];
                nextlevelset = nextlevelset + childrenofp
            currentlevelset = set( nextlevelset )
            currentlevel = currentlevel + 1

        self.NrLevel = max( self.Level[ p ] for p in self.ProductSet )

    def ComputeHasExternalDemand(self):
        self.HasExternalDemand = [  ( ( sum(self.Scenarios[w].Demands[t][p] for t in self.TimeBucketSet
                                                                            for w in self.ScenarioSet ) ) > 0  )
                                    for p in self.ProductSet ]


    #Compute the start of index and the number of variables for the considered instance
    def ComputeIndices( self ):
        self.NrQuantiyVariables = self.NrProduct * self.NrTimeBucket * self.NrScenario
        self.NrInventoryVariable = self.NrProduct * self.NrTimeBucket * self.NrScenario
        self.NrProductionVariable = self.NrProduct  *  self.NrTimeBucket  * self.NrScenario
        self.NrBackorderVariable = self.NrProduct * self.NrTimeBucket * self.NrScenario
        self.StartQuantityVariable = 0
        self.StartInventoryVariable =  self.StartQuantityVariable + self.NrQuantiyVariables
        self.StartProdustionVariable = self.StartInventoryVariable +  self.NrInventoryVariable
        self.StartBackorderVariable =   self.StartProdustionVariable +  self.NrProductionVariable
        self.ProductSet = range( self.NrProduct )
        self.TimeBucketSet = range( self.NrTimeBucket )
        self.ScenarioSet = range( self.NrScenario )

        #The indices of the variable in the case where the non anticipativity constraints are created explicitely
        self.NrQuantiyVariablesWithoutNonAnticipativity = self.NrProduct  * ( self.DemandScenarioTree.NrNode -2 ) #remove the root node
        self.NrInventoryVariableWithoutNonAnticipativity = self.NrProduct *  ( self.DemandScenarioTree.NrNode -2 )
        self.NrProductionVariableWithoutNonAnticipativity = self.NrProduct  * ( self.DemandScenarioTree.NrNode -2 )
        self.NrBackorderVariableWithoutNonAnticipativity = self.NrProduct  *( self.DemandScenarioTree.NrNode -2 )
        self.StartQuantityVariableWithoutNonAnticipativity = 0
        self.StartInventoryVariableWithoutNonAnticipativity =  self.StartQuantityVariableWithoutNonAnticipativity + self.NrQuantiyVariablesWithoutNonAnticipativity
        self.StartProdustionVariableWithoutNonAnticipativity = self.StartInventoryVariableWithoutNonAnticipativity +  self.NrInventoryVariableWithoutNonAnticipativity
        self.StartBackorderVariableWithoutNonAnticipativity =   self.StartProdustionVariableWithoutNonAnticipativity +  self.NrProductionVariableWithoutNonAnticipativity

        #The indices of the variable in the case where the a two stage problem is solved
        self.NrQuantiyVariablesTwoStages = self.NrProduct +  self.NrProduct * ( self.NrTimeBucket -1 ) * self.NrScenario
        self.NrInventoryVariableTwoStages =  self.NrProduct +  self.NrProduct * ( self.NrTimeBucket -1 ) * self.NrScenario
        self.NrProductionVariableTwoStages = self.NrProduct +  self.NrProduct * ( self.NrTimeBucket -1 ) * self.NrScenario
        self.NrBackorderVariableTwoStages =  self.NrProduct +  self.NrProduct * ( self.NrTimeBucket -1 ) * self.NrScenario
        self.StartQuantityVariableTwoStages = 0
        self.StartInventoryVariableTwoStages = self.StartQuantityVariableTwoStages + self.NrQuantiyVariablesTwoStages
        self.StartProdustionVariableTwoStages = self.StartInventoryVariableTwoStages + self.NrInventoryVariableTwoStages
        self.StartBackorderVariableTwoStages = self.StartProdustionVariableTwoStages + self.NrProductionVariableTwoStages

        #The indices of the variable in the case where a one stage problem is solved
        self.NrQuantiyVariablesOneStage =  self.NrProduct * ( self.NrTimeBucket  )
        self.StartQuantityVariableOneStage = 0
        self.StartInventoryVariableOneStage = self.StartQuantityVariableOneStage + self.NrQuantiyVariablesOneStage
        self.StartProdustionVariableOneStage = self.StartInventoryVariableOneStage + self.NrInventoryVariable
        self.StartBackorderVariableOneStage = self.StartProdustionVariableOneStage + self.NrProductionVariable

    #This function transform the sheet given in arguments into a dataframe
    def ReadDataFrame( self, wb2, framename ):
        sheet = wb2[framename];
        data =  sheet.values
        cols = next( data ) [ 1: ]
        cols = list( cols )
        #remove the None from the column names
        for i in range( len( cols ) ):
            if cols[i] == None :
                cols[i] = i

        data = list( data )
        idx = [ r[ 0 ] for r in data ]
        data = ( itools.islice(r, 1, None ) for r in data )
        df = pd.DataFrame( data, index=idx, columns=cols )
        return df;

    #This function load the scenario tree from a fil
    def LoadFromFile( self ):
        result = None
        filepath = '/tmp/thesim/' + self.InstanceName + '_Scenario%r.pkl'%self.NrScenarioPerBranch
        try:
          with open( filepath, 'rb') as input:
              result = pickle.load( input )
          return result
        except: 
          print "file %r not found" %(filepath)

    #This function create all the scenario using a scenario tree
    def CreateAllScenario( self, ):
        if self.Average: #1 scenario corresponding to the average demand
            self.StandardDevDemands = [0] * self.NrProduct
            nrbranchperlevellist = [1]  * (self.NrTimeBucket +1)
            self.DemandScenarioTree = ScenarioTree( self, nrbranchperlevellist );

        elif self.LoadScenarioFromFile : #Load the scenario tree from a file
            self.DemandScenarioTree = self.LoadFromFile()

        else :#Create the scenario tree
            nrbranchperlevellist = [1] + [self.NrScenarioPerBranch ] * ( self.NrTimeBucket )
            self.DemandScenarioTree =  ScenarioTree( self, nrbranchperlevellist );

        #Re-compute the indices to set the variable index to the correct values
        self.ComputeIndices()
        scenariosasleaf = self.DemandScenarioTree.CreateAllScenario()
        #Build the set of scenarios by copying the leaves
        scenarios = [ Scenario( owner = self,
                                demand = s.DemandsInScenario,
                                proabability = s.ProbabilityOfScenario,
                                quantityvariable = s.QuanitityVariableOfScenario,
                                productionvariable = s.ProductionVariableOfScenario,
                                inventoryvariable = s.InventoryVariableOfScenario,
                                backordervariable = s.BackOrderVariableOfScenario ) for s in scenariosasleaf ]

        return len(scenarios), scenarios

    #This funciton read the instance from the file ./Instances/MSOM-06-038-R2.xlsx
    def ReadFromFile( self, instancename, nrscenario ):
        wb2 = opxl.load_workbook( "./Instances/MSOM-06-038-R2.xlsx" )
        #The supplychain is defined in the sheet named "01_LL" and the data are in the sheet "01_SD"
        supplychaindf = self.ReadDataFrame( wb2, instancename + "_LL" )
        datasheetdf = self.ReadDataFrame( wb2, instancename + "_SD" )
        datasheetdf = datasheetdf.fillna(0)
        #read the data
        self.ProductName = list( datasheetdf.index.values )
        self.InstanceName = instancename
        #This set of instances assume no capacity
        self.NrResource =  len( self.ProductName )
        self.NrProduct = len( self.ProductName )
        self.NrTimeBucket = 0
        self.ComputeIndices()
        #This set of instances assume no setup
        self.SetupCosts = [ 10.0 ] * self.NrProduct 
         #Get the average demand, lead time
        self.Leadtimes = [1 for p in self.ProductSet]

        #self.Leadtimes =  [  int ( math.ceil( datasheetdf.get_value( self.ProductName[ p ], 'stageTime' ) ) ) for p in self.ProductSet ]
        print " CAUTION: LEAD TIME ARe MODIFIED"
        #Compute the requireement from the supply chain. This set of instances assume the requirement of each arc is 1.
        self.Requirements = [ [ 0 ] * self.NrProduct for _ in self.ProductSet ]
        for i, row in supplychaindf.iterrows():
            self.Requirements[ self.ProductName.index( row.get_value('destinationStage' ) ) ][ self.ProductName.index( i ) ] = 1
        #Assume an inventory holding cost of 0.1 per day for now
        holdingcost = 0.1
        self.InventoryCosts = [ 0.0 ] * self.NrProduct
        #The cost of the product is given by  added value per stage. The cost of the product at each stage must be computed
        addedvalueatstage = [ datasheetdf.get_value( self.ProductName[ p ], 'stageCost' ) for p in self.ProductSet ]
        level = [ datasheetdf.get_value( self.ProductName[ p ], 'relDepth' ) for p in self.ProductSet    ]
        levelset = sorted( set( level ), reverse=True )
        for l in levelset:
            prodinlevel =  [ p for p in self.ProductSet  if level[p] == l ]
            for p in prodinlevel:
                addedvalueatstage[p] = sum(addedvalueatstage[ q ] * self.Requirements[p][q] for q in self.ProductSet ) + \
                                            addedvalueatstage[ p ]
                self.InventoryCosts[p] = holdingcost *  addedvalueatstage[ p ]

        #The instances provide a level of service and no back order cost. Assume a backorder cost of 0.1.
        self.BackorderCosts = [ 10 ] * self.NrProduct
        self.ComputeLevel()
        self.ComputeMaxLeadTime( )
        # Consider a time horizon of 20 days plus the total lead time
        self.NrTimeBucket = 2* self.MaxLeadTime
        self.ComputeIndices()
        # Assume a starting inventory is the average demand during the lead time
        self.StartingInventories = [ datasheetdf.get_value( self.ProductName[ p ], 'avgDemand')
                                     * max( self.Leadtimes[q] *  self.Requirements[ q ][ p ]  for q in self.ProductSet )
                                     for p in self.ProductSet ] 

        #Generate the sets of scenarios
        self.AverageDemand = [ datasheetdf.get_value( self.ProductName[ p ], 'avgDemand') for p in self.ProductSet ]
        self.StandardDevDemands = [ datasheetdf.get_value( self.ProductName[ p ], 'stdDevDemand') for p in self.ProductSet ]
        self.CapacityConsumptions =  [ [ 1.0 / ( datasheetdf.get_value( self.ProductName[ p ], 'avgDemand')
                                                  + datasheetdf.get_value( self.ProductName[ p ], 'stdDevDemand')  )
                                        if ( p == k and ( ( datasheetdf.get_value( self.ProductName[ p ], 'avgDemand')
                                                  + datasheetdf.get_value( self.ProductName[ p ], 'stdDevDemand') ) > 0 ) )   else 0.0
                                        for p in self.ProductSet ] for k in range( self.NrResource ) ]
        self.CapacityConsumptions =  [ [ 0.0  for p in self.ProductSet ] for k in range( self.NrResource ) ]
        self.ComputeInstanceData()