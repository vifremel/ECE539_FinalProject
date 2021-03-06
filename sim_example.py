#!/bin/env python3

from NMPC_Net.simulation import simulation
import numpy as np
from NMPC_Net.controller import pyomo_controller
from functools import partial
from NMPC_Net.controller.MPC import MPC, MPCParams


### SIM EXAMPLE (10 Hz)
initial = np.array([0.0, 0.0, 5.0, 0.0])
#final = np.array([180.0, -84.0, 15.0, -1.85])
final = np.array([40.0, -10.0, 0.0, -np.pi/2])
controller = MPC()
sim = simulation.Simulation(initial, final, 10.0, controller, stop_r=0.5)
sim.run_simulation(20.0)
simulation.plot_path(sim, f"path_sim.png")
simulation.plot_input(sim, f"input_sim.png")
simulation.plot_state(sim, f"state_sim.png")


### PYOMO EXAMPLE
#initial = [70.0, 3.0, 10.0, 0.0]
#final = [100.0, 5.0, 0.0, 0.0]
#pyomo_controller.mpcController(initial, final, plot=True)


### PYOMO CLASS EXAMPLE
#initial = [70.0, 3.0, 10.0, 0.0]
#final = [100.0, 5.0, 0.0, 0.0]
#controller = MPC(final, plot=True)
#controller(initial)
