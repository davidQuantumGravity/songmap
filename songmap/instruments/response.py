"""Optional measured instrument gain. One fixed gain preserves all recorded dynamics."""
from __future__ import annotations

from functools import lru_cache
import hashlib
import json
from pathlib import Path

import numpy as np
import yaml

from .base import Param

CALIBRATION=Param('calibration',0,0,1,'','lin','response','0 original response; 1 measured reference gain; preserves soft/loud ratios')
PATH=Path(__file__).with_name('response.yaml')


@lru_cache(maxsize=4)
def _read(stamp):return yaml.safe_load(PATH.read_text(encoding='utf-8')).get('profiles',{}) if PATH.is_file() else {}


def profiles():return _read(PATH.stat().st_mtime_ns if PATH.is_file() else 0)


def profile(inst):return profiles().get(getattr(inst,'response_ref',''),{})


def fingerprint(inst):
    # Include source profiles even when calibration arrives through note/style overrides.
    data=profiles() if hasattr(inst,'layers') or hasattr(inst,'choices') else profile(inst)
    return hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest() if data else None


def apply(inst,note,audio):
    amount=note.params.get('calibration',inst.p.get('calibration',0))
    if not amount:return audio
    p=profile(inst)
    if not p:return audio
    gain=float(p.get('gain_db',0))*float(np.clip(amount,0,1))
    return audio if gain==0 else audio*10**(gain/20)
