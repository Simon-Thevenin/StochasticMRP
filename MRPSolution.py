import pandas as pd
import openpyxl as opxl
from openpyxl.utils.dataframe import dataframe_to_rows
import numpy as np
import itertools as itools
from MRPInstance import MRPInstance

class MRPSolution:

    #This function print the solution in an Excel file in the folde "Solutions"
    def PrintToExcel(self):


        writer = pd.ExcelWriter("./Solutions/"+self.MRPInstance.InstanceName + "_Solution.xlsx", engine='openpyxl')
        self.ProductionQuantity.to_excel(writer, 'ProductionQuantity')
        self.Production.to_excel(writer, 'Production')
        self.InventoryLevel.to_excel(writer, 'InventoryLevel')
        self.BackOrder.to_excel(writer, 'BackOrder')

        writer.save()

        #workbook.save(  )

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
        self.TotalCost =  self.InventoryCost + self.BackOrderCost +  self.SetupCost

    #constructor
    def __init__( self, instance, solquantity, solproduction, solinventory, solbackorder ):
        self.MRPInstance = instance
        #Create a multi index to store the scenarios and time
        iterables = [ self.MRPInstance.TimeBucketSet, self.MRPInstance.ScenarioSet ]
        multiindex = pd.MultiIndex.from_product(iterables, names=['time', 'scenario'])
        self.ProductionQuantity = pd.DataFrame(  solquantity, index = instance.ProductName, columns = multiindex  )
        self.InventoryLevel = pd.DataFrame(  solinventory, index = instance.ProductName, columns = multiindex )
        self.Production = pd.DataFrame(  solproduction, index = instance.ProductName, columns = multiindex  )
        self.BackOrder = pd.DataFrame(  solbackorder,  index = instance.ProductName, columns = multiindex  )
        self.InventoryCost = -1;
        self.BackOrderCost = -1;
        self.SetupCost = -1;
        self.TotalCost =-1;
        self.ComputeCost();
