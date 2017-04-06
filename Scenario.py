import pandas as pd

class Scenario:

    NrScenario = 0

    def __init__( self, owner = None, demand = None, proabability = -1, quantityvariable = None,  productionvariable = None,  inventoryvariable = None,  backordervariable = None ):
        self.Owner = owner
        # The  demand in the scenario for each time period
        self.Demands= demand
        # The probability of the partial scenario
        self.Probability = proabability
        # The attribute below contains the index of the CPLEX variables (quanity, production, invenotry) for each product and time.
        self.QuanitityVariable = quantityvariable
        self.ProductionVariable = productionvariable
        self.InventoryVariable = inventoryvariable
        self.BackOrderVariable = backordervariable
        Scenario.NrScenario = Scenario.NrScenario +1
        self.ScenarioId =  Scenario.NrScenario

    def DisplayScenario( self ):
        print "Scenario %d" %self.ScenarioId
        print "Demand of scenario( %d ): %r" %( self.ScenarioId, self.Demands )
        print "Probability of scenario( %d ): %r" %( self.ScenarioId, self.Probability )
        print "Quantity variable of scenario( %d ): %r" % ( self.ScenarioId, self.QuanitityVariable )
        print "Production variable of scenario( %d ): %r" % ( self.ScenarioId, self.ProductionVariable )
        print "Inventory variable of scenario( %d ): %r" % ( self.ScenarioId, self.InventoryVariable )
        print "BackOrder variable of scenario( %d ): %r" % ( self.ScenarioId, self.BackOrderVariable )

    # This function print the scenario in an Excel file in the folde "Solutions"
    def PrintScenarioToExcel(self, writer):
        print self.Demands
        demanddf = pd.DataFrame(self.Demands, columns = self.Owner.ProductName,  index = self.Owner.TimeBucketSet)
        demanddf.to_excel( writer, "DemandScenario %d" %self.ScenarioId )
        quantitydf = pd.DataFrame(self.QuanitityVariable, columns = self.Owner.ProductName, index = self.Owner.TimeBucketSet)
        quantitydf.to_excel( writer, "QuanitityVariable %d" %self.ScenarioId )
        productiondf = pd.DataFrame(self.ProductionVariable, columns = self.Owner.ProductName, index = self.Owner.TimeBucketSet)
        productiondf.to_excel( writer, "ProductionVariable %d" % self.ScenarioId )
        inventorydf = pd.DataFrame(self.InventoryVariable, columns = self.Owner.ProductName, index = self.Owner.TimeBucketSet)
        inventorydf.to_excel( writer, "InventoryVariable %d" % self.ScenarioId )
        bbackorderydf = pd.DataFrame(self.BackOrderVariable, columns = self.Owner.ProductName, index = self.Owner.TimeBucketSet)
        bbackorderydf.to_excel( writer, "BackOrderVariable %d" % self.ScenarioId )
