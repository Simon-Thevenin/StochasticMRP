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

    def IsLastStage(self):
        return self.DecisionStage == self.Instance.NrTimeBucket

    def IsFirstStage(self):
        return self.DecisionStage == 0

    def ComputeNrVariables(self):
        #number of variable at stage 1<t<T
        self.NrBackOrderVariable = sum( 1 for p in self.Instance.ProductWithExternalDemand )
        self.NrQuantityVariable = self.Instance.NrProduct
        self.NrStockVariable = self.Instance.NrProduct
        self.NrProductionVariable = 0

        # number of variable at stage 1
        if self.IsFirstStage():
            self.NrProductionVariable = self.Instance.NrTimeBucket * self.Instance.NrProduct
            self.NrBackOrderVariable = 0
            self.NrStockVariable = sum( 1 for p in self.Instance.ProductWithoutExternalDemand )

        # number of variable at stage T
        if self.IsLastStage():
            self.NrQuantityVariable = 0
            self.NrStockVariable =sum( 1 for p in self.Instance.ProductWithExternalDemand )

    def GetIndexProductionVariable(self, p, t):
        if self.IsFirstStage() :
            return self.StartProduction + p*self.Instance.NrTimeBucket + t
        else :
            raise ValueError('Production variables are only defined at stage 0')

    def GetIndexQuantityVariable(self, p ):
        return self.StartQuantity + p

    def GetIndexStockVariable(self, p ):
        if self.IsLastStage() :
            return self.StartStock + self.Instance.ProductWithExternalDemandIndex[ p ]
        elif self.IsFirstStage() :
            return self.StartStock + self.Instance.ProductWithoutExternalDemandIndex[ p ]
        else :
           return self.StartStock + p

    def GetIndexBackorderVariable(self, p ):
        if self.IsFirstStage() :
            raise ValueError('Backorder variables are not defined at stage 0')
        else :
            return self.StartBackOrder + self.Instance.ProductWithExternalDemandIndex[p]

    def GetNameProductionVariable(self, p, t):
        if self.IsFirstStage():
            return "Y_%d_%d"%(p, t )
        else:
            raise ValueError('Production variables are only defined at stage 0')

    def GetNameQuantityVariable(self, p):
        time = self.GetTimePeriodAssociatedToQuantityVariable( p )
        return "Q_%d_%d"%(p, time )

    def GetNameStockVariable(self, p):
        time = self.GetTimePeriodAssociatedToInventoryVariable( p )
        return "I_%d_%d"%(p, time)

    def GetNameBackorderVariable(self, p):
         time = self.GetTimePeriodAssociatedToBackorderVariable( p )
         return "I_%d_%d" % (p, time)

    def GetTimePeriodAssociatedToQuantityVariable( self, p ):
        result = self.DecisionStage
        return result

    def GetTimePeriodAssociatedToInventoryVariable( self, p ):
        result = self.DecisionStage
        if self.Instance.HasExternalDemand[p]:
            result = self.DecisionStage + 1

        return result

    def GetTimePeriodAssociatedToBackorderVariable( self, p ):
        result = self.DecisionStage
        if not self.Instance.HasExternalDemand[p]:
            raise ValueError('Backorder variables are not defined for component')
        return result

    # def CreateFlowConstraints(self):
    #     self.FlowConstraintNR = [[["" for t in self.Instance.TimeBucketSet] for p in self.Instance.ProductSet] for w in
    #                              self.ScenarioSet]
    #
    #     for p in self.Instance.ProductSet:
    #             righthandside = [-1 * self.Instance.StartingInventories[p]]
    #             quantityvar = []
    #             quantityvarceoff = []
    #             dependentdemandvar = []
    #             dependentdemandvarcoeff = []
    #             backordervar = []
    #             righthandside[0] = righthandside[0] + self.Scenarios[ self.CurrentScenario].Demands[t][p]
    #             if self.Instance.HasExternalDemand[p]:
    #                  backordervar = [ self.GetIndexBackorderVariable(p, t, w) ]
    #
    #                 if t - self.Instance.Leadtimes[p] >= 0:
    #                     quantityvar = quantityvar + [
    #                         self.GetIndexQuantityVariable(p, t - self.Instance.Leadtimes[p], w)]
    #                     quantityvarceoff = quantityvarceoff + [1]
    #
    #                 dependentdemandvar = dependentdemandvar + [self.GetIndexQuantityVariable(q, t, w) for q in
    #                                                            self.Instance.RequieredProduct[p]]
    #
    #                 dependentdemandvarcoeff = dependentdemandvarcoeff + [-1 * self.Instance.Requirements[q][p] for q in
    #                                                                      self.Instance.RequieredProduct[p]]
    #                 inventoryvar = [self.GetIndexInventoryVariable(p, t, w)]
    #
    #                 vars = inventoryvar + backordervar + quantityvar + dependentdemandvar
    #                 coeff = [-1] * len(inventoryvar) \
    #                         + [1] * len(backordervar) \
    #                         + quantityvarceoff \
    #                         + dependentdemandvarcoeff
    #
    #                 if len(vars) > 0:
    #                     self.Cplex.linear_constraints.add(lin_expr=[cplex.SparsePair(vars, coeff)],
    #                                                       senses=["E"],
    #                                                       rhs=righthandside,
    #                                                       names=["Flow%d%d%d" % (p, t, w)])
    #                 self.FlowConstraintNR[w][p][t] = "Flow%d%d%d" % (p, t, w)



    def DefineVariables( self ):
        self.Cplex.variables.add( obj = [0.0] * self.NrQuantityVariable,
                                  lb = [0.0] * self.NrQuantityVariable,
                                  ub = [self.M] * self.NrQuantityVariable )

        self.Cplex.variables.add( obj = [ math.pow( self.Instance.Gamma, self.DecisionStage )
                                          * self.Instance.SetupCosts[p]
                                            for p in self.Instance.ProductSet
                                            for t in self.Instance.TimeBucketSet],
                                  lb = [0.0] * self.NrProductionVariable,
                                  ub = [self.M] * self.NrProductionVariable )


        productwithstockvariable = self.Instance.ProductSet
        #At the first stage, only the components are associated with a stock variable
        if self.IsFirstStage():
            productwithstockvariable = self.Instance.ProductWithoutExternalDemand

        self.Cplex.variables.add( obj = [ math.pow( self.Instance.Gamma, self.DecisionStage )
                                          * self.Instance.InventoryCosts[p]
                                          if self.Instance.HasExternalDemand[p] else
                                          math.pow(self.Instance.Gamma, self.DecisionStage +1)
                                          * self.Instance.InventoryCosts[p]
                                          for p in productwithstockvariable ],
                                  lb = [0.0] * self.NrStockVariable,
                                  ub = [self.M] * self.NrStockVariable )


        self.Cplex.variables.add( obj = [math.pow( self.Instance.Gamma, self.DecisionStage ) * self.Instance.BackorderCosts[  self.Instance.ProductWithExternalDemandIndex[p] ]
                                             if not self.IsLastStage()
                                             else math.pow( self.Instance.Gamma, self.DecisionStage ) * self.Instance.LostSaleCost[  self.Instance.ProductWithExternalDemandIndex[p] ]
                                             for p in self.Instance.ProductWithExternalDemand ],
                                      lb = [0.0] * self.NrBackOrderVariable,
                                      ub = [self.M] * self.NrBackOrderVariable )

        if Constants.Debug:
            self.AddVariableName()



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
                        productionvars.append((self.GetIndexProductionVariable(p, t), self.GetNameProductionVariable(p, t)))

            quantityvars.append( ( self.GetIndexQuantityVariable(p), self.GetNameQuantityVariable(p) ) )
            inventoryvars.append( ( self.GetIndexStockVariable(p), self.GetNameStockVariable(p) ) )
            if self.Instance.HasExternalDemand[p] and not self.IsFirstStage():
                     backordervars.append( ( self.GetIndexBackorderVariable(p), self.GetNameBackorderVariable(p) ) )

            quantityvars = list( set( quantityvars ) )
            productionvars = list( set( productionvars ) )
            inventoryvars = list( set( inventoryvars ) )
            backordervars = list( set( backordervars ) )
            varnames = quantityvars + inventoryvars + productionvars + backordervars
            self.Cplex.variables.set_names(varnames)

    def DefineMIP( self ):
        if Constants.Debug:
            print "Define the MIP of stage %d" % self.DecisionStage

        self.DefineVariables()

        self.MIPDefined = True

    #The function below update the constraint of the MIP to correspond to the new scenario
    def UpdateMIP( self ):
        print "TBD "

    #This function Build or update the MIP of the current stage
    def BuildMIP( self ):
        if Constants.Debug:
            print "build the MIP of stage %d" %self.DecisionStage

        if not self.MIPDefined:
            self.DefineMIP()
        else:
            self.UpdateMIP()

    # This function run the MIP of the current stage
    def Run(self):
        if Constants.Debug:
            print "Update the MIP of stage %d" % self.DecisionStage
            self.Cplex.write( "stage_%d_iter_%d.lp" %( self.DecisionStage, self.SDDPOwner.CurrentIteration ) )

        self.Cplex.solve()



    def GernerateCut( self ):
        if Constants.Debug:
            print "Generate a cut to add at stage %d" % self.PreviousSDDPStage.DecisionStage