import pandas as pd
import openpyxl as opxl
import itertools as itools
import math

class MRPInstance:

    FileName = "./Instances/MSOM-06-038-R2.xls"

    def PrintInstance( self ):
        print "instance: %s" %self.InstanceName
        print "instance with %d products and %d time buckets" % ( self.NrProduct, self.NrTimeBucket );
        print "demand: \n %r" % ( pd.DataFrame( self.Demands, index = self.ProductName ) );
        print "requirements: \n %r" % (pd.DataFrame( self.Requirements, index = self.ProductName, columns = self.ProductName ) );
        print "CapacityConsumptions: \n %r" % (pd.DataFrame( self.CapacityConsumptions, index = self.ProductName ) );
        aggregated = [ self.Leadtimes, self.StartingInventories, self.InventoryCosts,
                       self.SetupCosts, self.BackorderCosts]
        col = [ "Leadtimes", "StartingInventories", "InventoryCosts", "SetupCosts", "BackorderCosts" ]
        print "Per product data: \n %r" % ( pd.DataFrame( aggregated, columns = self.ProductName, index = col ).transpose() );

     # This function defines a small instance, this is usefull for debugging.
    def DefineAsSmallIntance(self ):
        self.InstanceName = "SmallIntance"
        self.ProductName = [ "P1", "P2", "P3", "P4", "P5" ]
        self.NrProduct = 5
        self.NrTimeBucket = 7
        self.NrResource = 5
        self.NrScenario = 3
        self.Requirements = [ [ 0, 1, 1, 0, 0 ],
                              [ 0, 0, 0, 1, 0 ],
                              [ 0, 0, 0, 0, 0 ],
                              [  0, 0, 0, 0, 1 ],
                              [ 0, 0, 0, 0, 0 ] ]
        self.Leadtimes = [0, 1, 1, 1, 1]
        self.Demands = [ [ [ 5.0, 10.0 , 15.0 ], [ 5.0, 10.0 , 15.0 ], [ 5.0, 10.0 , 15.0 ], [ 5.0, 10.0 , 15.0 ],
                           [ 5.0, 10.0 , 15.0 ], [ 5.0, 10.0 , 15.0 ], [ 5.0, 10.0 , 15.0 ]],
                         [ [ 0.0, 0.0 , 0.0 ], [ 0.0, 0.0 , 0.0 ], [ 0.0, 0.0 , 0.0 ], [ 0.0, 0.0 , 0.0 ],
                           [ 0.0, 0.0 , 0.0 ], [ 0.0, 0.0 , 0.0 ], [ 0.0, 0.0 , 0.0 ]],
                         [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0],
                          [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]],
                         [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0],
                          [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]],
                         [[0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0], [0.0, 0.0, 0.0],
                          [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]] ]
        self.StartingInventories = [10.0, 100.0, 100.0, 100.0, 100.0]
        self.InventoryCosts = [5.0, 4.0, 3.0, 2.0, 1.0]
        self.SetupCosts = [10000.0, 0.0, 0.0, 0.0, 0.0]
        self.BackorderCosts = [100000.0, 0.0, 0.0, 0.0, 0.0]  # for now assume no external demand for components
        self.CapacityConsumptions = [ [0.01, 0.0, 0.0, 0.0, 0.0],
                                      [0.0, 0.02, 0.0, 0.0, 0.0],
                                      [0.0, 0.0, 0.01, 0.0, 0.0],
                                      [0.0, 0.0, 0.0, 0.01, 0.0],
                                      [0.0, 0.0, 0.0, 0.0, 0.04] ]
        self.ComputeIndices()
        self.ComputeLevel()
        self.ComputeMaxLeadTime( )

     # This function defines a very small instance, this is usefull for debugging.
    def DefineAsSuperSmallIntance(self ):
        # data of a small instance to implement.
        self.InstanceName = "SuperSmallIntance"
        self.ProductName = [ "P1", "P2" ]
        self.NrProduct = 2
        self.NrTimeBucket = 3
        self.NrResource = 2
        self.NrScenario = 3
        self.Requirements = [ [ 0, 1 ],
                              [ 0, 0 ] ]
        self.Leadtimes = [1, 1]
        self.Demands = [ [ [ 5.0, 10.0 , 200.0 ], [ 5.0, 10.0 , 200.0 ], [ 5.0, 10.0 , 200.0 ] ],
                         [ [0.0,0.0 , 0.0 ], [ 0.0, 0.0 , 0.0 ], [ 0.0, 0.0 , 0.0 ] ] ]

        self.StartingInventories = [ 10.0, 10.0 ]
        self.InventoryCosts = [ 10.0, 5.0 ]
        self.SetupCosts = [ 5.0, 5.0 ]
        self.BackorderCosts = [ 10000.0, 0.0 ]  # for now assume no external demand for components
        self.CapacityConsumptions = [ [ 0.0001, 0.0 ],
                                      [ 0.0, 0.002 ] ]
        self.ComputeIndices()
        self.ComputeLevel()
        self.ComputeMaxLeadTime( )

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
        self.Demands = []
        self.Requirements = []
        self.Leadtimes = []
        self.StartingInventories = []
        self.InventoryCosts = []
        self.SetupCosts = []
        self.BackorderCosts = []
        self.CapacityConsumptions = []
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
        self.ProductName = ""
        #Compute some statistic about the instance
        self.MaxLeadTime = -1
        self.NrLevel = -1
        self.Level = [] # The level of each product in the bom
        self.MaxLeadTimeProduct = [] #The maximum leadtime to the component for each product


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

    #Compute the start of index and the number of variables for the considered instance
    def ComputeIndices( self ):
#        self.NrQuantiyPeriod1Variables = self.NrProduct
        self.NrQuantiyVariables = self.NrProduct * self.NrTimeBucket * self.NrScenario
        self.NrInventoryVariable = self.NrProduct * self.NrTimeBucket * self.NrScenario
       # self.NrProductionPeriod1Variable = self.NrProduct
        self.NrProductionVariable = self.NrProduct  *  self.NrTimeBucket  * self.NrScenario
        self.NrBackorderVariable = self.NrProduct * self.NrTimeBucket * self.NrScenario
        #self.StartQuantiyPeriod1Variables = 0
        self.StartQuantityVariable = 0 #self.StartQuantiyPeriod1Variables + self.NrQuantiyVariables;
        self.StartInventoryVariable =  self.StartQuantityVariable + self.NrQuantiyVariables
        #self.StartProdustionPeriod1Variable =  self.StartInventoryVariable +  self.NrInventoryVariable
        self.StartProdustionVariable = self.StartInventoryVariable +  self.NrInventoryVariable# self.StartProdustionPeriod1Variable + self.NrProductionPeriod1Variable
        self.StartBackorderVariable =   self.StartProdustionVariable +  self.NrProductionVariable
        self.ProductSet = range( self.NrProduct )
        self.TimeBucketSet = range( self.NrTimeBucket )
        self.ScenarioSet = range( self.NrScenario )

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
        self.NrResource = 0
        self.CapacityConsumptions =  [  ]
        self.NrProduct = len( self.ProductName )
        self.NrScenario = nrscenario
        self.NrTimeBucket = 0
        self.ComputeIndices()
        #This set of instances assume no setup
        self.SetupCosts = [ 0.0 ] * self.NrProduct
         #Get the average demand, lead time
        self.Leadtimes =  [ int ( math.ceil( datasheetdf.get_value( self.ProductName[ p ], 'stageTime' ) ) ) for p in self.ProductSet ]
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
        self.BackorderCosts = [ 0.1 ] * self.NrProduct
        self.ComputeLevel()
        self.ComputeMaxLeadTime( )
        # Consider a time horizon of 20 days plus the total lead time
        self.NrTimeBucket = self.MaxLeadTime + 20
        self.ComputeIndices()
        # Assume a starting inventory is the average demand during the lead time
        self.StartingInventories = [ datasheetdf.get_value( self.ProductName[p], 'avgDemand')
                                     * self.MaxLeadTimeProduct[p] for p in self.ProductSet]

        self.Demands = [[[datasheetdf.get_value(self.ProductName[p], 'avgDemand') for w in self.ScenarioSet]
                         for t in self.TimeBucketSet]
                        for p in self.ProductSet]
