import pandas as pd
import openpyxl as opxl
import itertools as itools
import math

class MRPInstance:

    FileName = "../Instance/MSOM-06-038-R2.xls"


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

    def DefineAsSmallIntance(self ):
        # data of a small instance to implement.
        self.InstanceName = "SmallIntance"
        self.ProductName = [ "P1", "P2", "P3", "P4", "P5" ]
        self.NrProduct = 5
        self.NrTimeBucket = 7
        self.NrResource = 5
        self.Requirements = [ [ 0, 1, 1, 0, 0 ],
                              [ 0, 0, 0, 1, 0 ],
                              [ 0, 0, 0, 0, 0 ],
                              [  0, 0, 0, 0, 1 ],
                              [ 0, 0, 0, 0, 0 ] ]
        self.Leadtimes = [0, 1, 1, 1, 1]
        self.Demands = [ [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0],
                         [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                         [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                         [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0],
                         [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0] ]

        self.StartingInventories = [10.0, 100.0, 100.0, 100.0, 100.0]
        self.InventoryCosts = [5.0, 4.0, 3.0, 2.0, 1.0]
        self.SetupCosts = [10000.0, 0.0, 0.0, 0.0, 0.0]
        self.BackorderCosts = [100000.0, 0.0, 0.0, 0.0, 0.0]  # for now assume no external demand for components
        self.CapacityConsumptions = [ [0.01, 0.0, 0.0, 0.0, 0.0],
                                      [0.0, 0.02, 0.0, 0.0, 0.0],
                                      [0.0, 0.0, 0.01, 0.0, 0.0],
                                      [0.0, 0.0, 0.0, 0.01, 0.0],
                                      [0.0, 0.0, 0.0, 0.0, 0.04] ]

    def DefineAsSuperSmallIntance(self ):
        # data of a small instance to implement.
        self.InstanceName = "SuperSmallIntance"
        self.ProductName = [ "P1", "P2" ]
        self.NrProduct = 2
        self.NrTimeBucket = 3
        self.NrResource = 2
        self.Requirements = [ [ 0, 1 ],
                              [ 0, 0 ] ]
        self.Leadtimes = [0, 1]
        self.Demands = [ [10.0, 10.0, 10.0 ],
                         [0.0, 0.0, 0.0 ] ]

        self.StartingInventories = [ 10.0, 10.0 ]
        self.InventoryCosts = [ 10.0, 5.0 ]
        self.SetupCosts = [ 5.0, 5.0 ]
        self.BackorderCosts = [ 100.0, 0.0 ]  # for now assume no external demand for components
        self.CapacityConsumptions = [ [ 0.1, 0.0 ],
                                      [ 0.0, 0.2 ] ]

    def __init__( self ):
        self.InstanceName = ""
        self.NrProduct = -1
        self.NrTimeBucket = -1
        self.NrResource = -1
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


    #Compute the start of index and the number of variables for the considered instance
    def ComputeIndices( self ):
        self.NrQuantiyVariables = self.NrProduct * self.NrTimeBucket
        self.NrInventoryVariable = self.NrProduct * ( self.NrTimeBucket )
        self.NrProductionVariable = self.NrProduct * self.NrTimeBucket
        self.NrBackorderVariable = self.NrProduct * self.NrTimeBucket
        self.StartQuantityVariable = 0
        self.StartInventoryVariable =  self.NrQuantiyVariables
        self.StartProdustionVariable =  self.StartInventoryVariable +  self.NrInventoryVariable
        self.StartBackorderVariable =   self.StartProdustionVariable +  self.NrProductionVariable


    def ReadDataFrame( self, wb2, framename ):
        sheet = wb2[framename];
        data =  sheet.values
        cols = next( data ) [ 1: ]
        data = list( data )
        idx = [ r[ 0 ] for r in data ]
        data = ( itools.islice(r, 1, None ) for r in data )
        df = pd.DataFrame( data, index=idx, columns=cols )
        return df;

    #Compute the start of index and the number of variables for the considered instance
    def ReadFromFile( self, instancename ):
        wb2 = opxl.load_workbook( "../Instances/MSOM-06-038-R2.xlsx" )

        supplychaindf = self.ReadDataFrame( wb2, instancename + "_LL" )
        datasheetdf = self.ReadDataFrame( wb2, instancename + "_SD" )

        self.ProductName = list( datasheetdf.index.values )

        self.InstanceName = instancename
        self.NrResource = 0
        self.CapacityConsumptions =  [  ]
        self.NrProduct = len( self.ProductName )
        self.NrTimeBucket = 200
        self.SetupCosts = [ 0 ] *  self.NrProduct
        datasheetdf = datasheetdf.fillna( 0 )

        self.Demands = [ [ datasheetdf.get_value( self.ProductName[ p ], 'avgDemand' ) ] * self.NrTimeBucket   for p in range( self.NrProduct )  ]
        self.Leadtimes =  [  int ( math.ceil( datasheetdf.get_value( self.ProductName[ p ], 'stageTime' )  ) ) for p in range( self.NrProduct )  ]
        holdingcost = 0.1
        addedvalueatstage = [ datasheetdf.get_value( self.ProductName[ p ], 'stageCost' ) for p in range( self.NrProduct )  ]

        level = [ datasheetdf.get_value( self.ProductName[ p ], 'relDepth' ) for p in range( self.NrProduct )  ]
        levelset = sorted( set( level ), reverse=True )

        self.Requirements = [ [ 0 ] * self.NrProduct  for _ in range( self.NrProduct ) ]
        self.InventoryCosts = [ 0.0 ] * self.NrProduct
        for i, row in supplychaindf.iterrows() :
            self.Requirements[ self.ProductName.index( row.get_value('destinationStage') ) ][ self.ProductName.index( i ) ]  = 1


        for l in levelset:
            prodinlevel =  [ p for p in range( self.NrProduct ) if level[p] == l ]
            for p in prodinlevel:
                print "product: %r" % p
                addedvalueatstage[p] = sum(addedvalueatstage[ q ] * self.Requirements[p][q] for q in range( self.NrProduct ) ) + \
                                            addedvalueatstage[ p ]
                self.InventoryCosts[p] = holdingcost *  addedvalueatstage[ p ]

        self.StartingInventories = [ 0 ] * self.NrProduct
        self.BackorderCosts = [ 0.1 ] * self.NrProduct