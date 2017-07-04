import cplex
from Constants import Constants
#from sets import Set

class SDDPCut:

    def __init__( self, owner = None   ):
        self.Stage = owner
        owner.SDDPCuts.append(self)
        self.Iteration = self.Stage.SDDPOwner.CurrentIteration
        self.Id = self.Iteration
        self.Name = "Cut_%d"%self.Iteration
        self.Instance =  self.Stage.Instance

        self.CoefficientQuantityVariable = [  [ 0 for p in self.Instance.ProductSet] for t in self.Instance.TimeBucketSet ]
        self.CoefficientProductionVariable = [  [ 0 for p in self.Instance.ProductSet] for t in self.Instance.TimeBucketSet ]
        self.CoefficientStockVariable = [  [ 0 for p in self.Instance.ProductSet] for t in self.Instance.TimeBucketSet ]
        self.CoefficientBackorderyVariable = [  [ 0 for p in self.Instance.ProductWithExternalDemand] for t in self.Instance.TimeBucketSet ]

        #The quantity variable fixed at earlier stages with a non zero coefficient
        self.NonZeroFixedEarlierQuantityVar = set()
        self.NonZeroFixedEarlierProductionVar = set()
        self.NonZeroFixedEarlierStockVar = set()
        self.NonZeroFixedEarlierBackOrderVar = set()


        self.DemandRHS = 0.0
        self.CapacityRHS = 0.0
        self.PreviousCutRHS = 0.0
        self.InitialInventoryRHS = 0.0
        self.CPlexConstraint = None
        self.IsActive = False
        self.RHSConstantValue = -1
        self.RHSValueComputed = False
        #self.LastAddedConstraintIndex = 0

        #This function add the cut to the MIP

    #This function return the variables of the cut in its stage (do ot include the variable fixed at previous stage)
    def GetCutVariablesAtStage(self):
        vars = [self.Stage.StartCostToGo] \
               + [self.Stage.GetIndexQuantityVariable(p) for p in self.Instance.ProductSet] \
               + [self.Stage.GetIndexStockVariable(p) for p in self.Stage.GetProductWithStockVariable()]
        if not self.Stage.IsFirstStage():
            vars = vars + [self.Stage.GetIndexBackorderVariable(p) for p in self.Instance.ProductWithExternalDemand]

        if self.Stage.DecisionStage == 0:
            vars = vars + [self.Stage.GetIndexProductionVariable(p, t) for p in self.Instance.ProductSet for t in
                           self.Instance.TimeBucketSet]

        return vars

    # This function return the coefficient variables of the cut in its stage (do ot include the variable fixed at previous stage)
    def GetCutVariablesCoefficientAtStage(self):
        coeff = [1] \
                + [self.CoefficientQuantityVariable[self.Stage.GetTimePeriodAssociatedToQuantityVariable(p)][p] for p in
                   self.Instance.ProductSet] \
                + [self.CoefficientStockVariable[self.Stage.GetTimePeriodAssociatedToInventoryVariable(p)][p] for p in
                   self.Stage.GetProductWithStockVariable()]

        if not self.Stage.IsFirstStage():
            coeff = coeff + [
                self.CoefficientBackorderyVariable[self.Stage.GetTimePeriodAssociatedToBackorderVariable(p)][
                    self.Instance.ProductWithExternalDemandIndex[p]]
                for p in self.Instance.ProductWithExternalDemand]

        if self.Stage.DecisionStage == 0:
            coeff = coeff + [self.CoefficientProductionVariable[t][p] for p in self.Instance.ProductSet for t in
                             self.Instance.TimeBucketSet]
        return coeff

    def AddCut(self):
        self.IsActive = True
        if Constants.Debug:
            print "Add the Cut %s" %self.Name


        vars = self.GetCutVariablesAtStage()

        #multiply by -1 because the variable goes on the left hand side
        coeff =  self.GetCutVariablesCoefficientAtStage()
        self.RHSConstantValue = self.DemandRHS + self.CapacityRHS + self.PreviousCutRHS + self.InitialInventoryRHS
        righthandside = [ self.ComputeCurrentRightHandSide() ]

        self.Stage.Cplex.linear_constraints.add( lin_expr=[cplex.SparsePair(vars, coeff)],
                                           senses=["G"],
                                           rhs=righthandside,
                                           names =[self.Name] )

        self.Stage.IndexCutConstraint.append( self.Stage.LastAddedConstraintIndex )
        self.Stage.LastAddedConstraintIndex = self.Stage.LastAddedConstraintIndex + 1

        self.Stage.ConcernedCutinConstraint.append( self )




    #This function modify the cut to take into account the Fixed variables
    def ModifyCut( self ):

        righthandside = self.ComputeCurrentRightHandSide()

        constrnr = self.Name
        constrainttuples=(constrnr, righthandside)
        return constrainttuples



    def GetRHS(self):
        righthandside = self.RHSConstantValue
        return righthandside

    def ComputeCurrentRightHandSideA(self):

        righthandside =  self.GetRHS()

        for p in self.Instance.ProductSet:
                for t in range(0,self.Stage.GetTimePeriodAssociatedToQuantityVariable( p )):
                   if self.CoefficientQuantityVariable[t][p] > 0:
                        righthandside =  righthandside  - self.Stage.SDDPOwner.GetQuantityFixedEarlier(p,t, self.Stage.CurrentScenarioNr) \
                                                          * self.CoefficientQuantityVariable[t][p]

        if not self.Stage.IsFirstStage():
            for p in self.Instance.ProductSet:
                    for t in self.Instance.TimeBucketSet:
                        if self.CoefficientProductionVariable[t][p] > 0:
                            righthandside = righthandside - self.Stage.SDDPOwner.GetSetupFixedEarlier(p, t, self.Stage.CurrentScenarioNr)\
                                                        * self.CoefficientProductionVariable[t][p]


        for p in self.Instance.ProductSet:
                for t in range(0, self.Stage.GetTimePeriodAssociatedToInventoryVariable(p)):
                    righthandside = righthandside - self.Stage.SDDPOwner.GetInventoryFixedEarlier(p, t, self.Stage.CurrentScenarioNr) \
                                                    * self.CoefficientStockVariable[t][p]

        for p in self.Instance.ProductWithExternalDemand:
                for t in range(0,self.Stage.GetTimePeriodAssociatedToBackorderVariable(p)):

                    indexp = self.Instance.ProductWithExternalDemandIndex[p]
                    righthandside = righthandside - self.Stage.SDDPOwner.GetBackorderFixedEarlier(p, t, self.Stage.CurrentScenarioNr) \
                                                    * self.CoefficientBackorderyVariable[t][indexp]


        return righthandside

    def ComputeCurrentRightHandSide(self):

        righthandside = self.GetRHS()

        for tuple in self.NonZeroFixedEarlierProductionVar:
            p = tuple[0]
            t = tuple[1]
            righthandside = righthandside - self.Stage.SDDPOwner.GetSetupFixedEarlier(p, t,
                                                                                      self.Stage.CurrentScenarioNr) \
                                            * self.CoefficientProductionVariable[t][p]

        for tuple in self.NonZeroFixedEarlierQuantityVar:
            p = tuple[0]
            t = tuple[1]
            righthandside = righthandside - self.Stage.SDDPOwner.GetQuantityFixedEarlier(p, t,
                                                                                         self.Stage.CurrentScenarioNr) \
                                            * self.CoefficientQuantityVariable[t][p]
        for tuple in self.NonZeroFixedEarlierBackOrderVar:
            p = tuple[0]
            t = tuple[1]
            indexp = self.Instance.ProductWithExternalDemandIndex[p]
            righthandside = righthandside - self.Stage.SDDPOwner.GetBackorderFixedEarlier(p, t,
                                                                                          self.Stage.CurrentScenarioNr) \
                                            * self.CoefficientBackorderyVariable[t][indexp]

        for tuple in self.NonZeroFixedEarlierStockVar:
            p = tuple[0];
            t = tuple[1]
            righthandside = righthandside - self.Stage.SDDPOwner.GetInventoryFixedEarlier(p, t,
                                                                                          self.Stage.CurrentScenarioNr) \
                                            * self.CoefficientStockVariable[t][p]
        return righthandside

    #Increase the coefficient of the quantity variable for product and time  by value
    def IncreaseCoefficientQuantity(self, product, time, value):
        self.CoefficientQuantityVariable[time][product] =self.CoefficientQuantityVariable[time][product] + value

        if time < self.Stage.GetTimePeriodAssociatedToQuantityVariable( product ):
            self.NonZeroFixedEarlierQuantityVar.add( ( product, time) )


    #Increase the coefficient of the quantity variable for product and time  by value
    def IncreaseCoefficientProduction(self, product, time, value):
        self.CoefficientProductionVariable[time][product] =self.CoefficientProductionVariable[time][product] + value

        if not self.Stage.IsFirstStage():
            self.NonZeroFixedEarlierProductionVar.add((product, time))


        #Increase the coefficient of the quantity variable for product and time  by value
    def IncreaseCoefficientInventory(self, product, time, value):
        self.CoefficientStockVariable[time][product] =self.CoefficientStockVariable[time][product] + value
        if time < self.Stage.GetTimePeriodAssociatedToInventoryVariable( product ):
            self.NonZeroFixedEarlierStockVar.add((product, time))
    #Increase the coefficient of the quantity variable for product and time  by value
    def IncreaseCoefficientBackorder(self, product, time, value):
        indexp = self.Instance.ProductWithExternalDemandIndex[product]
        self.CoefficientBackorderyVariable[time][indexp] =self.CoefficientBackorderyVariable[time][indexp] + value

        if time < self.Stage.GetTimePeriodAssociatedToBackorderVariable( product ):
            self.NonZeroFixedEarlierBackOrderVar.add( ( product, time) )

        # Increase the coefficient of the quantity variable for product and time  by value

    def IncreaseDemandRHS(self, value):
         self.DemandRHS = self.DemandRHS + value

    def IncreaseCapacityRHS(self, value):
        self.CapacityRHS = self.CapacityRHS + value

    def IncreasePReviousCutRHS(self, value):
        self.PreviousCutRHS = self.PreviousCutRHS + value

    def IncreaseInitInventryRHS(self, value):
        self.InitialInventoryRHS = self.InitialInventoryRHS + value

    def DivideAllCoeff (self, diviser ):

        self.DemandRHS = self.DemandRHS / diviser
        self.CapacityRHS = self.CapacityRHS / diviser
        self.PreviousCutRHS = self.PreviousCutRHS / diviser
        self.InitialInventoryRHS = self.InitialInventoryRHS / diviser

        for p in self.Instance.ProductSet:
            for t in self.Instance.TimeBucketSet:
                self.CoefficientQuantityVariable[t][p] =  self.CoefficientQuantityVariable[t][p] / diviser
                self.CoefficientProductionVariable[t][p] =  self.CoefficientProductionVariable[t][p] / diviser
                self.CoefficientStockVariable[t][p] =  self.CoefficientStockVariable[t][p] / diviser
                if self.Instance.HasExternalDemand[p]:
                    indexp = self.Instance.ProductWithExternalDemandIndex[p]
                    self.CoefficientBackorderyVariable[t][indexp] =  self.CoefficientBackorderyVariable[t][indexp] / diviser

    def GetCostToGoLBInCUrrentSolution(self, sol):
        variablofstage = self.GetCutVariablesAtStage()
        #REmove cost to go
        variablofstage = variablofstage[1:]
        valueofvariable = sol.get_values(variablofstage)
        #coefficient of the variable a
        coefficientvariableatstage =self.GetCutVariablesCoefficientAtStage()
        coefficientvariableatstage = coefficientvariableatstage[1:]
        valueofvarsinconsraint = sum(i[0] * i[1] for i in zip(valueofvariable, coefficientvariableatstage))

        RHS = self.ComputeCurrentRightHandSide()

        costtogo = RHS -valueofvarsinconsraint
        return costtogo
