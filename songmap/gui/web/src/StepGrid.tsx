// The step grid: a kit part in one section, one row per piece. A click cycles a step (x → X → - → o → .);
// an edited row is written as `piece="x...|...."` on the section's line, replacing that lane of the style.
import { useEffect, useMemo, useState } from "react";
import { api } from "./api";

type Hits = {
  section: string; index: number; part: string; bars: number; beats_per_bar: number; line: number | null;
  start: number; end: number; pieces: Record<string, [number, number][]>; written: string[];
};

const CYCLE = [".", "x", "X", "-", "o"];
const LEVEL: Record<string, number> = { X: 1.0, x: 0.78, "-": 0.55, o: 0.38 };
const charOf = (v: number) => (v >= 0.89 ? "X" : v >= 0.665 ? "x" : v >= 0.465 ? "-" : "o");

export function StepGrid({ path, text, summary, index, part, time, onApply, color }: {
  path: string; text: string; summary: unknown; index: number; part: string; time: number;
  onApply: (op: string, args: object) => Promise<void>; color: string;
}) {
  const [hits, setHits] = useState<Hits | null>(null);
  const [res, setRes] = useState(4);                       // steps per beat: 4 = 16ths, 3 = 8th triplets, 2 = 8ths
  const [grid, setGrid] = useState<Record<string, string[]>>({});
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let live = true;
    api.clip(path, text, index, part).then((h: Hits) => { if (live) { setHits(h); setErr(null); } }).catch((e) => live && setErr(String(e)));
    return () => { live = false; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [summary, index, part]);

  const n = hits ? Math.round(hits.bars * hits.beats_per_bar * res) : 0;
  const perBar = hits ? Math.round(hits.beats_per_bar * res) : 16;
  useEffect(() => {
    if (!hits) return;
    const g: Record<string, string[]> = {};
    for (const [piece, hs] of Object.entries(hits.pieces)) {
      const row = Array(n).fill(".");
      for (const [b, v] of hs) {
        const k = Math.round(b * res);
        if (k >= 0 && k < n && Math.abs(b * res - k) < 0.2) row[k] = row[k] === "." || LEVEL[charOf(v)] > LEVEL[row[k]] ? charOf(v) : row[k];
      }
      g[piece] = row;
    }
    setGrid(g);
  }, [hits, res, n]);
  const offGrid = useMemo(() => {
    if (!hits) return 0;
    return Object.values(hits.pieces).flat().filter(([b]) => Math.abs(b * res - Math.round(b * res)) >= 0.2).length;
  }, [hits, res]);

  const write = async (piece: string, row: string[]) => {
    setBusy(true);
    try { await onApply("steps", { index, part, piece, steps: row.reduce((s, c, i) => s + (i && i % perBar === 0 ? "|" : "") + c, "") }); }
    catch (e) { setErr(String(e)); }
    setBusy(false);
  };
  const click = (piece: string, i: number, e: React.MouseEvent) => {
    const row = [...grid[piece]];
    row[i] = e.shiftKey ? "." : CYCLE[(CYCLE.indexOf(row[i]) + 1) % CYCLE.length];
    setGrid({ ...grid, [piece]: row });
    write(piece, row);
  };
  const playBeat = hits && time >= hits.start && time < hits.end
    ? Math.floor(((time - hits.start) / (hits.end - hits.start)) * n) : -1;

  if (!hits) return <p className="pad muted">{err ?? "loading…"}</p>;
  const pieces = Object.keys(hits.pieces).sort((a, b) => (hits.pieces[b].length > 0 ? 1 : 0) - (hits.pieces[a].length > 0 ? 1 : 0));
  return (
    <div className="steps">
      <div className="steps-tools">
        <label className="field-inline">grid
          <select value={res} onChange={(e) => setRes(+e.target.value)}>
            <option value={4}>16ths</option><option value={3}>8th triplets</option><option value={2}>8ths</option><option value={6}>16th triplets</option>
          </select></label>
        <span className="muted small">click: . → x → X → - → o · shift-click clears · an edited row replaces that lane of the style</span>
        <span className="spacer" />
        {offGrid > 0 && <span className="pill warn" title="Hits between steps of this grid (swing, flams, a finer grid): editing a row writes it on this grid">{offGrid} hits off this grid</span>}
        {busy && <span className="muted small">saving…</span>}
      </div>
      {err && <p className="warn-text small pad">{err}</p>}
      <div className="steps-scroll">
        <table className="steps-table">
          <tbody>
            {pieces.map((piece) => (
              <tr key={piece} className={hits.written.includes(piece) ? "written" : ""}>
                <th title={hits.written.includes(piece) ? "written on the section line" : "from the style"}>
                  {piece}{hits.written.includes(piece) && <i> •</i>}</th>
                {(grid[piece] ?? []).map((c, i) => (
                  <td key={i} className={(i % perBar === 0 ? "bar " : i % res === 0 ? "beat " : "") + (i === playBeat ? "now" : "")}
                      onClick={(e) => click(piece, i, e)}>
                    <span className={"cell c" + (c === "." ? "0" : c === "X" ? "X" : c === "x" ? "x" : c === "-" ? "s" : "o")}
                          style={c !== "." ? { background: color, opacity: 0.25 + 0.75 * (LEVEL[c] ?? 0) } : undefined} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
