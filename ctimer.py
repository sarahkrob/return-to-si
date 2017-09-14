import timeit as ti

#------------------------------------------------------------------------------
# CTimer class -- simple scope-based timer
class CTimer:
    def __init__(self, debugprint=True):
        self.debugprint = debugprint
        self.start = ti.default_timer()

    def __del__(self):
        if (self.debugprint):
            os = "{:.5f}".format(time_it.default_timer() - self.create)
            print "Total Elapsed:", os
#------------------------------------------------------------------------------
