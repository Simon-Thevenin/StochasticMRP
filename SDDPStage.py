import cplex
import math
from Constants import Constants


# This class contains the attributes and methodss allowing to define one stage of the SDDP algorithm.
class SDDPStage:

    def __init__(self,
                 owner = None,
                 previousstage = None,
                 nextstage = None,
                 decisionstage = -1 ):

        self.SDDPOwner = owner
        self.PreviousSDDPStage = previousstage
        self.NextSDDPStage = nextstage
        #A Cplex MIP object will be associated to each stage later.
        self.Cplex = cplex.Cplex()
        #The variable MIPDefined is turned to True when the MIP is built
        self.MIPDefined = False
        self.DecisionStage = decisionstage
        self.Instance = self.SDDPOwner.Instance

        #The following attribute will contain the coefficient of hte variable in the cuts
        self.CoefficientConstraint = []
        #The following variable constains the value at which the variables are fixed
        self.VariableFixedTo = []
        #The number of variable of each type in the stage will be set later
        self.NrProductionVariable = 0
        self.NrQuantityVariable = 0
        self.NrStockVariable = 0
        self.NrBackOrderVariable = 0
        self.ComputeNrVariables()
        #The start of the index of each variable
        self.StartProduction = 0
        self.StartQuantity = self.StartProduction + self.NrProductionVariable
        self.StartStock = self.StartQuantity + self.NrQuantityVariable
        self.StartBackOrder = self.StartStock + self.NrStockVariable
        # Demand and materials requirement: set the value of the invetory level and backorder quantity according to
        #  the quantities produced and the demand
        self.M = cplex.infinity
        self.CurrentScenarioNr = -1
        #The quantity to order (filled after having solve the MIPs for all scenario)
        self.QuantityValues = []
        #The value of the production variables (filled after having solve the MIPs for all scenario)
        self.ProductionValue = []
        # The value of the inventory variables (filled after having solve the MIPs for all scenario)
        self.InventoryValue = []
        #The value of the backorder variable (filled after having solve the MIPs for all scenario)
        self.BackorderValue = []

    #This function modify the number of scenario in the stage
    def SetNrScenario(self, nrscenario ):
        self.ScenarioNrSet = range( nrscenario )
        #The quantity to order (filled after having solve the MIPs for all scenario)
        self.QuantityValues = [ [] for w in self.ScenarioNrSet ]
        #The value of the production variables (filled after having solve the MIPs for all scenario)
        self.ProductionValue = [ [] for w in self.ScenarioNrSet ]
        # The value of the inventory variables (filled after having solve the MIPs for all scenario)
        self.InventoryValue = [ [] for w in self.ScenarioNrSet ]
        #The value of the backorder variable (filled after having solve the MIPs for all scenario)
        self.BackorderValue = [ [] for w in self.ScenarioNrSet ]

    #Return true if the current stage is the last
    def IsLastStage(self):
        return self.DecisionStage == self.Instance.NrTimeBucket

    #Return true if the current stage is the first
    def IsFirstStage(self):
        return self.DecisionStage == 0

    #Compute the number of variable of each type (production quantty, setup, inventory, backorder)
    def ComputeNrVariables(self):
        #number of variable at stage 1<t<T
        self.NrBackOrderVariable = len( self.Instance.ProductWithExternalDemand )
        self.NrQuantityVariable = self.Instance.NrProduct
        self.NrStockVariable = self.Instance.NrProduct
        self.NrProductionVariable = 0

        # number of variable at stage 1
        if self.IsFirstStage():
            self.NrProductionVariable = self.Instance.NrTimeBucket * self.Instance.NrProduct
            self.NrBackOrderVariable = 0
            self.NrStockVariable = len( self.Instance.ProductWithoutExternalDemand )

        # number of variable at stage T
        if self.IsLastStage():
            self.NrQuantityVariable = 0
            self.NrStockVariable = len( self.Instance.ProductWithExternalDemand )

    #return the index of the production variable associated with the product p at time t
    def GetIndexProductionVariable(self, p, t):
        if self.IsFirstStage() :
            return self.StartProduction + p*self.Instance.NrTimeBucket + t
        else :
            raise ValueError('Production variables are only defined at stage 0')

    #Return the index of the variable associated with the quanity of product p decided at the current stage
    def GetIndexQuantityVariable(self, p ):
        return self.StartQuantity + p

    #Return the index of the variable associated with the stock of product p decided at the current stage
    def GetIndexStockVariable(self, p ):
        if self.IsLastStage() :
            return self.StartStock + self.Instance.ProductWithExternalDemandIndex[ p ]
        elif self.IsFirstStage() :
            return self.StartStock + self.Instance.ProductWithoutExternalDemandIndex[ p ]
        else :
           return self.StartStock + p

    #Return the index of the variable associated with the stock of product p decided at the current stage
    def GetIndexBackorderVariable(self, p ):
        if self.IsFirstStage() :
            raise ValueError('Backorder variables are not defined at stage 0')
        else :
            return self.StartBackOrder + self.Instance.ProductWithExternalDemandIndex[p]

    #Return the name of the variable associated with the setup of product p at time t
    def GetNameProductionVariable(self, p, t):
        if self.IsFirstStage():
            return "Y_%d_%d"%(p, t )
        else:
            raise ValueError('Production variables are only defined at stage 0')

    # Return the name of the variable associated with the quanity of product p decided at the current stage
    def GetNameQuantityVariable(self, p):
        time = self.GetTimePeriodAssociatedToQuantityVariable( p )
        return "Q_%d_%d"%(p, time )

    # Return the name of the variable associated with the stock of product p decided at the current stage
    def GetNameStockVariable(self, p):
        time = self.GetTimePeriodAssociatedToInventoryVariable( p )
        return "I_%d_%d"%(p, time)

    # Return the name of the variable associated with the backorder of product p decided at the current stage
    def GetNameBackorderVariable(self, p):
         time = self.GetTimePeriodAssociatedToBackorderVariable( p )
         return "B_%d_%d" % (p, time)

    # Return the time period associated with quanity of product p decided at the current stage
    def GetTimePeriodAssociatedToQuantityVariable( self, p ):
        result = self.DecisionStage
        return result

    # Return the time period associated with inventory of product p decided at the current stage (the inventory level of component,  at time t is observed at stage t -1 because it is not stochastic)
    def GetTimePeriodAssociatedToInventoryVariable( self, p ):
        result = self.DecisionStage
        if self.Instance.HasExternalDemand[p]:
            result = self.DecisionStage -1

        return result

    # Return the time period associated with backorder of product p decided at the current stage
    def GetTimePeriodAssociatedToBackorderVariable( self, p ):
        result = self.DecisionStage - 1
        if not self.Instance.HasExternalDemand[p]:
            raise ValueError('Backorder variables are not defined for component')
        return result

    def CreateFlowConstraints(self):
        self.FlowConstraintNR = [""  for p in self.Instance.ProductSet]

        for p in self.Instance.ProductSet:
            if  not (  ( self.IsFirstStage()  and  self.Instance.HasExternalDemand[p] )  or  (  self.IsLastStage()  and ( not   self.Instance.HasExternalDemand[p] ) ) ) :
                backordervar = []
                inventoryvar = []
                quantityvar = []
                dependentdemandvar = []
                dependentdemandvarcoeff = []
                righthandside = [-1 * self.Instance.StartingInventories[p]]
                if self.Instance.HasExternalDemand[p] and not self.IsFirstStage():
                     righthandside[0] = righthandside[0] \
                                        + self.SDDPOwner.CurrentSetOfScenarios[ self.CurrentScenarioNr ].Demands[self.GetTimePeriodAssociatedToInventoryVariable(p)][p] \
                                        + self.SDDPOwner.GetBackorderFixedEarlier( p, self.GetTimePeriodAssociatedToInventoryVariable(p) - 1, self.CurrentScenarioNr )

                     backordervar = [ self.GetIndexBackorderVariable(p) ]

                else:
                     dependentdemandvar = [self.GetIndexQuantityVariable(q) for q in  self.Instance.RequieredProduct[p] ]
                     dependentdemandvarcoeff =  [-1 * self.Instance.Requirements[q][p] for q in self.Instance.RequieredProduct[p]]


                productionstartedtime = self.GetTimePeriodAssociatedToQuantityVariable(p) - self.Instance.Leadtimes[p]
                if productionstartedtime -1 >= 0:
                    righthandside[0] = righthandside[0] \
                                       - self.SDDPOwner.GetQuantityFixedEarlier(p,  productionstartedtime, self.CurrentScenarioNr)

                if self.GetTimePeriodAssociatedToInventoryVariable(p) - 1 >= 0:
                    righthandside[0] = righthandside[0] \
                                        - self.SDDPOwner.GetInventoryFixedEarlier(p, self.GetTimePeriodAssociatedToInventoryVariable(p) - 1, self.CurrentScenarioNr)

                inventoryvar = [self.GetIndexStockVariable(p)]

                vars = inventoryvar + backordervar + dependentdemandvar
                coeff = [-1] * len(inventoryvar) \
                        + [1] * len(backordervar) \
                        + dependentdemandvarcoeff

                if len(vars) > 0:
                       self.Cplex.linear_constraints.add(lin_expr=[cplex.SparsePair(vars, coeff)],
                                                           senses=["E"],
                                                           rhs=righthandside,
                                                           names=["Flow%d" %(p)])
                       self.FlowConstraintNR[p] = "Flow%d" % (p)

    # Return the set of products which are associated with stock decisions at the current stage
    def GetProductWithStockVariable(self):
        result = self.Instance.ProductSet
        # At the first stage, only the components are associated with a stock variable
        if self.IsFirstStage():
            result = self.Instance.ProductWithoutExternalDemand
        #At the last stage only the finish product have inventory variable
        if self.IsLastStage():
            result = self.Instance.ProductWithExternalDemand
        return result

    # Return the set of products which are associated with backorder decisions at the current stage
    def GetProductWithBackOrderVariable(self):
        result = []
        # At each stage except the first, the finsih product are associated with a backorders variable
        if not self.IsFirstStage():
            result = self.Instance.ProductWithExternalDemand
        return result

    # This function creates the  indicator constraint to se the production variable to 1 when a positive quantity is produce
    def CreateProductionConstraints(self):
       # AlreadyAdded = [[False for v in range(self.GetNrQuantityVariable())] for w in
       #                 r ange(self.GetNrProductionVariable()) ]

        for p in self.Instance.ProductSet:
            if self.IsFirstStage():
                vars = [  self.GetIndexQuantityVariable( p ) , self.GetIndexProductionVariable( p, self.GetTimePeriodAssociatedToQuantityVariable( p ) ) ]
                coeff = [-1.0, self.GetBigMValue(p)]
                righthandside = [0.0]
                # PrintConstraint( vars, coeff, righthandside )
                self.Cplex.linear_constraints.add( lin_expr=[cplex.SparsePair(vars, coeff)],
                                                    senses=["G"],
                                                    rhs=righthandside)

            else:
                if not self.IsLastStage():
                    yvalue =  self.SDDPOwner.GetSetupFixedEarlier( p,  self.GetTimePeriodAssociatedToQuantityVariable( p ), self.CurrentScenarioNr)
                    vars = [ self.GetIndexQuantityVariable(p) ]
                    coeff = [1.0]
                    righthandside = [  self.GetBigMValue(p) * yvalue]
                    # PrintConstraint( vars, coeff, righthandside )
                    self.Cplex.linear_constraints.add(lin_expr=[cplex.SparsePair(vars, coeff)],
                                                         senses=["L"],
                                                         rhs=righthandside)
                        # This function creates the Capacity constraint

    def CreateCapacityConstraints(self):
        # Capacity constraint
        if self.Instance.NrResource > 0  and not self.IsLastStage():
            for k in range(self.Instance.NrResource):
               vars = [self.GetIndexQuantityVariable(p) for p in self.Instance.ProductSet]
               coeff = [self.Instance.ProcessingTime[p][k] for p in self.Instance.ProductSet]
               righthandside = [self.Instance.Capacity[k]]
               self.Cplex.linear_constraints.add(lin_expr=[cplex.SparsePair(vars, coeff)],
                                                  senses=["L"],
                                                  rhs=righthandside)

    #Define the variables
    def DefineVariables( self ):
        #The setups are decided at the first stage
        if self.IsFirstStage():
            self.Cplex.variables.add( obj = [ math.pow( self.Instance.Gamma, self.DecisionStage )
                                              * self.Instance.SetupCosts[p]
                                                for p in self.Instance.ProductSet
                                                for t in self.Instance.TimeBucketSet],
                                            types=['B'] * self.NrProductionVariable )

        #Variable for the production quanitity
        self.Cplex.variables.add( obj = [0.0] * self.NrQuantityVariable,
                                  lb = [0.0] * self.NrQuantityVariable,
                                  ub = [self.M] * self.NrQuantityVariable )

        productwithstockvariable = self.GetProductWithStockVariable()

        #Variable for the inventory
        self.Cplex.variables.add( obj = [ math.pow( self.Instance.Gamma, self.DecisionStage-1 )
                                          * self.Instance.InventoryCosts[p]
                                          if self.Instance.HasExternalDemand[p] else
                                          math.pow(self.Instance.Gamma, self.DecisionStage )
                                          * self.Instance.InventoryCosts[p]
                                          for p in productwithstockvariable ],
                                  lb = [0.0] * self.NrStockVariable,
                                  ub = [self.M] * self.NrStockVariable )

        # Backorder/lostsales variables
        productwithbackorder= self.GetProductWithBackOrderVariable()
        self.Cplex.variables.add( obj = [math.pow( self.Instance.Gamma, self.DecisionStage - 1) * self.Instance.BackorderCosts[  p ]
                                             if not self.IsLastStage()
                                             else math.pow( self.Instance.Gamma, self.DecisionStage -1 ) * self.Instance.LostSaleCost[  p ]
                                             for p in productwithbackorder],
                                      lb = [0.0] * self.NrBackOrderVariable,
                                      ub = [self.M] * self.NrBackOrderVariable )

        #In debug mode, the variables have names
        if Constants.Debug:
            self.AddVariableName()

    #Add the name of each variable
    def AddVariableName(self):
        print "Add the names of the variable"
        # Define the variable name.
        # Usefull for debuging purpose. Otherwise, disable it, it is time consuming.
        if Constants.Debug:
            quantityvars = []
            inventoryvars = []
            productionvars = []
            backordervars = []
            if self.IsFirstStage():
                for p in self.Instance.ProductSet:
                    for t in self.Instance.TimeBucketSet:
                        productionvars.append( ( self.GetIndexProductionVariable(p, t), self.GetNameProductionVariable(p, t) ) )

            productwithstockvariable = self.GetProductWithStockVariable()
            for p in productwithstockvariable:
                inventoryvars.append( ( self.GetIndexStockVariable(p), self.GetNameStockVariable( p ) ) )

            for p in self.GetProductWithBackOrderVariable():
                backordervars.append( (self.GetIndexBackorderVariable(p), self.GetNameBackorderVariable(p) ) )

            if not self.IsLastStage():
                for p in self.Instance.ProductSet:
                    quantityvars.append( ( self.GetIndexQuantityVariable(p), self.GetNameQuantityVariable(p) ) )


            quantityvars = list( set( quantityvars ) )
            productionvars = list( set( productionvars ) )
            inventoryvars = list( set( inventoryvars ) )
            backordervars = list( set( backordervars ) )
            varnames = quantityvars + inventoryvars + productionvars + backordervars
            self.Cplex.variables.set_names(varnames)

    #Create the MIP
    def DefineMIP( self ):
        if Constants.Debug:
            print "Define the MIP of stage %d" % self.DecisionStage

        self.DefineVariables()

        self.CreateProductionConstraints()
        self.CreateFlowConstraints()
        self.CreateCapacityConstraints()
        self.MIPDefined = True

    #The function below update the constraint of the MIP to correspond to the new scenario
    def UpdateMIPForScenario( self, scenarionr ):
        self.CurrentScenarioNr  = scenarionr
        print "TBD "



    #This run the MIP of the current stage (one for each scenario)
    def RunForwardPassMIP( self ):
        if Constants.Debug:
            print "build the MIP of stage %d" %self.DecisionStage

        if not self.MIPDefined:
            self.DefineMIP()

        for w in range( len( self.SDDPOwner.CurrentSetOfScenarios ) ):
            self.UpdateMIPForScenario( w )
            if Constants.Debug:
                print "Update the MIP of stage %d for scenario %d" %( self.DecisionStage, w )
                self.Cplex.write("stage_%d_iter_%d_scenar_%d.lp" % (self.DecisionStage, self.SDDPOwner.CurrentIteration, w))
            sol = self.Cplex.solve()
            self.SaveSolutionForScenario( sol )

    # This function run the MIP of the current stage
    def SaveSolutionForScenario(self, sol):

        sol = self.Cplex.solution
        if sol.is_primal_feasible():
            if Constants.Debug:
                sol.write("mrpsolution.sol")

            objvalue = sol.get_objective_value()
            if not self.IsLastStage():
                indexarray = [ self.GetIndexQuantityVariable(p) for p in self.Instance.ProductSet ]
                self.QuantityValues[self.CurrentScenarioNr] = sol.get_values( indexarray )

            if self.IsFirstStage():
                indexarray = [self.GetIndexProductionVariable(p, t)  for p in self.Instance.ProductSet for t in self.Instance.TimeBucketSet ]
                self.ProductionValue[self.CurrentScenarioNr] = sol.get_values( indexarray )

            indexarray = [self.GetIndexStockVariable(p) for p in self.GetProductWithStockVariable() ]
            self.InventoryValue[ self.CurrentScenarioNr ] = sol.get_values( indexarray )

            if not self.IsFirstStage():
                indexarray = [self.GetIndexBackorderVariable(p) for p in self.GetProductWithBackOrderVariable() ]
                self.BackorderValue[ self.CurrentScenarioNr ] = sol.get_values( indexarray )



     #Generate the bender cut
    def GernerateCut( self ):
        if Constants.Debug:
            print "Generate a cut to add at stage %d" % self.PreviousSDDPStage.DecisionStage

    def GetBigMValue( self, p ):
        print "TBD"
        result = 999999999
        return result