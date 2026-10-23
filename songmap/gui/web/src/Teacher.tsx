// The theory teacher: a deterministic reading of the harmony at the playhead (gui/teach.py) and of every note
// sounding against it, the section's progression and cadences, and the automated ear's findings explained.
import { useEffect, useMemo, useState } from "react";
import { api, type Summary } from "./api";

type TChord = {
  symbol: string; start: number; end: number; key: string; section: string | null; section_index: number | null;
  root: number; tones: number[]; intervals: number[]; numeral: string; degree: number; function: string;
  quality_name: string; quality_text: string; function_text: string; explain: string; cadence: string | null;
  motion: { semitones: number; text: string; common_tones: number } | null; sixth_steps: number;
};
type TSection = { name: string; index: number; start: number; key: string; progression: string; summary: string; cadences: string[] };
type TFinding = { severity: string; kind: string; where: string; message: string; fix: string; why: string };
type Teach = { key: string; tuning: string; chords: TChord[]; sections: TSection[]; findings: TFinding[] };

const NAMES = ["C", "C♯", "D", "E♭", "E", "F", "F♯", "G", "A♭", "A", "B♭", "B"];
const pc = (x: number) => ((x % 12) + 12) % 12;
export const noteName = (p: number) => {
  const k = Math.round(p), off = Math.round((p - k) * 3);
  return (off > 0 ? "↑" : off < 0 ? "↓" : "") + NAMES[pc(k)] + (Math.floor(k / 12) - 1);
};

// What a note is doing against a chord, by its interval above the root (in semitones, 36-EDO aware).
const DEGREES: [number, string, string][] = [
  [0, "root", "chord"], [3, "minor 3rd", "chord"], [4, "major 3rd", "chord"], [7, "5th", "chord"],
  [10, "minor 7th", "chord"], [11, "major 7th", "chord"], [9, "6th", "colour"],
  [11 / 3, "golden 3rd", "chord"], [22 / 3, "golden 5th", "chord"], [10 / 3, "silver 3rd", "chord"], [20 / 3, "silver 5th", "chord"],
  [2, "9th", "tension"], [5, "11th (4th)", "tension"], [1, "♭9", "rub"], [6, "♯11 / ♭5", "tension"], [8, "♭13 / ♯5", "tension"],
  [6.5, "", ""],
];
const ROLE_TEXT: Record<string, string> = {
  chord: "a chord tone: stable, it agrees with the harmony",
  colour: "an added colour tone: consonant but not in the triad",
  tension: "a tension: a colour that leans and usually moves by step to a chord tone",
  rub: "a rub: a half step above a chord tone, it beats against it (expressive if short or resolving)",
  micro: "between the cracks: a sixth-step off a chord tone, the golden harmony's inflection",
};

function relate(p: number, c: TChord): { label: string; role: string } {
  const iv = pc(p - c.root);
  for (const ci of c.intervals) {
    if (Math.abs(pc(ci) - iv) < 0.05 || Math.abs(pc(ci) - iv) > 11.95) {
      const d = DEGREES.find(([s]) => Math.abs(s - pc(ci)) < 0.05);
      return { label: d ? d[1] : "chord tone", role: "chord" };
    }
  }
  const d = DEGREES.find(([s]) => Math.abs(s - iv) < 0.05);
  if (d && d[1]) return { label: d[1], role: d[2] };
  const near = c.intervals.map(pc).reduce((a, b) => (Math.abs(b - iv) < Math.abs(a - iv) ? b : a), 0);
  const steps = Math.round((iv - near) * 3);
  const nd = DEGREES.find(([s]) => Math.abs(s - near) < 0.05);
  return { label: `${Math.abs(steps)} sixth-step${Math.abs(steps) > 1 ? "s" : ""} ${steps > 0 ? "above" : "below"} the ${nd ? nd[1] : "chord tone"}`, role: "micro" };
}

export function Teacher({ path, text, summary, time, onSeek, ok }: {
  path: string; text: string; summary: Summary | null; time: number; onSeek: (t: number) => void; ok: boolean;
}) {
  const [data, setData] = useState<Teach | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [open, setOpen] = useState<number | null>(null);

  useEffect(() => {
    if (!ok) return;
    const id = window.setTimeout(() => {
      api.teach(path, text).then((d: Teach) => { setData(d); setErr(null); }).catch((e) => setErr(String(e)));
    }, 400);
    return () => window.clearTimeout(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [summary, ok]);

  const ci = data ? data.chords.findIndex((c) => time >= c.start && time < c.end) : -1;
  const chord = ci >= 0 ? data!.chords[ci] : null;
  const next = data && ci >= 0 ? data.chords[ci + 1] : null;
  const sec = data?.sections.find((s) => chord && s.index === chord.section_index) ?? null;
  const sounding = useMemo(() => {
    if (!summary || !chord) return [];
    const out: { part: string; pitch: number; vel: number }[] = [];
    for (const p of summary.parts) {
      if (p.kit) continue;
      for (const n of p.notes) if (n[2] !== null && n[0] <= time + 1e-3 && time < n[0] + n[1]) out.push({ part: p.name, pitch: n[2], vel: n[3] });
    }
    return out.sort((a, b) => b.pitch - a.pitch);
  }, [summary, chord, time]);

  const seekWhere = (where: string) => {
    if (!summary) return;
    const m = where.match(/^(.+?) bar (\d+)$/);
    const s = summary.sections.find((x) => x.name === (m ? m[1] : where));
    if (s) {
      const bar = m ? +m[2] - 1 : 0;
      onSeek(summary.bar_times[s.bar + bar] ?? s.start);
    } else if (m && m[1] === "bar") onSeek(summary.bar_times[+m[2]] ?? 0);
  };

  if (!ok) return <p className="pad muted">Fix the errors and the teacher will read the song.</p>;
  if (!data) return <p className="pad muted">{err ?? "reading the harmony…"}</p>;
  return (
    <div className="teacher pad">
      {chord ? (
        <section className={"t-card fn-" + chord.function}>
          <div className="t-chord">
            <b>{chord.symbol}</b><span className="t-num">{chord.numeral}</span>
            <span className={"pill fn fn-" + chord.function}>{chord.function}</span>
            <span className="spacer" /><span className="muted small">in {chord.key}</span>
          </div>
          <p>{chord.explain}</p>
          {next && <p className="muted small">Next: <b>{next.symbol}</b> ({next.numeral}){next.cadence ? ` — ${next.cadence}` : ""}{next.motion ? `; the root ${next.motion.text}.` : "."}</p>}
        </section>
      ) : <p className="muted">No chord at the playhead.</p>}

      {chord && sounding.length > 0 && (
        <section>
          <h4>What's sounding now</h4>
          <ul className="t-notes">
            {sounding.slice(0, 12).map((n, i) => {
              const r = relate(n.pitch, chord);
              return <li key={i} className={"role-" + r.role} title={ROLE_TEXT[r.role]}>
                <span className="t-part">{n.part}</span><b>{noteName(n.pitch)}</b><span>{r.label}</span></li>;
            })}
          </ul>
          <p className="muted small">Hover a note for what its role means. Chord tones are stable; tensions lean; rubs beat.</p>
        </section>
      )}

      {sec && (
        <section>
          <h4>This section: {sec.name}</h4>
          <p>{sec.summary}</p>
          <div className="t-prog">
            {data.chords.filter((c) => c.section_index === sec.index).map((c, i) => (
              <button key={i} className={"chip" + (c === chord ? " on" : "")} onClick={() => onSeek(c.start)} title={c.explain}>
                {c.numeral}<small>{c.symbol}</small></button>
            ))}
          </div>
          {sec.cadences.length > 0 && <p className="small">Cadences: {sec.cadences.join("; ")}.</p>}
        </section>
      )}

      <section>
        <h4>The ear ({data.findings.length})</h4>
        {data.findings.length === 0 && <p className="ok small">Nothing to report.</p>}
        <ul className="t-findings">
          {data.findings.map((f, i) => (
            <li key={i} className={"sev-" + f.severity}>
              <div className="t-f-head" onClick={() => setOpen(open === i ? null : i)}>
                <span className="pill">{f.kind}</span>
                <a onClick={(e) => { e.stopPropagation(); seekWhere(f.where); }} title="go there">{f.where}</a>
              </div>
              <p>{f.message}</p>
              {open === i ? (
                <>
                  {f.why && <p className="small"><b>Why it matters:</b> {f.why}</p>}
                  {f.fix && <p className="small"><b>Try:</b> {f.fix}</p>}
                </>
              ) : <button className="ghost small" onClick={() => setOpen(i)}>why · how to fix</button>}
            </li>
          ))}
        </ul>
      </section>
      <section>
        <h4>The whole song</h4>
        {data.sections.map((s) => (
          <p key={s.index} className="small t-sec" onClick={() => onSeek(s.start)}><b>{s.name}</b> {s.progression}</p>
        ))}
      </section>
    </div>
  );
}
