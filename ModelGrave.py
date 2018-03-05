import cplex

class ModelGrave(object):
    M = cplex.infinity

    # constructor

    def __init__(self, instance, owner ):

        self.Instance = instance
        self.Owner = owner
        self.nrvaluesS = 6
        self.NrVariable = len(self.Instance.TimeBucketSet) * self.Instance.NrProduct * self.nrvaluesS  * self.nrvaluesS
        self.Cplex = cplex.Cplex()
        self.XSSI = [ [ [ [ t + p * len(self.Instance.TimeBucketSet)
                            + s * self.Instance.NrProduct * len(self.Instance.TimeBucketSet)
                            + si * self.nrvaluesS  * self.Instance.NrProduct * len(self.Instance.TimeBucketSet)
                          for t in self.Instance.TimeBucketSet ]
                     for p in range( self.Instance.NrProduct ) ]
                   for s in range( self.nrvaluesS ) ]
                 for si in range( self.nrvaluesS ) ]


    def ComputeSSI(self):
        self.CreateVariable()
        self.CreateConstraints()
        s, si = self.Solve()

        return s, si

    def CreateVariable( self ):
        costXSSI = [    self.Owner.GetCostGrave(s, si, p, t)
                         for si in range(self.nrvaluesS)
                         for s in range(self.nrvaluesS)
                         for p in range(self.Instance.NrProduct)
                        for t in self.Instance.TimeBucketSet]



        NameXSSI = [ "Name_t_p_s_si_%s_%s_%s_%s"%(t, p, s, si)
                     for si in range(self.nrvaluesS)
                     for s in range(self.nrvaluesS)
                     for p in range(self.Instance.NrProduct)
                     for t in self.Instance.TimeBucketSet]

        # for si in range(self.nrvaluesS):
        #     for s in range(self.nrvaluesS):
        #         for p in range(self.Instance.NrProduct):
        #             for t in range(5, 6):
        #                 print " t_%s P_%s s_%s si_%s: %s " % (t,p,s,si,  self.Owner.GetCostGrave(s, si, p, t))

        self.Cplex.variables.add(costXSSI,
                                 types=['B'] * self.NrVariable,
                                 names = NameXSSI )
    def CreateConstraints(self):

        for t in self.Instance.TimeBucketSet:
            for p in range(self.Instance.NrProduct):
                 vars = [ self.XSSI[si][s][p][t] for s in range(self.nrvaluesS)  for si in range(self.nrvaluesS) ]
                 coeff = [1] * len(vars)

                 self.Cplex.linear_constraints.add( lin_expr=[ cplex.SparsePair(vars, coeff) ],
                                                    senses=[ "E" ],
                                                    rhs=[ 1 ] )

        #for t in self.Instance.TimeBucketSet:
        #    for p in range(self.Instance.NrProduct):
        #        vars = [self.XSSI[0][0][p][t] ]
        #        coeff = [1]#
#
#                self.Cplex.linear_constraints.add(lin_expr=[cplex.SparsePair(vars, coeff)],
#                                                  senses=["E"],
#                                                  rhs=[1])


        for t in self.Instance.TimeBucketSet:
            for p in range(self.Instance.NrProduct):
                for s in range(self.nrvaluesS):
                    for si in range(self.nrvaluesS):
                         if( ( self.Instance.HasExternalDemand[p] and s > 0 )
                             or ( s - si > self.Instance.Leadtimes[p] ) ):
                            vars = [self.XSSI[si][s][p][t]]
                            coeff = [1]

                            self.Cplex.linear_constraints.add(lin_expr=[cplex.SparsePair(vars, coeff)],
                                                              senses=["E"],
                                                              rhs=[0])


        for t in self.Instance.TimeBucketSet:
            for p in range(self.Instance.NrProduct):
                for q in range(self.Instance.NrProduct):
                    for sp in range(self.nrvaluesS):
                        for sip in range(self.nrvaluesS):
                            for sq in range(self.nrvaluesS):
                                for siq in range(self.nrvaluesS):
                                     if( sp > siq
                                         and self.Instance.Requirements[q][p] >0 ):
                                        vars = [self.XSSI[sip][sp][p][t], self.XSSI[siq][sq][q][t] ]
                                        coeff = [1,1]

                                        self.Cplex.linear_constraints.add(lin_expr=[cplex.SparsePair(vars, coeff)],
                                                                          senses=["L"],
                                                                          rhs=[1])


    def Solve(self):
        self.Cplex.objective.set_sense(self.Cplex.objective.sense.minimize)
        #if Constants.Debug:
        #self.Cplex.write("mrpoo.lp")

        # name = "mrp_log%r_%r_%r" % ( self.Instance.InstanceName, self.Model, self.DemandScenarioTree.Seed )
        # file = open("/tmp/thesim/CPLEXLog/%s.txt" % self.logfilename, 'w')

        self.Cplex.set_log_stream( None )
        self.Cplex.set_results_stream( None )
        self.Cplex.set_warning_stream( None )
        self.Cplex.set_error_stream( None )

        # tune the paramters
        self.Cplex.parameters.timelimit.set(1000)
        self.Cplex.parameters.mip.limits.treememory.set(700000000.0)
        self.Cplex.parameters.threads.set(1)
        #self.TuneCplexParamter()

        #if self.YFixHeuristic:
        #    self.Cplex.parameters.lpmethod.set(self.Cplex.parameters.lpmethod.values.barrier)
        #    self.Cplex.parameters.threads.set(1)

        #end_modeling = time.time();

        self.Cplex.solve()


        # Handle the results
        sol = self.Cplex.solution
        xssi = [ i for i in range( self.NrVariable ) ]

        values = sol.get_values(xssi)

        xssivalues = [[[[  values[ t + p * len(self.Instance.TimeBucketSet)
                                     + s * self.Instance.NrProduct * len(self.Instance.TimeBucketSet)
                                     + si * self.nrvaluesS * self.Instance.NrProduct * len(self.Instance.TimeBucketSet)]
                        for t in self.Instance.TimeBucketSet]
                       for p in range(self.Instance.NrProduct)]
                      for s in range(self.nrvaluesS)]
                     for si in range(self.nrvaluesS)]


        #print xssivalues

        S = [  [ -1 for p in range(self.Instance.NrProduct)] for t in self.Instance.TimeBucketSet ]
        SI = [ [ -1 for p in range(self.Instance.NrProduct)] for t in self.Instance.TimeBucketSet ]
        for t in self.Instance.TimeBucketSet:
            for p in range(self.Instance.NrProduct):
                for s in range(self.nrvaluesS):
                    for si in range(self.nrvaluesS):
                        if xssivalues[si][s][p][t] == 1:
                            SI[t][p]= si
                            S[t][p] = s

        return S, SI