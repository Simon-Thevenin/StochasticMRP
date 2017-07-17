#This script aggregates all the csv file in the folder Test.

import openpyxl as opxl
import pandas as pd
import glob as glob
columnname = ["Instance name",
              "Distribution",
              "Model",
              "Method",
              "Scenario Generation",
              "NrInSampleScenario",
              "Seed",
              "Policy generation",
              "NrOutSampleScenario",
               "Cplex solution value",
               "Solution cost",
               "Cplex_status",
               "Build time",
               "Solve time",
               "Cplex gap",
               "Cplex Nr iteration",
               "Cplex Nr nodes",
               "Cplex best node nr",
               "Cplex Nr Variable",
               "Cplex Nr constraint",
               "Inventory Cost",
               "BackOrder cost",
               "Setup cost",
               "In sample Average", 
               "In Sample Standard deviation",
               "Nr level",
               "Nr product",
               "Nr time Period",
               "Demand Tree Seed",
			   "Nr Scenario",
               "Max lead time",
			   "BranchingStrategy",
               "Demand Distribuion",
			   "UseNonAnticipativity",
			   "Model",
			   "UseSlowMoving",
			   "ScenarioSeed"		   
			   ]
			  
all_data = pd.DataFrame(  columns = columnname )
#Add the content of each csv file at the end of the dataframe
for f in glob.glob("./Test/SolveInfo/*.csv"):
    df = pd.read_csv( f, names= columnname )
    df.columns = columnname
    all_data = all_data.append(df,  ignore_index = True)


writer = pd.ExcelWriter( "./Test/SolveInfo/TestResultSolveInfo.xlsx", engine='openpyxl' )
all_data.to_excel( writer, "Res" )
writer.save( )

# columnname = ["Instance name",
#               "Distribution",
#               "Model",
#               "Method",
#               "Scenario Generation",
#               "NrInSampleScenario",
#               "Seed",
#               "Policy generation",
#               "NrOutSampleScenario",
#               "Identificator",
#               "Mean",
#               "Variance",
#               "Covariance",
#               "LB",
#               "UB",
#               "Min Average",
#               "Max Average",
#               "Error"
#               ]
#
# all_data = pd.DataFrame(columns=columnname)
# # Add the content of each csv file at the end of the dataframe
# for f in glob.glob("./Test/Bounds/*.csv"):
#     df = pd.read_csv(f, names=columnname)
#     df.columns = columnname
#     all_data = all_data.append(df, ignore_index=True)
#
#
# writer = pd.ExcelWriter("./Test/Bounds/TestResultBounds.xlsx", engine='openpyxl')
# all_data.to_excel(writer, "Res")
# writer.save()

columnname = ["Instance name",
              "Model",
              "Scenario from YQFix",
              "Policy generation",
              "Distribution",
              "NrInSampleScenario",
              "Scenario Geeration Method",
              " Whatever ",
              "Nr Scenario",
              "KPI On Time",
              "KPI Backorder",
              "KPI Lost sales",
              "Stock level 1",
              "Stock level 2",
              "Stock level 3",
              "Stock level 4",
              "Stock level 5",
              "BackOrder For 1 Period",
              "BackOrder For 2 Period",
              "BackOrder For 3 Period",
              "BackOrder For 4 Period",
              "BackOrder For 5 Period",
              "BackOrder For 6 Period",
              "BackOrder For 7 Period",
              "BackOrder For 8 Period",
              "BackOrder For 9 Period",
              "BackOrder For 10 Period",
              "Lost Sale"
              ]

all_data = pd.DataFrame(columns=columnname)
# Add the content of each csv file at the end of the dataframe
for f in glob.glob("./Test/Statistic/*.csv"):
    df = pd.read_csv(f, names=columnname)
    df.columns = columnname
    all_data = all_data.append(df, ignore_index=True)

writer = pd.ExcelWriter("./Test/Statistic/TestResultStatistic.xlsx", engine='openpyxl')
all_data.to_excel(writer, "Res")
writer.save()


columnname = ["Instance name",
              "Distribution",
              "Model",
              "Method",
              "Scenario Generation Method",
              "NrInSampleScenario",
              "Seed",
              "Policy generation",
              "Policy generation2",
              "NrOutSampleScenario",
              "Expected In Sample",
              "CPLEX Time",
              "CPLEX Gap",
              "SetupCost",
              "Inventory",
              "In Sample KPI On Time",
              "Backorder cost",
              "Lost sales cost",
              "Inventory cost stochastic period  ",
              "Setup cost stochastic period  ",
              "Backorder cost stochastic period  ",
              "In Sample Stock level 1",
              "In Sample Stock level 2",
              "In Sample Stock level 3",
              "In Sample Stock level 4",
              "In Sample Stock level 5",
              "In Sample BackOrder For 1 Period",
              "In Sample BackOrder For 2 Period",
              "In Sample BackOrder For 3 Period",
              "In Sample BackOrder For 4 Period",
              "In Sample BackOrder For 5 Period",
              "In Sample BackOrder For 6 Period",
              "In Sample BackOrder For 7 Period",
              "In Sample BackOrder For 8 Period",
              "In Sample BackOrder For 9 Period",
              "In Sample BackOrder For 10 Period",
              "In Sample BackOrder For 11 Period",
              "In Sample BackOrder For 12 Period",
              "In Sample BackOrder For 13 Period",
              "In Sample BackOrder For 14 Period",
              "In Sample BackOrder For 15 Period",
              "In Sample BackOrder For 16 Period",
              "In Sample BackOrder For 17 Period",
              "In Sample BackOrder For 18 Period",
              "In Sample BackOrder For 19 Period",
              "In Sample BackOrder For 20 Period",
              "In Sample BackOrder For 21 Period",
              "In Sample BackOrder For 22 Period",
              "In Sample BackOrder For 23 Period",
              "In Sample BackOrder For 24 Period",
              "In Sample BackOrder For 25 Period",
              "In Sample BackOrder For 26 Period",
              "In Sample BackOrder For 27 Period",
              "In Sample BackOrder For 28 Period",
              "In Sample BackOrder For 29 Period",
              "In Sample BackOrder For 30 Period",
              "In Sample BackOrder For 31 Period",
              "In Sample BackOrder For 32 Period",
              "In Sample BackOrder For 33 Period",
              "In Sample BackOrder For 34 Period",
              "In Sample BackOrder For 35 Period",
              "In Sample BackOrder For 36 Period",
              "In Sample BackOrder For 37 Period",
              "In Sample BackOrder For 38 Period",
              "In Sample BackOrder For 39 Period",
              "In Sample BackOrder For 40 Period",
              "In Sample BackOrder For 41 Period",
              "In Sample BackOrder For 42 Period",
              "In Sample BackOrder For 43 Period",
              "In Sample BackOrder For 44 Period",
              "In Sample BackOrder For 45 Period",
              "In Sample BackOrder For 46 Period",
              "In Sample BackOrder For 47 Period",
              "In Sample BackOrder For 48 Period",
              "In Sample BackOrder For 49 Period",
              "In Sample BackOrder For 50 Period",
              "In Sample Lost Sale",
              "Expected Out Sample",
              "LB",
              "UB",
              "Min Average",
              "Max Average",
              "Error",
              "SetupCost",
              "Inventory",
              "Out Sample KPI On Time",
              "backorder cost",
              "lostsales cost",
              "Inventory cost stochastic period  ",
              "Setup cost stochastic period  ",
              "Backorder cost stochastic period  ",
              "Out Sample Stock level 1",
              "Out Sample Stock level 2",
              "Out Sample Stock level 3",
              "Out Sample Stock level 4",
              "Out Sample Stock level 5",
              "In Sample BackOrder For 1 Period",
              "In Sample BackOrder For 2 Period",
              "In Sample BackOrder For 3 Period",
              "In Sample BackOrder For 4 Period",
              "In Sample BackOrder For 5 Period",
              "In Sample BackOrder For 6 Period",
              "In Sample BackOrder For 7 Period",
              "In Sample BackOrder For 8 Period",
              "In Sample BackOrder For 9 Period",
              "In Sample BackOrder For 10 Period",
              "In Sample BackOrder For 11 Period",
              "In Sample BackOrder For 12 Period",
              "In Sample BackOrder For 13 Period",
              "In Sample BackOrder For 14 Period",
              "In Sample BackOrder For 15 Period",
              "In Sample BackOrder For 16 Period",
              "In Sample BackOrder For 17 Period",
              "In Sample BackOrder For 18 Period",
              "In Sample BackOrder For 19 Period",
              "In Sample BackOrder For 20 Period",
              "In Sample BackOrder For 21 Period",
              "In Sample BackOrder For 22 Period",
              "In Sample BackOrder For 23 Period",
              "In Sample BackOrder For 24 Period",
              "In Sample BackOrder For 25 Period",
              "In Sample BackOrder For 26 Period",
              "In Sample BackOrder For 27 Period",
              "In Sample BackOrder For 28 Period",
              "In Sample BackOrder For 29 Period",
              "In Sample BackOrder For 30 Period",
              "In Sample BackOrder For 31 Period",
              "In Sample BackOrder For 32 Period",
              "In Sample BackOrder For 33 Period",
              "In Sample BackOrder For 34 Period",
              "In Sample BackOrder For 35 Period",
              "In Sample BackOrder For 36 Period",
              "In Sample BackOrder For 37 Period",
              "In Sample BackOrder For 38 Period",
              "In Sample BackOrder For 39 Period",
              "In Sample BackOrder For 40 Period",
              "In Sample BackOrder For 41 Period",
              "In Sample BackOrder For 42 Period",
              "In Sample BackOrder For 43 Period",
              "In Sample BackOrder For 44 Period",
              "In Sample BackOrder For 45 Period",
              "In Sample BackOrder For 46 Period",
              "In Sample BackOrder For 47 Period",
              "In Sample BackOrder For 48 Period",
              "In Sample BackOrder For 49 Period",
              "In Sample BackOrder For 50 Period",
              "Out Sample Lost Sale"
              ]

all_data = pd.DataFrame(columns=columnname)
# Add the content of each csv file at the end of the dataframe
for f in glob.glob("./Test/*.csv"):
    df = pd.read_csv(f, names=columnname)
    df.columns = columnname
    all_data = all_data.append(df, ignore_index=True)

#all_data.sort_values(by=["Instance name",
#                     "Distribution",
#                     "Model",
#                     "Scenario Generation Method",
#                     "NrInSampleScenario",
#                     "Seed",
#                     "Policy generation",
#                     "NrOutSampleScenario"])

writer = pd.ExcelWriter("./Test/TestResult.xlsx", engine='openpyxl')
all_data.to_excel(writer, "Res")
writer.save()