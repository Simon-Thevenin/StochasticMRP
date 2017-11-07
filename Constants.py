

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
    NonStationary = "NonStationary"
    Resolve = "Re-solve"
    Fix = "Fix"
    ModelYQFix = "YQFix"
    ModelYFix = "YFix"
    ModelHeuristicYFix = "HeuristicYFix"
    Model_Fix = "_Fix"
    Average = "Average"
    AverageSS = "AverageSS"
    MonteCarlo = "MC"
    RQMC = "RQMC"
    All = "all"
    Solve = "Solve"
    Evaluate = "Evaluate"
    VSS= "VSS"
    MIP = "MIP"
    SDDP = "SDDP"


    Debug = False
    PrintSolutionFileToExcel = False
    PrintDebugLPFiles = False
    LauchEvalAfterSolve = True
    # When PrintOnlyFirstStageDecision is True, only the implemented decision are saved in an Excel File. This is necessary when a large number of scenario is consider, as the size of the Excel file would be to Large.
    # Turn PrintOnlyFirstStageDecision to False for debug purpose (allows to see the detail solution). Also statistics about the "in sample" solution are computed.
    PrintOnlyFirstStageDecision = True
    PrintDetailsExcelFiles = False
    # To avoid memory comsumption it is better to print the files in /tmp However if the files are printed in tmp they are deleted after 4 days
    PrintSolutionFileInTMP = False
    Infinity = 9999999999999.9
    AlgorithmTimeLimit = 36000.0
    AlgorithmOptimalityTolerence = 0.00001
    SDDPIterationLimit = 10000