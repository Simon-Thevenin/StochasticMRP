import cplex
import math
from Constants import Constants
from SDDPCut import SDDPCut


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
        self.SDDPCuts = []
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
        self.StartCostToGo = self.StartBackOrder + self.NrBackOrderVariable
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

        # Try to use the corepoint method of papadakos, remove if it doesn't work
        self.CorePointQuantityValues = []
        # The value of the production variables (filled after having solve the MIPs for all scenario)
        self.CorePointProductionValue = []
        # The value of the inventory variables (filled after having solve the MIPs for all scenario)
        self.CorePointInventoryValue = []
        # The value of the backorder variable (filled after having solve the MIPs for all scenario)
        self.CorePointBackorderValue = []

        #The cost of each scenario
        self.StageCostPerScenarioWithoutCostoGo = []
        self.StageCostPerScenarioWithCostoGo = []
        self.PartialCostPerScenario = []
        self.PassCost = -1
        self.NrScenario = -1

        self.LastAddedConstraintIndex = 0
        self.IndexFlowConstraint = []
        self.IndexProductionQuantityConstraint = []
        self.IndexCapacityConstraint = []
        self.IndexCutConstraint = []

        self.ConcernedProductFlowConstraint = []
        self.ConcernedTimeFlowConstraint = []
        self.ConcernedProductProductionQuantityConstraint = []
        self.ConcernedTimeProductionQuantityConstraint = []
        self.ConcernedResourceCapacityConstraint = []
        self.IndexCutConstraint = []
        self.ConcernedCutinConstraint = []


    def ComputePassCost(self):
        self.PassCost = sum(self.PartialCostPerScenario[w] for w in self.ScenarioNrSet) / self.NrScenario
        self.PassCostWithAproxCosttoGo = sum(self.StageCostPerScenarioWithCostoGo[w] for w in self.ScenarioNrSet) / self.NrScenario

    #This function modify the number of scenario in the stage
    def SetNrScenario(self, nrscenario ):
        self.NrScenario = nrscenario
        self.ScenarioNrSet = range( nrscenario )
        #The quantity to order (filled after having solve the MIPs for all scenario)
        self.QuantityValues = [ [] for w in self.ScenarioNrSet ]
        #The value of the production variables (filled after having solve the MIPs for all scenario)
        self.ProductionValue = [ [ [] for t in self.Instance.TimeBucketSet] for w in self.ScenarioNrSet ]
        # The value of the inventory variables (filled after having solve the MIPs for all scenario)
        self.InventoryValue = [ [] for w in self.ScenarioNrSet ]
        #The value of the backorder variable (filled after having solve the MIPs for all scenario)
        self.BackorderValue = [ [] for w in self.ScenarioNrSet ]
        # The cost of each scenario
        self.StageCostPerScenarioWithoutCostoGo = [ -1 for w in self.ScenarioNrSet ]
        self.StageCostPerScenarioWithCostoGo = [-1 for w in self.ScenarioNrSet]

        self.PartialCostPerScenario = [ 0 for w in self.ScenarioNrSet]

    #Return true if the current stage is the last
    def IsLastStage(self):
        return False

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
        result = self.DecisionStage - 1
        if not self.Instance.HasExternalDemand[p]:
            result = self.DecisionStage

        return result

    # Return the time period associated with backorder of product p decided at the current stage
    def GetTimePeriodAssociatedToBackorderVariable( self, p ):
        result = self.DecisionStage -1
        if not self.Instance.HasExternalDemand[p]:
            raise ValueError('Backorder variables are not defined for component')
        return result

    #This function return the right hand side of flow constraint for product p
    def GetRHSFlowConst(self, p):
        righthandside = 0
        if self.Instance.HasExternalDemand[p] and not self.IsFirstStage():
            righthandside = righthandside \
                               + self.SDDPOwner.CurrentSetOfScenarios[self.CurrentScenarioNr].Demands[
                                   self.GetTimePeriodAssociatedToInventoryVariable(p)][p]
            if self.GetTimePeriodAssociatedToBackorderVariable(p) -1 >= 0:
                righthandside = righthandside \
                                   + self.SDDPOwner.GetBackorderFixedEarlier(p,
                                                                             self.GetTimePeriodAssociatedToBackorderVariable(p) -1,
                                                                             self.CurrentScenarioNr)

        productionstartedtime = self.GetTimePeriodAssociatedToInventoryVariable(p) - self.Instance.Leadtimes[p]
        if productionstartedtime >= 0:
            righthandside = righthandside \
                               - self.SDDPOwner.GetQuantityFixedEarlier(p, productionstartedtime ,
                                                                        self.CurrentScenarioNr)

        if self.GetTimePeriodAssociatedToInventoryVariable(p) - 1 >= -1 and not ( self.IsFirstStage() and  self.Instance.HasExternalDemand[p] ):
            righthandside = righthandside \
                               - self.SDDPOwner.GetInventoryFixedEarlier(p,
                                                                         self.GetTimePeriodAssociatedToInventoryVariable(
                                                                             p) - 1, self.CurrentScenarioNr)
        return righthandside

    #This funciton creates all the flow constraint
    def CreateFlowConstraints(self):
        self.FlowConstraintNR = [""  for p in self.Instance.ProductSet]

        for p in self.Instance.ProductSet:
            if  not (  ( self.IsFirstStage()  and  self.Instance.HasExternalDemand[p] )  or  (  self.IsLastStage()  and ( not   self.Instance.HasExternalDemand[p] ) ) ) :
                backordervar = []
                inventoryvar = []
                quantityvar = []
                dependentdemandvar = []
                dependentdemandvarcoeff = []
                righthandside = [ self.GetRHSFlowConst( p )]
                if self.Instance.HasExternalDemand[p] and not self.IsFirstStage():
                     backordervar = [ self.GetIndexBackorderVariable(p) ]

                else:
                     dependentdemandvar = [self.GetIndexQuantityVariable(q) for q in  self.Instance.RequieredProduct[p] ]
                     dependentdemandvarcoeff =  [-1 * self.Instance.Requirements[q][p] for q in self.Instance.RequieredProduct[p]]


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

                       self.IndexFlowConstraint.append( self.LastAddedConstraintIndex )
                       self.LastAddedConstraintIndex = self.LastAddedConstraintIndex + 1

                       self.ConcernedProductFlowConstraint.append( p )



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

    #This function returns the right hand side of the production consraint associated with product p
    def GetProductionConstrainRHS(self, p):
        if self.IsFirstStage():
            righthandside = 0.0
        else:
                yvalue = self.SDDPOwner.GetSetupFixedEarlier(p, self.GetTimePeriodAssociatedToQuantityVariable(p),
                                                             self.CurrentScenarioNr)
                righthandside = self.GetBigMValue(p) * yvalue

        return righthandside


    # This function creates the  indicator constraint to se the production variable to 1 when a positive quantity is produce
    def CreateProductionConstraints(self):
        for p in self.Instance.ProductSet:
            righthandside = [ self.GetProductionConstrainRHS( p ) ]
            if self.IsFirstStage():
                vars = [  self.GetIndexQuantityVariable( p ) , self.GetIndexProductionVariable( p, self.GetTimePeriodAssociatedToQuantityVariable( p ) ) ]
                coeff = [-1.0, self.GetBigMValue(p)]

                # PrintConstraint( vars, coeff, righthandside )
                self.Cplex.linear_constraints.add( lin_expr=[cplex.SparsePair(vars, coeff)],
                                                    senses=["G"],
                                                    rhs=righthandside)


            else:
                    vars = [ self.GetIndexQuantityVariable(p) ]
                    coeff = [1.0]
                    # PrintConstraint( vars, coeff, righthandside )
                    self.Cplex.linear_constraints.add(lin_expr=[cplex.SparsePair(vars, coeff)],
                                                         senses=["L"],
                                                         rhs=righthandside)
            self.IndexProductionQuantityConstraint.append(self.LastAddedConstraintIndex)
            self.LastAddedConstraintIndex = self.LastAddedConstraintIndex + 1

            self.ConcernedProductProductionQuantityConstraint.append(p)
            self.ConcernedTimeProductionQuantityConstraint.append(self.GetTimePeriodAssociatedToQuantityVariable(p))

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

               self.IndexCapacityConstraint.append(self.LastAddedConstraintIndex)
               self.LastAddedConstraintIndex = self.LastAddedConstraintIndex + 1

               self.ConcernedResourceCapacityConstraint.append(k)

    #Define the variables
    def DefineVariables( self ):
        #The setups are decided at the first stage
        if self.IsFirstStage():
            self.Cplex.variables.add( obj = [ math.pow( self.Instance.Gamma, t )
                                              * self.Instance.SetupCosts[p]
                                                for p in self.Instance.ProductSet
                                                for t in self.Instance.TimeBucketSet],
                                             #lb=[0.0] * self.NrProductionVariable,
                                             #ub=[1.0] * self.NrProductionVariable)
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
                                  lb = [0.0] * len(productwithstockvariable),
                                  ub = [self.M] * len(productwithstockvariable) )

        # Backorder/lostsales variables
        productwithbackorder= self.GetProductWithBackOrderVariable()
        self.Cplex.variables.add( obj = [math.pow( self.Instance.Gamma, self.DecisionStage - 1) * self.Instance.BackorderCosts[  p ]
                                             if not self.IsLastStage()
                                             else math.pow( self.Instance.Gamma, self.DecisionStage -1 ) * self.Instance.LostSaleCost[  p ]
                                             for p in productwithbackorder],
                                      lb = [0.0] * self.NrBackOrderVariable,
                                      ub = [self.M] * self.NrBackOrderVariable )

        if not self.IsLastStage():
            self.Cplex.variables.add(
                obj=[1],
                lb=[0.0],
                ub=[self.M] )


        #In debug mode, the variables have names
        if Constants.Debug:
            self.AddVariableName()

    #Add the name of each variable
    def AddVariableName(self):
        if Constants.Debug:
            print "Add the names of the variable"
        # Define the variable name.
        # Usefull for debuging purpose. Otherwise, disable it, it is time consuming.
        if Constants.Debug:
            quantityvars = []
            inventoryvars = []
            productionvars = []
            backordervars = []
            costtogovars = []
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

                costtogovars = [( self.StartCostToGo, "E%d"%(self.DecisionStage + 1) ) ]
            quantityvars = list( set( quantityvars ) )
            productionvars = list( set( productionvars ) )
            inventoryvars = list( set( inventoryvars ) )
            backordervars = list( set( backordervars ) )
            varnames = quantityvars + inventoryvars + productionvars + backordervars + costtogovars
            self.Cplex.variables.set_names(varnames)

    #Create the MIP
    def DefineMIP( self, scenarionr ):
        if Constants.Debug:
            print "Define the MIP of stage %d" % self.DecisionStage
        self.DefineVariables()
        self.CurrentScenarioNr  = scenarionr
        self.CreateProductionConstraints()
        self.CreateFlowConstraints()
        self.CreateCapacityConstraints()
        self.MIPDefined = True

    #The function below update the constraint of the MIP to correspond to the new scenario
    def UpdateMIPForScenario( self, scenarionr ):
        self.CurrentScenarioNr  = scenarionr
        constraintuples = []


        for i in range( len(self.IndexFlowConstraint) ):
            constr = self.IndexFlowConstraint[i]
            p = self.ConcernedProductFlowConstraint[i]
            if not self.IsLastStage():
                rhs = self.GetRHSFlowConst( p )
            else:
                t = self.ConcernedTimeFlowConstraint[i]
                rhs = self.GetRHSFlowConst( p, t )
            constraintuples.append( (constr, rhs)  )

        #self.Cplex.linear_constraints.set_rhs(constraintuples)

        #constrainttuples = []
        for cut in self.SDDPCuts:
            #Do not modify a cut that is not already added
            if cut.IsActive:
                constraintuples.append( cut.ModifyCut())
        if len(constraintuples) > 0:
            #print constraintuples
            self.Cplex.linear_constraints.set_rhs(constraintuples)

    #This function update the MIP for the current stage, taking into account the new value fixedin the previous stage
    def UpdateMIPForStage(self):
        if not self.IsFirstStage():
            constraintuples =[]
            for i in range( len( self.IndexProductionQuantityConstraint ) ):
                    constr = self.IndexProductionQuantityConstraint[i]
                    p = self.ConcernedProductProductionQuantityConstraint[i]
                    if not self.IsLastStage():
                        rhs = self.GetProductionConstrainRHS(p)
                    else:
                        t = self.ConcernedTimeProductionQuantityConstraint[i]
                        rhs= self.GetProductionConstrainRHS(p,t)

                    constraintuples.append( (constr, rhs) )
            self.Cplex.linear_constraints.set_rhs(constraintuples)


    #This run the MIP of the current stage (one for each scenario)
    def RunForwardPassMIP( self ):

        generatecut = self.IsLastStage() and not self.SDDPOwner.EvaluationMode

        if Constants.Debug:
            print "build the MIP of stage %d" %self.DecisionStage

        # Create a cute for the previous stage problem
        if generatecut:
            cut = SDDPCut(self.PreviousSDDPStage)



        if self.MIPDefined:
            self.UpdateMIPForStage()

        if self.IsFirstStage():
            consideredscenario = [0]#range( len( self.SDDPOwner.CurrentSetOfScenarios ) )
        else:
            consideredscenario = range( len( self.SDDPOwner.CurrentSetOfScenarios ) )

        for w in consideredscenario:
            if not self.MIPDefined:
                self.DefineMIP( w )
            else:
                self.UpdateMIPForScenario( w )
            if Constants.PrintDebugLPFiles:
                print "Update or build the MIP of stage %d for scenario %d" %( self.DecisionStage, w )
                self.Cplex.write("stage_%d_iter_%d_scenar_%d.lp" % (self.DecisionStage, self.SDDPOwner.CurrentIteration, w))
            else:
                # name = "mrp_log%r_%r_%r" % ( self.Instance.InstanceName, self.Model, self.DemandScenarioTree.Seed )
                self.Cplex.set_log_stream(None)
                self.Cplex.set_results_stream(None)
                self.Cplex.set_warning_stream(None)
                self.Cplex.set_error_stream(None)
            self.Cplex.parameters.advance = 1
            self.Cplex.parameters.lpmethod = 2  # Dual primal cplex.CPX_ALG_DUAL
            self.Cplex.parameters.threads.set(1)
            self.Cplex.solve()
            if Constants.Debug:
                 print "Solution status:%r"%self.Cplex.solution.get_status()

            if self.IsFirstStage():
                for w2 in  range( len( self.SDDPOwner.CurrentSetOfScenarios ) ):
                    self.CurrentScenarioNr = w2
                    self.SaveSolutionForScenario()

            else:
                self.SaveSolutionForScenario(  )

            if generatecut:
                sol = self.Cplex.solution
                self.ImproveCutFromSolution(cut, sol)

        if generatecut:
                # Average by the number of scenario
            cut.DivideAllCoeff(len(self.SDDPOwner.CurrentSetOfScenarios))
            if Constants.Debug:
                self.checknewcut(cut)

            cut.AddCut()

        #if self.IsLastStage():
            # Average by the number of scenario
        #    cut.DivideAllCoeff(len(self.SDDPOwner.CurrentSetOfScenarios))


    def GetVariableValue(self, sol):
        indexarray = [self.GetIndexQuantityVariable(p) for p in self.Instance.ProductSet]
        self.QuantityValues[self.CurrentScenarioNr] = sol.get_values(indexarray)

        if self.IsFirstStage():
            indexarray = [self.GetIndexProductionVariable(p, t) for t in self.Instance.TimeBucketSet for p in
                          self.Instance.ProductSet]
            values = sol.get_values(indexarray)
            self.ProductionValue[self.CurrentScenarioNr] = [
                 [ max( values[t * self.Instance.NrProduct + p], 0.0) for p in self.Instance.ProductSet] for t in
                 self.Instance.TimeBucketSet]
                #[round( values[t * self.Instance.NrProduct + p], 0) for p in self.Instance.ProductSet] for t in
                #self.Instance.TimeBucketSet]

        prductwithstock = self.GetProductWithStockVariable()
        indexarray = [self.GetIndexStockVariable(p) for p in prductwithstock]
        inventory = sol.get_values(indexarray)
        if self.IsFirstStage():
            self.InventoryValue[self.CurrentScenarioNr] = ['nan' for p in self.Instance.ProductSet]
            index = 0
            for p in prductwithstock:
                self.InventoryValue[self.CurrentScenarioNr][p] = inventory[index]
                index = index + 1
        else:
           self.InventoryValue[self.CurrentScenarioNr] = inventory

        if not self.IsFirstStage():
            indexarray = [self.GetIndexBackorderVariable(p) for p in self.GetProductWithBackOrderVariable()]
            self.BackorderValue[self.CurrentScenarioNr] = sol.get_values(indexarray)


    # This function run the MIP of the current stage
    def SaveSolutionForScenario(self):

        sol = self.Cplex.solution
        if sol.is_primal_feasible():
            if Constants.PrintDebugLPFiles:
                sol.write("mrpsolution.sol")

            obj =  sol.get_objective_value()
            self.StageCostPerScenarioWithCostoGo[ self.CurrentScenarioNr ] = obj
            self.StageCostPerScenarioWithoutCostoGo[self.CurrentScenarioNr] = self.StageCostPerScenarioWithCostoGo[self.CurrentScenarioNr]
            if not self.IsLastStage():
                self.StageCostPerScenarioWithoutCostoGo[self.CurrentScenarioNr] =  self.StageCostPerScenarioWithCostoGo[ self.CurrentScenarioNr ]  - sol.get_values( [self.StartCostToGo] )[0]

            if self.IsFirstStage():
                self.PartialCostPerScenario[ self.CurrentScenarioNr ] = self.StageCostPerScenarioWithoutCostoGo[ self.CurrentScenarioNr ]
            else:
                self.PartialCostPerScenario[ self.CurrentScenarioNr ] = self.StageCostPerScenarioWithoutCostoGo[ self.CurrentScenarioNr ] \
                                                                        + self.PreviousSDDPStage.PartialCostPerScenario[ self.CurrentScenarioNr ]

            self.GetVariableValue(sol)

            if Constants.Debug:
                print "******************** Solutionat stage %d cost: %d *********************"%(self.DecisionStage, sol.get_objective_value() )
                print " Quantities: %r"%self.QuantityValues
                print " Inventory: %r"%self.InventoryValue
                print " BackOrder: %r"%self.BackorderValue
                if self.IsFirstStage():
                    print " Production: %r "%self.ProductionValue
                print "*************************************************************"
        else:
            self.Cplex.write("InfeasibleLP_stage_%d_iter_%d_scenar_%d.lp" % (self.DecisionStage, self.SDDPOwner.CurrentIteration, self.CurrentScenarioNr) )
            raise NameError("Infeasible sub-problem!!!!")



    def ImproveCutFromSolution(self, cut, solution):
        self.IncreaseCutWithFlowDual(cut, solution)

        self.IncreaseCutWithProductionDual(cut, solution)

        self.IncreaseCutWithCapacityDual(cut, solution)

        if not self.IsLastStage():
            self.IncreaseCutWithCutDuals(cut, solution)


            #Generate the bender cut
    def GernerateCut( self ):
        if Constants.Debug:
            print "Generate a cut to add at stage %d" % self.PreviousSDDPStage.DecisionStage

        # Create a cute for the previous stage problem
        cut = SDDPCut(self.PreviousSDDPStage)

        if not self.IsLastStage() and not self.IsFirstStage():
            # Re-run the MIP to take into account the just added cut
            # Solve the problem for each scenario

            for w in range(len(self.SDDPOwner.CurrentSetOfScenarios)):


                self.UpdateMIPForScenario(w)
                if Constants.PrintDebugLPFiles:
                    print "Resolve for backward pass the MIP of stage %d for scenario %d" % (self.DecisionStage, w)
                    self.Cplex.write(
                        "backward_stage_%d_iter_%d_scenar_%d.lp" % (self.DecisionStage, self.SDDPOwner.CurrentIteration, w))

                self.Cplex.parameters.threads.set(1)
                self.Cplex.solve()


                sol =self.Cplex.solution

                if Constants.Debug:
                    print "cost of subproblem: %r"%sol.get_objective_value()

                if Constants.PrintDebugLPFiles:
                    sol.write("mrpsolution.sol")
                self.ImproveCutFromSolution( cut, sol)



            #Average by the number of scenario
            cut.DivideAllCoeff( len(self.SDDPOwner.CurrentSetOfScenarios) )

            if Constants.Debug:
                self.checknewcut(cut)

            cut.AddCut()

    def checknewcut(self, cut):
        currentosttogo = sum( self.SDDPOwner.Stage[t].StageCostPerScenarioWithoutCostoGo[w]
                              for w in range(self.SDDPOwner.CurrentNrScenario)
                              for t in range( self.DecisionStage , len(self.SDDPOwner.StagesSet) ) ) / self.SDDPOwner.CurrentNrScenario

        for w in range(len(self.SDDPOwner.CurrentSetOfScenarios)):
            self.PreviousSDDPStage.UpdateMIPForScenario(w)
            self.PreviousSDDPStage.Cplex.solve()
            #sol = self.Cplex.solution
            print "Cut added, the value of the cost to go with current sol is: %r (actual: %r)" % (
                cut.GetCostToGoLBInCUrrentSolution(self.PreviousSDDPStage.Cplex.solution), currentosttogo)


    def GetBigMValue( self, p ):
        result = self.SDDPOwner.CurrentBigM[p]
        return result

    def IncreaseCutWithFlowDual(self, cut, sol):
        if Constants.Debug:
            print "Increase cut with flow dual"
        duals = sol.get_dual_values(  self.IndexFlowConstraint )
        for i in range( len( duals )):
            if duals[i] <> 0:
                p = self.ConcernedProductFlowConstraint[ i ]
                if not self.IsLastStage():
                    periodproduction = self.GetTimePeriodAssociatedToInventoryVariable( p ) - self.Instance.Leadtimes[p]
                else:
                    periodproduction = self.ConcernedTimeFlowConstraint[ i ] - self.Instance.Leadtimes[p]


                if periodproduction  >= 0:
                    cut.IncreaseCoefficientQuantity( p, periodproduction , duals[i])

                if not self.IsLastStage():
                    periodpreviousstock = self.GetTimePeriodAssociatedToInventoryVariable( p ) -1
                else:
                    periodpreviousstock = self.ConcernedTimeFlowConstraint[ i ] - 1

                if periodpreviousstock >= 0:
                    cut.IncreaseCoefficientInventory( p, self.GetTimePeriodAssociatedToInventoryVariable( p ) -1, duals[i])
                else:
                    cut.IncreaseInitInventryRHS( -1*duals[i] * self.Instance.StartingInventories[p] )

                if self.Instance.HasExternalDemand[p]:
                    cut.IncreaseCoefficientBackorder( p, self.GetTimePeriodAssociatedToBackorderVariable( p ) -1 , -duals[i])
                    cut.IncreaseDemandRHS( duals[i]
                                           * self.SDDPOwner.CurrentSetOfScenarios[self.CurrentScenarioNr].Demands[self.GetTimePeriodAssociatedToInventoryVariable(p)][p])

    def IncreaseCutWithProductionDual(self, cut, sol):
        if Constants.Debug:
                print "Increase cut with production dual"
        duals = sol.get_dual_values(self.IndexProductionQuantityConstraint)
        for i in range(len(duals)):
            if duals[i] <> 0:
                p = self.ConcernedProductProductionQuantityConstraint[ self.IndexProductionQuantityConstraint[i] ]
                t= self.ConcernedTimeProductionQuantityConstraint[ self.IndexProductionQuantityConstraint[i] ]
                cut.IncreaseCoefficientProduction( p,t , -1* self.GetBigMValue(p) * duals[i])


    def IncreaseCutWithCapacityDual(self, cut, sol):
         if Constants.Debug:
            print "Increase cut with capacity dual"
         duals = sol.get_dual_values(self.IndexCapacityConstraint)
         for i in range(len(duals)):
             if duals[i] <> 0:
                 k = self.ConcernedResourceCapacityConstraint[ i ]
                 cut.IncreaseCapacityRHS( self.Instance.Capacity[k] * duals[i])

    def IncreaseCutWithCutDuals(self, cut, sol):

        #if self.SDDPOwner.CurrentIteration > 0 :
            if Constants.Debug:
                print "Increase cut with cut duals"
            duals = sol.get_dual_values(self.IndexCutConstraint)
            for i in range(len(duals)):
                if( duals[i] <> 0 ):
                    c = self.ConcernedCutinConstraint[i]
                    #In the new cut the contribution of C to the RHS is the RHS of C plus the value of of te variable of the current stage.
                    #variableatstage = c.GetCutVariablesAtStage()
                    #valueofvariable = sol.get_values(variableatstage)
                    #coefficientvariableatstage =c.GetCutVariablesCoefficientAtStage()
                    #valueofvarsinconsraint = sum(i[0] * i[1] for i in zip(valueofvariable, coefficientvariableatstage))
                    cut.IncreasePReviousCutRHS( c.GetRHS() * duals[i])#( c.GetRHS() + valueofvarsinconsraint )* duals[i])

                    for tuple in c.NonZeroFixedEarlierProductionVar:
                        p=tuple[0]; t=tuple[1]
                        cut.IncreaseCoefficientProduction(p,t, c.CoefficientProductionVariable[t][p] * duals[i])
                    for tuple in c.NonZeroFixedEarlierQuantityVar:
                        p = tuple[0];                t = tuple[1]
                        cut.IncreaseCoefficientQuantity(p,t, c.CoefficientQuantityVariable[t][p] * duals[i])
                    for tuple in c.NonZeroFixedEarlierBackOrderVar:
                        p = tuple[0];               t = tuple[1]
                        cut.IncreaseCoefficientBackorder(p,t, c.CoefficientBackorderyVariable[t][ self.Instance.ProductWithExternalDemandIndex[p]] * duals[i])
                    for tuple in c.NonZeroFixedEarlierStockVar:
                        p = tuple[0];                t = tuple[1]
                        cut.IncreaseCoefficientInventory(p,t, c.CoefficientStockVariable[t][p] * duals[i])

    # Try to use the corepoint method of papadakos, remove if it doesn't work
    # average current solution with last core point
    def UpdateCorePoint(self):

        if self.SDDPOwner.CurrentIteration > 1 :
            # Try to use the corepoint method of papadakos, remove if it doesn't work
            self.CorePointQuantityValues = [ [ 0.5 * self.QuantityValues[w][p] + 0.5 * self.CorePointQuantityValues[w][p]
                                             for p in self.Instance.ProductSet ] for w in self.ScenarioNrSet ]
            self.CorePointProductionValue = [ [ [ max( 0.5 * self.ProductionValue[w][t][p] + 0.5 * self.CorePointProductionValue[w][t][p], 0.0)
                                             for p in self.Instance.ProductSet ] for t in self.Instance.TimeBucketSet ] for w in self.ScenarioNrSet ]
            # The value of the inventory variables (filled after having solve the MIPs for all scenario)
            self.CorePointInventoryValue =  [ [ 0.5 * self.InventoryValue[w][p] + 0.5 * self.CorePointInventoryValue[w][p] if not self.Instance.HasExternalDemand[p] else 'nan'
                                             for p in self.Instance.ProductSet ] for w in self.ScenarioNrSet ]
            # The value of the backorder variable (filled after having solve the MIPs for all scenario)
            #self.CorePointBackorderValue =  [ [ 0.5 * self.BackorderValue[w][p] + 0.5 * self.CorePointBackorderValue[w][p]
            #                                 for p in self.Instance.ProductSet ] for w in self.ScenarioNrSet ]
        else:
            # Try to use the corepoint method of papadakos, remove if it doesn't work
            self.CorePointQuantityValues = [[ self.QuantityValues[w][p]
                                             for p in self.Instance.ProductSet] for w in self.ScenarioNrSet]
            self.CorePointProductionValue = [[[ self.ProductionValue[w][t][p]
                                               for p in self.Instance.ProductSet]
                                              for t in self.Instance.TimeBucketSet]
                                             for w in self.ScenarioNrSet]
            # The value of the inventory variables (filled after having solve the MIPs for all scenario)
            self.CorePointInventoryValue = [[ self.InventoryValue[w][p]
                                             for p in self.Instance.ProductSet] for w in self.ScenarioNrSet]
            # The value of the backorder variable (filled after having solve the MIPs for all scenario)
            #self.CorePointBackorderValue = [[ self.BackorderValue[w][p]
            #                                 for p in self.Instance.ProductSet] for w in self.ScenarioNrSet]
