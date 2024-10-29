import pickle

import numpy as np
import torch

from torchdiffeq import odeint

from matrace.helper import import_matlab_func


def _p(s): return f'./tests/matlab_examples/{s}.m'
def _s(s): return f'./tests/matlab_examples/{s}.pkl'


ode_lorenz = import_matlab_func(_p('ode_lorenz'))
ode_simple = import_matlab_func(_p('ode_simple'))
ode_msd_system = import_matlab_func(_p('ode_msd_system'))


class MSDSystem(torch.nn.Module):
  def __init__(self, m=1.0, c=0.5, k=2.5):
    super().__init__()
    self.m = torch.tensor([[m]])
    self.c = torch.tensor([[c]])
    self.k = torch.tensor([[k]])

  def forward(self, t, y):
    dydt: torch.Tensor = ode_msd_system(
        t, y[0], self.m, self.c, self.k
    )
    return torch.unsqueeze(dydt, 0)


def test_msd():

  with open(_s('ode_msd_system'), 'rb') as f:
    t_true, x_true, v_true = pickle.load(f)

  y0 = torch.tensor([1.0, 0.0]) \
      .unsqueeze(1).unsqueeze(0)  # col vec -> batch
  # t = torch.linspace(0, 20, 1000)
  t = torch.from_numpy(t_true)

  msd = MSDSystem()

  solution = odeint(msd, y0, t)  # (t, 1, 2, 1)
  padded_solution = solution[:, 0, :, 0]

  x = padded_solution[:, 0]
  v = padded_solution[:, 1]

  dx = np.sum(x.numpy() - x_true)
  dv = np.sum(v.numpy() - v_true)

  assert dx < 1e-15
  assert dv < 1e-15
