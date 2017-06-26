import cplex
from Constants import Constants
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
        self.NonZeroFixedEarlierQuantityVar = []
        self.NonZeroFixedEarlierProductionVar = []
        self.NonZeroFixedEarlierStockVar = []
        self.NonZeroFixedEarlierBackOrderVar = []


        self.DemandRHS = 0.0
        self.CapacityRHS = 0.0
        self.PreviousCutRHS = 0.0
        self.CPlexConstraint = None
        #self.LastAddedConstraintIndex = 0

        #This function add the cut to the MIP
    def AddCut(self):
        if Constants.Debug:
            print "Add the Cut %s" %self.Name

        vars = [ self.Stage.StartCostToGo] \
                + [self.Stage.GetIndexQuantityVariable(p) for p in self.Instance.ProductSet] \
                + [self.Stage.GetIndexStockVariable(p) for p in self.Stage.GetProductWithStockVariable() ]
        if not self.Stage.IsFirstStage():
            vars = vars + [self.Stage.GetIndexBackorderVariable(p) for p in self.Instance.ProductWithExternalDemand]


        #multiply by -1 because the variable goes on the left hand side
        coeff =  [1] \
                 +  [ self.CoefficientQuantityVariable[self.Stage.GetTimePeriodAssociatedToQuantityVariable(p)][p] for p in self.Instance.ProductSet] \
                + [ self.CoefficientStockVariable[self.Stage.GetTimePeriodAssociatedToInventoryVariable(p)][p]for p in self.Stage.GetProductWithStockVariable()]

        if not self.Stage.IsFirstStage():
            coeff = coeff + [ self.CoefficientBackorderyVariable[self.Stage.GetTimePeriodAssociatedToBackorderVariable(p)][ self.Instance.ProductWithExternalDemandIndex[p]]
                        for p in self.Instance.ProductWithExternalDemand]


        if self.Stage.DecisionStage == 0 :
            vars = vars + [self.Stage.GetIndexProductionVariable(p, t) for p in self.Instance.ProductSet for t in self.Instance.TimeBucketSet]
            coeff = coeff + [self.CoefficientProductionVariable[t][p] for p in self.Instance.ProductSet for t in self.Instance.TimeBucketSet]

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
        constrainttuples=[(constrnr, righthandside) ]

        self.Stage.Cplex.linear_constraints.set_rhs(constrainttuples)


    def GetRHS(self):
        righthandside = self.DemandRHS
        righthandside = righthandside + self.CapacityRHS
        righthandside = righthandside + self.PreviousCutRHS
        return righthandside

    def ComputeCurrentRightHandSide(self):

        righthandside =  self.GetRHS()

        for p in self.Instance.ProductSet:
            for t in range(1,self.Stage.GetTimePeriodAssociatedToQuantityVariable( p )):
                righthandside =  righthandside +  self.Stage.SDDPOwner.GetQuantityFixedEarlier(p,t, self.Stage.CurrentScenarioNr) \
                                                  * self.CoefficientQuantityVariable[t][p]


        for p in self.Instance.ProductSet:
            for t in self.Instance.TimeBucketSet[1:]:
                righthandside = righthandside + self.Stage.SDDPOwner.GetSetupFixedEarlier(p, t, self.Stage.CurrentScenarioNr)\
                                                * self.CoefficientProductionVariable[t][p]


        for p in self.Instance.ProductSet:
            for t in range(1, self.Stage.GetTimePeriodAssociatedToInventoryVariable(p)):
                righthandside = righthandside + self.Stage.SDDPOwner.GetInventoryFixedEarlier(p, t, self.Stage.CurrentScenarioNr) \
                                                * self.CoefficientStockVariable[t][p]

        for p in self.Instance.ProductWithExternalDemand:
            for t in range(1,self.Stage.GetTimePeriodAssociatedToBackorderVariable(p)):

                indexp = self.Instance.ProductWithExternalDemandIndex[p]
                righthandside = righthandside + self.Stage.SDDPOwner.GetBackorderFixedEarlier(p, t, self.Stage.CurrentScenarioNr) \
                                                * self.CoefficientBackorderyVariable[t][indexp]


        return righthandside


    #Increase the coefficient of the quantity variable for product and time  by value
    def IncreaseCoefficientQuantity(self, product, time, value):
        self.CoefficientQuantityVariable[time][product] =self.CoefficientQuantityVariable[time][product] + value

        if time <> self.Stage.GetTimePeriodAssociatedToQuantityVariable( product ):
            self.NonZeroFixedEarlierQuantityVar.append( ( product, time) )


    #Increase the coefficient of the quantity variable for product and time  by value
    def IncreaseCoefficientProduction(self, product, time, value):
        self.CoefficientProductionVariable[time][product] =self.CoefficientProductionVariable[time][product] + value

        if not self.Stage.IsFirstStage():
            self.NonZeroFixedEarlierProductionVar.append((product, time))


        #Increase the coefficient of the quantity variable for product and time  by value
    def IncreaseCoefficientInventory(self, product, time, value):
        self.CoefficientStockVariable[time][product] =self.CoefficientStockVariable[time][product] + value
        if time <> self.Stage.GetTimePeriodAssociatedToInventoryVariable( product ):
            self.NonZeroFixedEarlierStockVar.append((product, time))
    #Increase the coefficient of the quantity variable for product and time  by value
    def IncreaseCoefficientBackorder(self, product, time, value):
        indexp = self.Instance.ProductWithExternalDemandIndex[product]
        self.CoefficientBackorderyVariable[time][indexp] =self.CoefficientBackorderyVariable[time][indexp] + value

        if time <> self.Stage.GetTimePeriodAssociatedToBackorderVariable( product ):
            self.NonZeroFixedEarlierBackOrderVar.append( ( product, time) )

        # Increase the coefficient of the quantity variable for product and time  by value

    def IncreaseDemandRHS(self, value):
         self.DemandRHS = self.DemandRHS + value

    def IncreaseCapacityRHS(self, value):
        self.CapacityRHS = self.CapacityRHS + value

    def IncreasePReviousCutRHS(self, value):
       self.PreviousCutRHS = self.PreviousCutRHS + value

    def DivideAllCoeff (self, diviser ):
        self.DemandRHS = self.DemandRHS / diviser
        self.CapacityRHS = self.CapacityRHS / diviser
        for p in self.Instance.ProductSet:
            for t in self.Instance.TimeBucketSet:
                self.CoefficientQuantityVariable[t][p] =  self.CoefficientQuantityVariable[t][p] / diviser
                self.CoefficientProductionVariable[t][p] =  self.CoefficientProductionVariable[t][p] / diviser
                self.CoefficientStockVariable[t][p] =  self.CoefficientStockVariable[t][p] / diviser
                if self.Instance.HasExternalDemand[p]:
                    indexp = self.Instance.ProductWithExternalDemandIndex[p]
                    self.CoefficientBackorderyVariable[t][indexp] =  self.CoefficientBackorderyVariable[t][indexp] / diviser