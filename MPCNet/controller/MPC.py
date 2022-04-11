#!/usr/bin/env python3

import pyomo.environ as pyo
import numpy as np
import matplotlib.pyplot as plt

# MPC Hyper Parameters
class MPCParams():
    # Main Params
    H = 2 # [sec] Time horizon
    dt = 0.01 # [sec] MPC sampling time
    # Objective Params:
    R = np.diag([100.0, 100.0])
    Q = np.diag([5.0, 5.0, 0.0, 0.0])
    Qf = np.diag([10000.0, 10000.0, 100.0, 100000.0])


# Controller class for MPC
# Callable: MPC(x0) -> u = (v_dot, psi_dot)
class MPC():
    def __init__(self, goalState, params=MPCParams(), plot=False):
        # Store goal state
        self.xf = goalState # [x y v psi]
        # Store main parameters
        self.H = params.H # [sec] Time horizon
        self.dt = params.dt # [sec] MPC sampling time
        self.N = round(self.H/self.dt) # Number of samples
        self.plot = plot # Generate a plot each __call__?
        # Store objective parameters
        self.obj = self._ncvx_obj # Specify which obj to use
        self.Q = params.Q # State path weight matrix
        self.R = params.R # Input path weight matrix
        self.Qf = params.Qf # State terminal weight matrix

        # Initialize model and solver
        self.opt = pyo.SolverFactory('ipopt') # Optimizer
        self.model = self._init_model()

    # Solve the MPC problem with initial state x0 and return u0
    def __call__(self, x0):
        # Initialize parameter
        self.model.x0[0] = x0[0]
        self.model.x0[1] = x0[1]
        self.model.x0[2] = x0[2]
        self.model.x0[3] = x0[3]
        #x0_d = {0: x0[0], 1: x0[1], 2:x0[2], 3:x0[3]}
        #self.model.x0 = pyo.Param(range(4), initialize=x0_d)
        # Solve problem
        self.opt.solve(self.model)

        # Retrieve input u0
        u0 = self.model.input[0,0].value
        u1 = self.model.input[0,1].value

        # Plot
        if self.plot:
            self._plot()

        # Return u0
        return np.array([u0, u1])


    # Interval constraints on u
    def _input_bounds(self, model, t, i):
        if i == 0: # v_dot
            return(-1.5, 1.0)
        else: # psi_dot
            return(-0.7, 0.7)

    # Interval constraints on x
    def _state_bounds(self, model, t, i):
        if i == 0: # x
            return(None, None)
        elif i == 1: # y
            return(None, None)
        elif i == 2: # v
            return(0.0, 32.0)
        else: # psi
            return(None, None)

    # Nonconvex Objective
    def _ncvx_obj(self, model):
        term_expr = self.Qf[0][0]*(model.state[self.N,0] - self.xf[0])**2 + \
                self.Qf[1][1]*(model.state[self.N,1] - self.xf[1])**2 + \
                self.Qf[2][2]*(model.state[self.N,2] - self.xf[2])**2 + \
                self.Qf[3][3]*(model.state[self.N,3] - self.xf[3])**2
        accsum_expr = sum([dv**2 for dv in model.input[:,0]])
        angsum_expr = 0.0
        for k in range(self.N):
            angsum_expr += (model.state[k,2]**2)*(model.input[k,1]**2)

        # Add all costs
        obj = pyo.Objective(expr = term_expr + accsum_expr + angsum_expr)

        return obj

    # Convex Objective
    def _cvx_obj(self, model):
        obj = pyo.Objective(expr =
                self.Qf[0][0]*(model.state[n-1,0] - self.xf[0])**2 +
                self.Qf[1][1]*(model.state[n-1,1] - self.xf[1])**2 +
                self.Qf[2][2]*(model.state[n-1,2] - self.xf[2])**2 +
                self.Qf[3][3]*(model.state[n-1,3] - self.xf[3])**2 +
                self.Q[0][0]*sum([(s - self.xf[0])**2 for s in
                    model.state[:,0]]) +
                self.Q[1][1]*sum([(s - self.xf[1])**2 for s in
                    model.state[:,1]]) +
                self.Q[2][2]*sum([(s - self.xf[2])**2 for s in
                    model.state[:,2]]) +
                self.Q[3][3]*sum([(s - self.xf[3])**2 for s in
                    model.state[:,3]]) +
                self.R[0][0]*sum([c**2 for c in model.input[:,0]]) +
                self.R[1][1]*sum([c**2 for c in model.input[:,1]]))
        return obj

    # Create and initialize Pyomo model
    def _init_model(self):
        model = pyo.ConcreteModel()
        model.limits = pyo.ConstraintList()

        # Optimization variables
        model.state = pyo.Var(range(self.N+1), range(4),
                domain=pyo.Reals, bounds=self._state_bounds)
        model.input = pyo.Var(range(self.N), range(2),
                domain=pyo.Reals, bounds=self._input_bounds)

        # Optimization parameters
        model.x0 = pyo.Param(range(4), within=pyo.Reals, mutable=True)

        # Initial conditions
        model.limits.add(model.state[0,0] == model.x0[0])
        model.limits.add(model.state[0,1] == model.x0[1])
        model.limits.add(model.state[0,2] == model.x0[2])
        model.limits.add(model.state[0,3] == model.x0[3])

        # Dynamics Constraints
        for k in range(self.N):
            model.limits.add(model.state[k+1,0] == model.state[k,0] +\
                    self.dt*model.state[k,2]*pyo.cos(model.state[k,3]))
            model.limits.add(model.state[k+1,1] == model.state[k,1] +\
                    self.dt*model.state[k,2]*pyo.sin(model.state[k,3]))
            model.limits.add(model.state[k+1,2] == model.state[k,2] +\
                    self.dt*model.input[k,0])
            model.limits.add(model.state[k+1,3] == model.state[k,3] +\
                    self.dt*model.input[k,1])

        # Get obj function
        model.OBJ = self.obj(model)

        # Return model
        return model


    # Create 'mpc_traj.png'
    def _plot(self):
        xs = np.array([self.model.state[t,0].value for t in range(self.N)])
        ys = np.array([self.model.state[t,1].value for t in range(self.N)])
        vs = np.array([self.model.state[t,2].value for t in range(self.N)])
        hs = np.array([self.model.state[t,3].value for t in range(self.N)])
        plt.plot(xs, ys)
        axes_equal = False
        if axes_equal:
            all_min = min(np.min(xs), np.min(ys)) - 0.5
            all_max = max(np.max(xs), np.max(ys)) + 0.5
            plt.xlim([all_min, all_max])
            plt.ylim([all_min, all_max])
        else:
            plt.xlim([np.min(xs)-0.5, np.max(xs)+0.5])
            plt.ylim([np.min(ys)-0.5, np.max(ys)+0.5])
        plt.savefig("traj.png")


