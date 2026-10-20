"""DSP building blocks: oscillators, noise, envelopes, filters, physical models, fx kernels (numba)."""
from .core import SR, as_stereo, db, mtof, n_samples, pan_mono, t60_env, t_axis, undb
from .env import ad, adsr
from .filters import drive, eq, fold, onepole_lp, svf
from .fx import pingpong_delay
from .osc import phase, pink, saw, sine, square, supersaw, triangle, white
from .physical import ks_string, modal
