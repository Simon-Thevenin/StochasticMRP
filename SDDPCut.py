import cplex
class SDDPCut:

    def __init__( self, owner = None   ):
        self.Stage = owner
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
        self.CPlexConstraint = None
        #self.LastAddedConstraintIndex = 0

        #This function add the cut to the MIP
    def AddCut(self):
        print "Add the Cut %s" %self.Name

        vars = [self.Stage.GetIndexQuantityVariable(p) for p in self.Instance.ProductSet] \
               + [self.Stage.GetIndexStockVariable(p) for p in self.Instance.ProductSet] \
               + [self.Stage.GetIndexBackorderVariable(p) for p in self.Instance.ProductWithExternalDemand]

        #multiply by -1 because the variable goes on the left hand side
        coeff = [ -1 * self.CoefficientQuantityVariable[self.Stage.GetTimePeriodAssociatedToQuantityVariable(p)][p] for p in self.Instance.ProductSet] \
                + [-1 * self.CoefficientStockVariable[self.Stage.GetTimePeriodAssociatedToInventoryVariable(p)][p]for p in self.Instance.ProductSet] \
                + [-1 * self.CoefficientBackorderyVariable[self.Stage.GetTimePeriodAssociatedToBackorderVariable(p)][ self.Instance.ProductWithExternalDemandIndex[p]]
                    for p in self.Instance.ProductWithExternalDemand]

        if self.Stage.DecisionStage == 0 :
            vars = vars + [self.Stage.GetIndexProductionVariable(p) for p in self.Instance.ProductSet for t in self.Instance.TimeBucketSet]
            coeff = coeff + [self.CoefficientProductionVariable[p][t] for p in self.Instance.ProductSet for t in self.Instance.TimeBucketSet]

        righthandside = [ self.ComputeCurrentRightHandSide() ]

        self.Stage.Cplex.linear_constraints.add( lin_expr=[cplex.SparsePair(vars, coeff)],
                                           senses=["G"],
                                           rhs=righthandside,
                                           names =[self.Name] )

        self.Stage.IndexCutConstraint.append( self.Stage.LastAddedConstraintIndex )
        self.Stage.LastAddedConstraintIndex = self.Stage.LastAddedConstraintIndex + 1

        self.Stage.ConcernedCutinConstraint.append( self.Id)


    #This function modify the cut to take into account the Fixed variables
    def ModifyCut( self ):
        print "Modify the Cut "

        righthandside = [ self.ComputeCurrentRightHandSide() ]

        constrnr = self.Name
        constrainttuples=[(constrnr, righthandside) ]

        self.Stage.Cplex.linear_constraints.set_rhs(constrainttuples)

    def ComputeCurrentRightHandSide(self):

        righthandside =  self.DemandRHS


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
        print "Increase the Coefficient Quanitty"
        self.CoefficientQuantityVariable[time][product] =self.CoefficientQuantityVariable[time][product] + value

    #Increase the coefficient of the quantity variable for product and time  by value
    def IncreaseCoefficientProduction(self, product, time, value):
        print "Set Coefficient Production"
        self.CoefficientProductionVariable[time][product] =self.CoefficientProductionVariable[time][product] + value

    #Increase the coefficient of the quantity variable for product and time  by value
    def IncreaseCoefficientInventory(self, product, time, value):
        print "Set Coefficient Inventory"
        self.CoefficientStockVariable[time][product] =self.CoefficientStockVariable[time][product] + value

    #Increase the coefficient of the quantity variable for product and time  by value
    def IncreaseCoefficientBackorder(self, product, time, value):
        print "Set Coefficient Backorder"
        indexp = self.Instance.ProductWithExternalDemandIndex[product]
        self.CoefficientBackorderyVariable[time][indexp] =self.CoefficientBackorderyVariable[time][indexp] + value

        # Increase the coefficient of the quantity variable for product and time  by value

    def IncreaseDemandRHS(self, value):
        print "Set Coefficient Backorder"
        self.DemandRHS = self.DemandRHS + value

    def DivideAllCoeff (self, diviser ):

        for p in self.Instance.ProductSet:
            for t in self.Instance.TimeBucketSet:
                self.CoefficientQuantityVariable[t][p] =  self.CoefficientQuantityVariable[t][p] / diviser
                self.CoefficientProductionVariable[t][p] =  self.CoefficientQuantityVariable[t][p] / diviser
                self.CoefficientStockVariable[t][p] =  self.CoefficientQuantityVariable[t][p] / diviser
                if self.Instance.HasExternalDemand[p]:
                    indexp = self.Instance.ProductWithExternalDemandIndex[p]
                    self.CoefficientBackorderyVariable[t][indexp] =  self.CoefficientQuantityVariable[t][indexp] / diviser