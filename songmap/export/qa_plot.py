"""qa.png: a picture of a render for eyes instead of ears (ROADMAP P2).

Top: a log-frequency spectrogram with section boundaries and event ticks. Bottom: short-term
loudness over time with each section's integrated loudness as a step. Mud shows as a bright
band under ~250 Hz, harshness above 4 kHz, a flat arc as a flat loudness line.
"""
from __future__ import annotations

import numpy as np

from ..instruments.dsp import SR


def write_png(path: str, audio: np.ndarray, sections: list[tuple[str, float, float]], events: list[tuple[str, float]],
              section_loudness: dict[str, float], title: str = "") -> str:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from scipy.signal import stft

    x = audio.mean(axis=1) if audio.ndim > 1 else audio
    f, t, z = stft(x, fs=SR, nperseg=4096, noverlap=3072)
    mag = 20 * np.log10(np.abs(z) + 1e-9)
    keep = (f >= 30) & (f <= 16000)
    fig, (ax, ax2) = plt.subplots(2, 1, figsize=(14, 6), sharex=True, gridspec_kw={"height_ratios": [3, 1]})
    ax.pcolormesh(t, f[keep], mag[keep], shading="auto", cmap="magma", vmin=mag.max() - 80, vmax=mag.max())
    ax.set_yscale("log")
    ax.set_ylabel("Hz")
    ax.axhline(250, color="cyan", lw=0.6, alpha=0.5)
    ax.axhline(4000, color="cyan", lw=0.6, alpha=0.5)
    for name, s0, _ in sections:
        for a in (ax, ax2):
            a.axvline(s0, color="white" if a is ax else "gray", lw=0.8, alpha=0.8)
        ax.text(s0 + 0.2, 13000, name, color="white", fontsize=8, va="top")
    for kind, ts in events:
        ax.plot([ts], [40], marker="v", color="lime" if kind == "impact" else "yellow", ms=6)
    hop = int(0.4 * SR)
    win = int(3.0 * SR)
    xs, ys = [], []
    for i in range(0, max(1, len(x) - win), hop):
        seg = x[i:i + win]
        ys.append(10 * np.log10(np.mean(seg ** 2) + 1e-12) - 0.691)
        xs.append((i + win / 2) / SR)
    ax2.plot(xs, ys, color="tab:orange", lw=1, label="short-term level (3 s)")
    for name, s0, s1 in sections:
        if name in section_loudness and section_loudness[name] is not None:
            ax2.hlines(section_loudness[name], s0, s1, color="tab:blue", lw=2)
    ax2.set_ylabel("LUFS")
    ax2.set_xlabel("seconds")
    ax2.grid(alpha=0.3)
    ax.set_title(title)
    fig.tight_layout()
    fig.savefig(path, dpi=80)
    plt.close(fig)
    return path
