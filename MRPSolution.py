import pandas as pd
import openpyxl as opxl
from openpyxl.utils.dataframe import dataframe_to_rows
import numpy as np
import itertools as itools
from MRPInstance import MRPInstance
import math

class MRPSolution:

    #This function print the solution in an Excel file in the folde "Solutions"
    def PrintToExcel(self, description):
        writer = pd.ExcelWriter("./Solutions/"+ self.MRPInstance.InstanceName + "_" + description + "_Solution.xlsx", engine='openpyxl')
        self.ProductionQuantity.to_excel(writer, 'ProductionQuantity')
        self.Production.to_excel(writer, 'Production')
        self.InventoryLevel.to_excel(writer, 'InventoryLevel')
        self.BackOrder.to_excel(writer, 'BackOrder')
        writer.save()

    #This function prints a solution
    def Print(self):
        print "production ( cost: %r): \n %r" % ( self.SetupCost , self.Production );
        print "production quantities: \n %r" % self.ProductionQuantity ;
        print "inventory levels at the end of the periods: ( cost: %r ) \n %r" % ( self.InventoryCost, self.InventoryLevel );
        print "backorder quantities:  ( cost: %r ) \n %r" % ( self.BackOrderCost, self.BackOrder );

    #This funciton conpute the different costs (inventory, backorder, setups) associated with the solution.
    def ComputeCost(self):
        #multiply by inventory cost per product -> get a vector with cost per time unit and scenario
        print self.Production.transpose()
        inventorycostpertimeandscenar =  self.InventoryLevel.transpose().dot( self.MRPInstance.InventoryCosts )
        setupcostpertimeandscenar = self.Production.transpose().dot( self.MRPInstance.SetupCosts )
        backordercostpertimeandscenar = self.BackOrder.transpose().dot(self.MRPInstance.BackorderCosts )
        print setupcostpertimeandscenar

        #Reshap the vector to get matirces
        inventorycostpertimeandscenar = inventorycostpertimeandscenar.reshape( self.MRPInstance.NrTimeBucket, self.MRPInstance.NrScenario );
        setupcostpertimeandscenar = setupcostpertimeandscenar.reshape( self.MRPInstance.NrTimeBucket, self.MRPInstance.NrScenario );
        backordercostpertimeandscenar = backordercostpertimeandscenar.reshape( self.MRPInstance.NrTimeBucket, self.MRPInstance.NrScenario );
        print setupcostpertimeandscenar

        #multiply by the probability of each scenatio
        proabailities = [ s.Probability for s in self.MRPInstance.Scenarios  ]
        inventorycostpertime = inventorycostpertimeandscenar.dot( proabailities )
        setupcostpertime = setupcostpertimeandscenar.dot( proabailities )
        backordercostpertime = backordercostpertimeandscenar.dot( proabailities )
        print setupcostpertime
        print 'Now the gamma!!!'
        gammas = [ math.pow(self.MRPInstance.Gamma, t) for t in self.MRPInstance.TimeBucketSet]
        netpresentvalueinventorycostpertime = inventorycostpertime.transpose().dot( gammas )
        netpresentvaluesetupcostpertime = setupcostpertime.transpose().dot(gammas)
        netpresentvaluebackordercostpertime = backordercostpertime.transpose().dot(gammas)
        print netpresentvaluesetupcostpertime

        self.InventoryCost = netpresentvalueinventorycostpertime
        self.BackOrderCost = netpresentvaluebackordercostpertime
        self.SetupCost = netpresentvaluesetupcostpertime
        print 'Thae seem rith:%d!!!'%self.SetupCost
        self.TotalCost =  self.InventoryCost + self.BackOrderCost +  self.SetupCost
        print self.SetupCost

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
