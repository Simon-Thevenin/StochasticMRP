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

columnname = ["Instance name",
              "Model",
              "Scenario from YQFix",
              "Policy generation",
              "Distribution",
              "NrInSampleScenario",
              "Scenario Geeration Method",
              "Identificator",
              "Mean",
              "Variance",
              "Covariance",
              "LB",
              "UB",
              "Min Average",
              "Max Average",
              "Error"
              ]

all_data = pd.DataFrame(columns=columnname)
# Add the content of each csv file at the end of the dataframe
for f in glob.glob("./Test/Bounds/*.csv"):
    df = pd.read_csv(f, names=columnname)
    df.columns = columnname
    all_data = all_data.append(df, ignore_index=True)


writer = pd.ExcelWriter("./Test/Bounds/TestResultBounds.xlsx", engine='openpyxl')
all_data.to_excel(writer, "Res")
writer.save()

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
              "Stock level 5"
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
              "In Sample KPI Backorder",
              "In Sample KPI Lost sales",
              "In Sample Stock level 1",
              "In Sample Stock level 2",
              "In Sample Stock level 3",
              "In Sample Stock level 4",
              "In Sample Stock level 5",
              "Expected Out Sample",
              "LB",
              "UB",
              "Min Average",
              "Max Average",
              "Error",
              "SetupCost",
              "Inventory",
              "Out Sample KPI On Time",
              "Out Sample KPI Backorder",
              "Out Sample KPI Lost sales",
              "Out Sample Stock level 1",
              "Out Sample Stock level 2",
              "Out Sample Stock level 3",
              "Out Sample Stock level 4",
              "Out Sample Stock level 5"
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