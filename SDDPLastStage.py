import cplex
import math
from Constants import Constants
from SDDPCut import SDDPCut
from SDDPStage import SDDPStage
import numpy as np

# This class contains the attributes and methodss allowing to define one stage of the SDDP algorithm.
class SDDPLastStage( SDDPStage ):
    def rescaletimestock(self, t, p):

        result = t - self.GetStartStageTimeRangeStock( p )
        return result

    def rescaletimequantity(self, t):
        result = t -  ( self.Instance.NrTimeBucket - self.Instance.NrTimeBucketWithoutUncertainty  )
        return result

    def GetLastStageTimeRangeQuantity( self ):
       result = range( self.GetStartStageTimeRangeQuantity() ,  self.Instance.NrTimeBucket  )
       return result

    def GetLastStageTimeRangeStock( self, p ):
        if self.Instance.HasExternalDemand[p]:
            result = range( self.Instance.NrTimeBucket - self.Instance.NrTimeBucketWithoutUncertainty -1 ,  self.Instance.NrTimeBucket  )
        else:
            result = range(self.Instance.NrTimeBucket - self.Instance.NrTimeBucketWithoutUncertainty,
                           self.Instance.NrTimeBucket )
        return result

    def GetNrStageStock(self, p):
        if self.Instance.HasExternalDemand[p]:
            result = self.Instance.NrTimeBucketWithoutUncertainty +1
        else:
            result =  self.Instance.NrTimeBucketWithoutUncertainty
        return result

    def GetNrStageQuantity(self):
        result = self.Instance.NrTimeBucketWithoutUncertainty
        return result

    #The last stage has multiple inventory variable (for all time period without uncertainty) return the earliest time period with invenotry variabele
    def GetStartStageTimeRangeStock(self, p):
        if self.Instance.HasExternalDemand[p]:
            result = (self.Instance.NrTimeBucket - self.Instance.NrTimeBucketWithoutUncertainty - 1)
        else:
            result =  (self.Instance.NrTimeBucket - self.Instance.NrTimeBucketWithoutUncertainty)
        return result


    def GetStartStageTimeRangeQuantity(self):
        result =  self.Instance.NrTimeBucket - self.Instance.NrTimeBucketWithoutUncertainty
        return result

    #Compute the number of variable of each type (production quantty, setup, inventory, backorder)
    def ComputeNrVariables( self ):
        #number of variable at stage 1<t<T
        self.NrQuantityVariable = self.Instance.NrProduct  * self.Instance.NrTimeBucketWithoutUncertainty
        self.NrStockVariable = sum( self.GetNrStageStock(q) for q in self.Instance.ProductSet )
        self.NrBackOrderVariable =  sum( self.GetNrStageStock(q) for q in self.Instance.ProductWithExternalDemand )
        self.NrProductionVariable = 0

    def GetIndexBackorderVariable( self, p, t ):
        indexp = self.Instance.ProductWithExternalDemandIndex[p]
        return self.StartBackOrder + indexp *  self.GetNrStageStock(p) + self.rescaletimestock(t, p)

     # Return the index of the variable associated with the quanity of product p decided at the current stage
    def GetIndexQuantityVariable( self, p, t ):
        return self.StartQuantity + p * self.Instance.NrTimeBucketWithoutUncertainty + self.rescaletimequantity(t)

    # Return the index of the variable associated with the stock of product p decided at the current stage
    def GetIndexStockVariable( self, p, t ):
        result = sum(self.GetNrStageStock(q) for q in range(0, p))
        result = self.StartStock + result + self.rescaletimestock(t, p)
        return result


    # Return the name of the variable associated with the quanity of product p decided at the current stage
    def GetNameQuantityVariable(self, p, t):
        return "Q_%d_%d"%(p, t )

    # Return the name of the variable associated with the stock of product p decided at the current stage
    def GetNameStockVariable(self, p, t):
        return "I_%d_%d"%(p, t)

    # Return the name of the variable associated with the backorder of product p decided at the current stage
    def GetNameBackorderVariable(self, p, t):
         return "B_%d_%d" % (p, t)


 #Define the variables
    def DefineVariables( self ):

        #Variable for the production quanitity
        self.Cplex.variables.add( obj = [0.0] * self.NrQuantityVariable,
                                  lb = [0.0] * self.NrQuantityVariable,
                                  ub = [self.M] * self.NrQuantityVariable )


        #Variable for the inventory
        self.Cplex.variables.add( obj = [ math.pow( self.Instance.Gamma, t )
                                          * self.Instance.InventoryCosts[p]
                                          for p in self.Instance.ProductSet
                                          for t in self.GetLastStageTimeRangeStock(p) ],
                                  lb = [0.0] * self.NrStockVariable,
                                  ub = [self.M] * self.NrStockVariable )

        # Backorder/lostsales variables
        backordertime  =   self.GetLastStageTimeRangeStock(p)
        backordertime.pop()

        backordercost = [ math.pow( self.Instance.Gamma, t) * self.Instance.BackorderCosts[ p ]
                          if  t < self.Instance.NrTimeBucket -1
                          else math.pow( self.Instance.Gamma, t ) * self.Instance.LostSaleCost[ p ]
                                         for p in self.Instance.ProductWithExternalDemand
                                         for t in  self.GetLastStageTimeRangeStock(p)]

        self.Cplex.variables.add( obj = backordercost,
                                      lb = [0.0] * self.NrBackOrderVariable,
                                      ub = [self.M] * self.NrBackOrderVariable )

          #In debug mode, the variables have names
        if Constants.Debug:
            self.AddVariableName()

            # Add the name of each variable

    def IsLastStage(self):
        return True

    def IsFirstStage(self):
        return False

    def AddVariableName(self):
        if Constants.Debug:
            print "Add the names of the variable"
        # Define the variable name.
        # Usefull for debuging purpose. Otherwise, disable it, it is time consuming.
        if Constants.Debug:
            quantityvars = []
            inventoryvars = []
            backordervars = []

            for t in self.GetLastStageTimeRangeQuantity():
                for p in self.Instance.ProductSet:
                    quantityvars.append((self.GetIndexQuantityVariable(p, t), self.GetNameQuantityVariable(p, t)))


            for p in self.Instance.ProductWithExternalDemand:
                for t in self.GetLastStageTimeRangeStock(p):
                    backordervars.append((self.GetIndexBackorderVariable(p,t), self.GetNameBackorderVariable(p,t)))

            for p in self.Instance.ProductSet:
                for t in self.GetLastStageTimeRangeStock(p):
                    inventoryvars.append((self.GetIndexStockVariable(p, t), self.GetNameStockVariable(p, t)))

            quantityvars = list(set(quantityvars))
            inventoryvars = list(set(inventoryvars))
            backordervars = list(set(backordervars))
            varnames = quantityvars + inventoryvars  + backordervars
            self.Cplex.variables.set_names(varnames)


    #This function returns the right hand side of the production consraint associated with product p
    def GetProductionConstrainRHS(self, p, t):
        yvalue = self.SDDPOwner.GetSetupFixedEarlier(p, t, self.CurrentScenarioNr)
        righthandside = self.GetBigMValue(p) * yvalue

        return righthandside

    def CreateProductionConstraints(self):
        for p in self.Instance.ProductSet:
            for t in self.GetLastStageTimeRangeQuantity():
                righthandside = [ self.GetProductionConstrainRHS(p,t) ]

                vars = [self.GetIndexQuantityVariable(p, t)]
                coeff = [1.0]
                # PrintConstraint( vars, coeff, righthandside )
                self.Cplex.linear_constraints.add(lin_expr=[cplex.SparsePair(vars, coeff)],
                                                      senses=["L"],
                                                      rhs=righthandside,
                                                      names= ["Prodp%dt%d"%(p,t)])

                self.IndexProductionQuantityConstraint.append(self.LastAddedConstraintIndex)
                self.LastAddedConstraintIndex = self.LastAddedConstraintIndex + 1
                self.ConcernedProductProductionQuantityConstraint.append(p)
                self.ConcernedTimeProductionQuantityConstraint.append(t)

    def CreateCapacityConstraints(self):
        # Capacity constraint
        if self.Instance.NrResource > 0:
            for t in self.GetLastStageTimeRangeQuantity():
                for k in range(self.Instance.NrResource):
                    vars = [self.GetIndexQuantityVariable(p, t) for p in self.Instance.ProductSet]
                    coeff = [self.Instance.ProcessingTime[p][k] for p in self.Instance.ProductSet]
                    righthandside = [self.Instance.Capacity[k]]
                    self.Cplex.linear_constraints.add(lin_expr=[cplex.SparsePair(vars, coeff)],
                                                      senses=["L"],
                                                      rhs=righthandside,
                                                      names= ["Capt%dk%d"%(t,k)])

                    self.IndexCapacityConstraint.append(self.LastAddedConstraintIndex)
                    self.LastAddedConstraintIndex = self.LastAddedConstraintIndex + 1

                    self.ConcernedResourceCapacityConstraint.append(k)



    def GetVariableValue(self, sol):

        indexarray = [self.GetIndexQuantityVariable(p,t) for t in self.GetLastStageTimeRangeQuantity() for p in self.Instance.ProductSet]
        self.QuantityValues[self.CurrentScenarioNr] = sol.get_values(indexarray)
        self.QuantityValues[self.CurrentScenarioNr] = np.array(self.QuantityValues[self.CurrentScenarioNr] , np.float64).reshape(
                                                                 ( self.GetNrStageQuantity(), self.Instance.NrProduct, )).tolist()

        indexarray = [self.GetIndexStockVariable(p,t)  for p in self.Instance.ProductSet for t in self.GetLastStageTimeRangeStock(p ) ]
        inventory = sol.get_values(indexarray)

        indexarray = [self.GetIndexBackorderVariable(p,t)  for p in self.Instance.ProductSet for t in self.GetLastStageTimeRangeStock(p ) ]
        backorder = sol.get_values(indexarray)

        self.InventoryValue[self.CurrentScenarioNr] = [['nan' for p in self.Instance.ProductSet] for t in self.Instance.TimeBucketSet]
        self.BackorderValue[self.CurrentScenarioNr] = [['nan' for p in self.Instance.ProductSet] for t in self.Instance.TimeBucketSet]
        for p in self.Instance.ProductSet:
            for t in self.GetLastStageTimeRangeStock(p):
                indexi = sum( self.GetNrStageStock(q) for q in range(p) ) + self.rescaletimestock(t,p)
                self.InventoryValue[self.CurrentScenarioNr][t][p] = inventory[indexi]

                if self.Instance.HasExternalDemand[p]:
                    indexb = sum(self.GetNrStageStock(q) for q in range(p) if self.Instance.HasExternalDemand[p]) + self.rescaletimestock(t, p)
                    self.BackorderValue[self.CurrentScenarioNr][t][p] = backorder[indexb]



    #def IncreaseCutWithFlowDual(self, cut, solution):
    #    print "Increase the cut with flow constraint of the last stage"


    def GetRHSFlowConst(self, p, t):
        righthandside = 0
        # Get the level of inventory computed in the previsous stage
        if t == self.GetStartStageTimeRangeStock( p ): #if this t is the first time period with inventory variable
            previousperiod = t - 1
            if self.Instance.HasExternalDemand[p]:
                righthandside = righthandside - 1 * self.SDDPOwner.GetInventoryFixedEarlier(p, previousperiod, self.CurrentScenarioNr)
                righthandside = righthandside + self.SDDPOwner.GetBackorderFixedEarlier(p, previousperiod, self.CurrentScenarioNr)
            else:
                righthandside = -1 * self.SDDPOwner.GetInventoryFixedEarlier(p,previousperiod, self.CurrentScenarioNr)

      #  for t2 in range(self.GetStartStageTimeRangeStock(p), t ):
        righthandside= righthandside + self.SDDPOwner.CurrentSetOfScenarios[self.CurrentScenarioNr].Demands[t][p]

        productionstartedtime = t - self.Instance.Leadtimes[p]
        if productionstartedtime < self.GetStartStageTimeRangeQuantity():
            righthandside = righthandside \
                            - self.SDDPOwner.GetQuantityFixedEarlier(p, productionstartedtime,
                                                                     self.CurrentScenarioNr)
        return righthandside


            # Demand and materials requirement: set the value of the invetory level and backorder quantity according to
    #  the quantities produced and the demand
    def CreateFlowConstraints( self ):
        self.FlowConstraintNR = [[ "" for t in self.Instance.TimeBucketSet]  for p in self.Instance.ProductSet]

        for p in self.Instance.ProductSet:
             # To speed up the creation of the model, only the variable and coffectiant which were not in the previous constraints are added (See the model definition)



            for t in self.GetLastStageTimeRangeStock( p ):
                righthandside = [self.GetRHSFlowConst(p,t)]
                backordervar = []
                backordercoeff =[]
                quantityvar = []
                quantityvarceoff = []

                dependentdemandvar = []
                dependentdemandvarcoeff = []
                if self.Instance.HasExternalDemand[p]:
                    backordervar = [ self.GetIndexBackorderVariable(p, t) ]
                    backordercoeff = [1]

                if t - self.Instance.Leadtimes[p] >= self.GetStartStageTimeRangeQuantity():
                        quantityvar = quantityvar + [ self.GetIndexQuantityVariable(p, t - self.Instance.Leadtimes[p])]
                        quantityvarceoff = quantityvarceoff + [1]

                dependentdemandvar = dependentdemandvar + [ self.GetIndexQuantityVariable(q, t) for q in
                                                            self.Instance.RequieredProduct[p] ]

                dependentdemandvarcoeff = dependentdemandvarcoeff + [-1 * self.Instance.Requirements[q][p] for q in
                                                                     self.Instance.RequieredProduct[p] ]

                inventoryvar = [ self.GetIndexStockVariable(p, t) ]
                inventorycoeff = [-1]
                if t > self.GetStartStageTimeRangeStock( p ):
                    inventoryvar = inventoryvar + [self.GetIndexStockVariable(p, t-1)]
                    inventorycoeff = inventorycoeff +[1]
                    if self.Instance.HasExternalDemand[p]:
                        backordervar = backordervar + [self.GetIndexBackorderVariable(p, t-1)]
                        backordercoeff = backordercoeff +[-1]
                vars = inventoryvar + backordervar + quantityvar + dependentdemandvar
                coeff = inventorycoeff +backordercoeff  + quantityvarceoff + dependentdemandvarcoeff

                if len(vars) > 0:
                        self.Cplex.linear_constraints.add( lin_expr=[cplex.SparsePair(vars, coeff)],
                                                           senses=["E"],
                                                           rhs=righthandside,
                                                           names = ["Flowp%dp%d"%(p,t)])
                self.FlowConstraintNR[p][t] = "Flowp%dy%d"%(p,t)
                self.IndexFlowConstraint.append(self.LastAddedConstraintIndex)
                self.LastAddedConstraintIndex = self.LastAddedConstraintIndex + 1
                self.ConcernedTimeFlowConstraint.append(t)
                self.ConcernedProductFlowConstraint.append(p)

    def IncreaseCutWithFlowDual(self, cut, sol):
        if Constants.Debug:
            print "Increase cut with flow dual"
        duals = sol.get_dual_values(self.IndexFlowConstraint)
        for i in range(len(duals)):
            p = self.ConcernedProductFlowConstraint[i]
            periodproduction = self.ConcernedTimeFlowConstraint[i] - self.Instance.Leadtimes[p]
            if periodproduction >= 0:
                cut.IncreaseCoefficientQuantity(p, periodproduction, duals[i])

            periodpreviousstock = self.ConcernedTimeFlowConstraint[i] - 1

            if periodpreviousstock < self.GetStartStageTimeRangeStock( p ):
                if periodpreviousstock >= 0:
                    cut.IncreaseCoefficientInventory(p, self.GetTimePeriodAssociatedToInventoryVariable(p) - 1,
                                                             duals[i])
                else:
                    cut.IncreaseInitInventryRHS(-1 * duals[i] * self.Instance.StartingInventories[p])

            if self.Instance.HasExternalDemand[p]:
                cut.IncreaseCoefficientBackorder(p, periodpreviousstock,  -duals[i])
                cut.IncreaseDemandRHS(duals[i] * self.SDDPOwner.CurrentSetOfScenarios[self.CurrentScenarioNr].Demands[self.ConcernedTimeFlowConstraint[i]][p])

