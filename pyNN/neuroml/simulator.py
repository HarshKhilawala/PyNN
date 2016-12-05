from pyNN import common
from pyNN import __version__

import logging

name = "NeuroML2Converter"

import neuroml
from pyneuroml.lems.LEMSSimulation import LEMSSimulation

nml_doc = None
lems_sim = None

logger = logging.getLogger("PyNN_NeuroML")

def get_nml_doc(reference="PyNN_NeuroML2_Export",reset=False):
    global nml_doc
    if nml_doc == None or reset:
        nml_doc = neuroml.NeuroMLDocument(id=reference)
        
    return nml_doc

def get_main_network():
    return get_nml_doc().networks[0]

def get_lems_sim(reference=None,reset=False):
    global lems_sim
    if reference == None:
        reference = get_nml_doc().id
    if lems_sim == None or reset:
        # Note: values will be over written
        lems_sim = LEMSSimulation("Sim_%s"%reference, 100, 0.01, target="network",comment="This LEMS file has been generated from PyNN v%s"%__version__)
    return lems_sim

class ID(int, common.IDMixin):
    def __init__(self, n):
        """Create an ID object with numerical value `n`."""
        int.__init__(n)
        common.IDMixin.__init__(self)

class State(common.control.BaseState):
    def __init__(self):
        logger.debug("State initialised!")
        common.control.BaseState.__init__(self)
        self.mpi_rank = 0
        self.num_processes = 1
        self.clear()
        self.dt = 0.1
    def run(self, simtime):
        self.t += simtime
        self.running = True
    def run_until(self, tstop):
        logger.debug("run_until() called with %s"%tstop)
        lems_sim = get_lems_sim()
        lems_sim.duration = float(tstop)
        
        self.t = tstop
        self.running = True
    def clear(self):
        self.recorders = set([])
        self.id_counter = 42
        self.segment_counter = -1
        self.reset()
    def reset(self):
        """Reset the state of the current network to time t = 0."""
        self.running = False
        self.t = 0
        self.t_start = 0
        self.segment_counter += 1

state = State()
