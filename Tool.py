import numpy as np
import matplotlib.pyplot as plt
from Constants import Constants


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