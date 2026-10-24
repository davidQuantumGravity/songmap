"""Redraw the five Golden Worlds videos, reusing their verified melody-revision-2 audio.

Run from the repository root. Optional positional names select individual songs.
The adjacent view specifies 1080p, performance cards and exact per-note names.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from songmap.arrange.expand import expand
from songmap.parse import load
from songmap.parse.fmt import song_to_raw
from songmap.visual import write_poster,write_video
from songmap.visual import view


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def render(stem):
    score=ROOT/'songs/golden_worlds'/(stem+'.sm')
    source=ROOT/'textbook/audio/ch51'/(stem+'.songmap.yaml')
    song=load(str(source));arr=expand(song)
    canonical=load(str(score))
    assert song_to_raw(song)==song_to_raw(canonical), 'chapter instruments/mix differ from the canonical score'
    assert arr.digest()==expand(canonical).digest()
    frozen=json.loads((ROOT/'archives/golden_worlds/v2_video_grid/music_unchanged.json').read_text())[stem]
    wav=ROOT/'songs/golden_worlds/renders'/stem/'song.wav'
    assert sha(score)==frozen['score_sha256'] and sha(wav)==frozen['wav_sha256']
    settings=view.resolve(view.load(str(source)))
    assert settings['size']==[1920,1080]
    assert all(layer.get('style')=='performance' for layer in settings['layers'] if layer['type']=='instrument')
    staged=ROOT/'build/performance_videos'
    staged.mkdir(parents=True,exist_ok=True)
    movie=staged/(stem+'.mp4')
    print('Drawing 1080p performance video:',stem,flush=True)
    write_video(song,str(movie),fps=30,audio_wav=str(wav),view=settings,crf=18,
                log=lambda line:print(stem,line,flush=True))
    start=min(arr.timeline.beat_to_sec(e.beat) for e in arr.parts['lead'])
    poster=movie.with_suffix('.jpg')
    write_poster(song,str(poster),t=start+.3,view=settings)
    receipt={'song':stem,'musical_revision':2,'visual_revision':3,'size':[1920,1080],'fps':30,'crf':18,
             'score_sha256':sha(score),'wav_sha256':sha(wav),'source_sha256':sha(source),
             'view_sha256':sha(view.path_for(str(source))),'video_sha256':sha(movie),'poster_sha256':sha(poster),
             'audio_reused_without_changes':True}
    (ROOT/'textbook/audio/ch51'/(stem+'.video.json')).write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
    if '--stage-only' not in sys.argv:
        publish(stem)
    print('Finished',stem,flush=True)


def publish(stem):
    """Commit completed media; keep the staged copy for competing-build recovery."""
    stage=ROOT/'build/performance_videos'
    dest=ROOT/'textbook_site/video/ch51'
    receipt=json.loads((ROOT/'textbook/audio/ch51'/(stem+'.video.json')).read_text())
    assert sha(stage/(stem+'.mp4'))==receipt['video_sha256']
    assert sha(stage/(stem+'.jpg'))==receipt['poster_sha256']
    for suffix in ('.mp4','.jpg'):
        target=dest/(stem+suffix)
        temporary=dest/(stem+'.performance-publish'+suffix)
        shutil.copy2(stage/(stem+suffix),temporary)
        os.replace(temporary,target)


if __name__=='__main__':
    names=[arg for arg in sys.argv[1:] if not arg.startswith('--')] or [p.stem for p in sorted((ROOT/'songs/golden_worlds').glob('*.sm'))]
    for name in names:
        publish(name) if '--publish-only' in sys.argv else render(name)
