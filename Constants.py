
class Constants:
    Lumpy = "Lumpy"
    SlowMoving = "SlowMoving"
    Normal = "Normal"
    Uniform = "Uniform"
    Binomial = "Binomial"
    NearestNeighbor = "NN"
    NearestNeighborBasedOnDemandAC = "NNDAC"
    NearestNeighborBasedOnStateAC = "NNSAC"
    NearestNeighborBasedOnDemand = "NND"
    NearestNeighborBasedOnState = "NNS"
    InferS = "S"
    InferYS = "YS"
    NonStationary = "NonStationary"
    Resolve = "Re-solve"
    Fix = "Fix"
    ModelYQFix = "YQFix"
    ModelYFix = "YFix"
    ModelSFix = "SFix"
    ModelYSFix = "YSFix"
    ModelHeuristicYFix = "HeuristicYFix"
    Model_Fix = "_Fix"
    Average = "Average"
    AverageSS = "AverageSS"
    AverageSSGrave = "AverageSSGrave"
    MonteCarlo = "MC"
    RQMC = "RQMC"
    All = "all"
    Solve = "Solve"
    Evaluate = "Evaluate"
    VSS= "VSS"
    MIP = "MIP"
    SDDP = "SDDP"
    L4L = "L4L"
    EOQ  = "EOQ"
    POQ = "POQ"
    SilverMeal  = "SilverMeal"

    L4LGrave = "L4LGrave"
    EOQGrave  = "EOQGrave"
    POQGrave = "POQGrave"
    SilverMealGrave  = "SilverMealGrave"

    RollingHorizon = "RH"

    Debug = False
    PrintSolutionFileToExcel = False
    PrintDebugLPFiles = False
    LauchEvalAfterSolve = True
    # When PrintOnlyFirstStageDecision is True, only the implemented decision are saved in an Excel File. This is necessary when a large number of scenario is consider, as the size of the Excel file would be to Large.
    # Turn PrintOnlyFirstStageDecision to False for debug purpose (allows to see the detail solution). Also statistics about the "in sample" solution are computed.
    PrintOnlyFirstStageDecision = True
    PrintDetailsExcelFiles = False
    # To avoid memory comsumption it is better to print the files in /tmp However if the files are printed in tmp they are deleted after 4 days
    PrintSolutionFileInTMP = True
    RunEvaluationInSeparatedJob = False
    PrintScenarios = False
    Infinity = 9999999999999.9
    AlgorithmTimeLimit = 36000.0
    AlgorithmOptimalityTolerence = 0.00001
    SDDPIterationLimit = 10000


    @staticmethod
    def IsRule( s ):

       result =  s in [ Constants.L4L, Constants.EOQ, Constants.POQ, Constants.SilverMeal]\
                 or Constants.IsRuleWithGrave(s)
       return result

    @staticmethod
    def IsRuleWithGrave( s ):
       result =   s in [ Constants.L4LGrave, Constants.EOQGrave, Constants.POQGrave, Constants.SilverMealGrave]
       return result