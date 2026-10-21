"""Note-synchronised visuals: letter names, a grand staff and a piano roll with the sounding notes highlighted.

    from songmap.visual import write_video, write_poster, score_of
    songmap video song.sm -o song.mp4 [--theme dark] [--size 1920x1080] [--fps 30]
"""
from .score import Score, ScoreNote, Spelled, score_of, spell
from .video import write_poster, write_video

__all__ = ["Score", "ScoreNote", "Spelled", "score_of", "spell", "write_poster", "write_video"]
