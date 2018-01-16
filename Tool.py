
import itertools as itools
import pandas as pd

class Tool:

    #Append a list to another one only if the list to appebd is not empty
    @staticmethod
    def AppendIfNotEmpty( List1, List2):
        if len( List2 ) > 0:
            List1.append( List2 )

    #Create a 2d list from a 3d dataframe. The list contain the average over the  second index.
    #  The function assume that the column of the datafram are indexed with the value contained in  columnmap.
    @staticmethod
    def ComputeAverageOnIndex2( dataframe, columnset, columnmap, indexset1, indexset2):
        result = [ [ ( sum( dataframe.loc[ columnmap[ p ], (t,s)]
                       for s in indexset2 )
                   / len( indexset2 ) )
                  for p in columnset ]
                  for t in indexset1 ]
        return result

    #Create a 1d list from a 3d dataframe. The list contain the average over the  column and first indef index.
    #  The function assume that the column of the datafram are indexed with the value contained in  columnmap.
    @staticmethod
    def ComputeSumOnIndex1Column( dataframe, columnset, columnmap, indexset1, indexset2):
        result = [  ( sum ( sum( dataframe.loc[ columnmap[ p ], (t, s)]
                            for p in columnset )
                           for t in indexset1 )
                   )
                for s in indexset2]
        return result


    #This function transform the sheet given in arguments into a dataframe
    @staticmethod
    def ReadDataFrame( wb2, framename):
        sheet = wb2[framename];
        data =  sheet.values
        cols = next( data ) [ 1: ]
        cols = list( cols )
        #remove the None from the column names
        for i in range( len( cols ) ):
            if cols[i] == None :
                cols[i] = i

        data = list( data )
        idx = [ r[ 0 ] for r in data ]
        data = ( itools.islice(r, 1, None ) for r in data )
        df = pd.DataFrame( data, index=idx, columns=cols )
        return df;

    #This function transform the sheet given in arguments into a dataframe
    @staticmethod
    def ReadMultiIndexDataFrame( filename, sheetname):

        df = pd.read_excel(filename,
                      header=[0, 1],
                      index_col=[0],
                      sheetname=sheetname)

        return df;

    #This function transform the sheet given in arguments into a dataframe
    @staticmethod
    def Transform3d( array, dimension1, dimension2, dimension3):
        result = [ [ [ array[p * (dimension2 * dimension3) + t * dimension3 + w]
                          for p in range(dimension1) ]
                            for t in range(dimension2) ]
                              for w in range(dimension3) ]

        return result;

    # Compute the average (dependent) demand
    @staticmethod
    def ComputeInventoryEchelon(instance, prod, currrentstocklevel):

        echelonstock  = [ currrentstocklevel[p] for p in instance.ProductSet ]
        levelset = sorted(set(instance.Level), reverse=False)

        for l in levelset:
            prodinlevel = [p for p in instance.ProductSet if instance.Level[p] == l]
            for p in prodinlevel:
                echelonstock[p] = sum( echelonstock[q] * instance.Requirements[q][p] for q in instance.ProductSet) \
                                   + echelonstock[p]

        return echelonstock[prod]