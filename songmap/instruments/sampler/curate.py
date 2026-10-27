"""Compile a reviewed, fixed playing mode, retaining the original upstream program.

This is installation-time preparation, not live MIDI controller support. Every discarded
operation is explicit in the pinned manifest; unexpected features still fail installation.
"""
from __future__ import annotations

import os
from pathlib import Path
import re

from ...parse.errors import SongError
from . import sfz


def prepare(source: Path, target: Path, profile: dict) -> None:
    raw, headers = sfz.effective_regions(str(source))
    unknown = headers - set(profile.get('drop_headers', []))
    if unknown:
        raise SongError(f"{source}: unreviewed SFZ headers: {', '.join(sorted(unknown))}")
    cc = {int(k):int(v) for k,v in profile.get('cc',{}).items()}
    channel = int(profile.get('channel',1))
    switch = profile.get('keyswitch')
    output = ['// Prepared fixed program; original source and preparation profile are in songmap-library.json.']
    for original in raw:
        ops = dict(original)
        if any(k.startswith(('on_locc','on_hicc')) for k in ops):
            continue                         # controller events must never become ordinary note attacks
        if not int(ops.get('lochan',1)) <= channel <= int(ops.get('hichan',16)):
            continue
        if 'sw_last' in ops and (switch is None or sfz.note_number(ops['sw_last']) != int(switch)):
            continue
        bounds = [(k,re.fullmatch(r'(lo|hi)cc(\d+)',k)) for k in ops]
        if any((cc.get(int(m[2]),0) < float(ops[k]) if m[1]=='lo' else cc.get(int(m[2]),0) > float(ops[k]))
               for k,m in bounds if m):
            continue
        # Controller gates and keyswitch metadata have now been resolved, not ignored at playback.
        for k in list(ops):
            if re.fullmatch(r'(lo|hi)cc\d+',k) or k in ('lochan','hichan','sw_last','sw_lokey','sw_hikey','sw_default'):
                del ops[k]
        for k in profile.get('drop',[]):
            ops.pop(k,None)
        ops.update({k:str(v) for k,v in profile.get('set',{}).items()})
        sample = source.parent / ops.get('default_path','').replace('\\','/') / ops['sample'].replace('\\','/')
        ops['sample'] = Path(os.path.relpath(sample.resolve(),target.parent.resolve())).as_posix()
        ops.pop('default_path',None)
        extra = {k for k in ops if k not in sfz.SUPPORTED and not re.fullmatch(r'amp_velcurve_\d+',k)}
        if extra:
            raise SongError(f"{source}: unreviewed SFZ features: {', '.join(sorted(extra))}")
        output.append('<region> '+' '.join(f'{k}={v}' for k,v in ops.items()))
    if len(output)==1:
        raise SongError(f'{source}: fixed program selected no samples')
    # Check before writing; a failed preparation must not replace a working program.
    unsupported = set()
    for line in output[1:]:
        sfz._region(dict(sfz._opcodes(line)),str(target.parent),str(target),unsupported)
    if unsupported:
        raise SongError(f'{source}: unsupported fixed program: {sorted(unsupported)}')
    target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text('\n'.join(output)+'\n',encoding='utf-8')
