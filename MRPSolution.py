import pandas as pd
import openpyxl as opxl
from openpyxl.utils.dataframe import dataframe_to_rows
import numpy as np
import itertools as itools
from MRPInstance import MRPInstance

class MRPSolution:


    def PrintToExcel(self):
        workbook = opxl.Workbook();
        ws = workbook.create_sheet( 'Production' )
        for r in dataframe_to_rows( self.Production, index=True, header=True):
            ws.append(r)

        ws = workbook.create_sheet( 'ProductionQuantity' )
        for r in dataframe_to_rows( self.ProductionQuantity, index=True, header=True):
            ws.append(r)

        ws = workbook.create_sheet( 'InventoryLevel' )
        for r in dataframe_to_rows( self.InventoryLevel, index=True, header=True):
            ws.append(r)

        ws = workbook.create_sheet( 'BackOrder' )
        for r in dataframe_to_rows( self.BackOrder, index=True, header=True):
            ws.append(r)

        workbook.save( self.MRPInstance.InstanceName + "_Solution.xlsx" )

    #This function prints a solution
    def Print(self):
        print "production ( cost: %r): \n %r" % ( self.SetupCost , self.Production );
        print "production quantities: \n %r" % self.ProductionQuantity ;
        print "inventory levels at the end of the periods: ( cost: %r ) \n %r" % ( self.InventoryCost, self.InventoryLevel );
        print "backorder quantities:  ( cost: %r ) \n %r" % ( self.BackOrderCost, self.BackOrder );

    #This funciton conpute the different costs (inventory, backorder, setups) associated with the solution.
    def ComputeCost(self):
        inventorycostperproduct =  self.InventoryLevel.transpose().dot( self.MRPInstance.InventoryCosts )
        setupcostperproduct = self.Production.transpose().dot( self.MRPInstance.SetupCosts )
        backordercostperproduct = self.BackOrder.transpose().dot(self.MRPInstance.BackorderCosts )
        self.InventoryCost = inventorycostperproduct.sum();
        self.BackOrderCost = backordercostperproduct.sum();
        self.SetupCost = setupcostperproduct.sum();

    #constructor
    def __init__( self, instance, solquantity, solproduction, solinventory, solbackorder ):
        self.MRPInstance = instance
        self.ProductionQuantity = pd.DataFrame(  solquantity, index = instance.ProductName )
        self.InventoryLevel = pd.DataFrame(  solinventory, index = instance.ProductName )
        self.Production = pd.DataFrame(  solproduction, index = instance.ProductName )
        self.BackOrder = pd.DataFrame(  solbackorder, index = instance.ProductName )
        self.InventoryCost = -1;
        self.BackOrderCost = -1;
        self.SetupCost = -1;
        self.ComputeCost();
