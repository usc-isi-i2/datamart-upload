from datamart_isi.profilers.basic_profiler import BasicProfiler
from datamart_isi.profilers.dsbox_profiler import DSboxProfiler
from datamart_isi.profilers.two_ravens_profiler import TwoRavensProfiler


class Profiler(object):

    def __init__(self):
        self.basic_profiler = BasicProfiler()
        self.dsbox_profiler = DSboxProfiler()
        self.two_ravens_profiler = TwoRavensProfiler()
