import type { Section, Summary } from "./api";

// Match Timeline's exact integration: BPM is linear in beats, exponential in seconds.
export function localBeat(s: Section, time: number) {
  const dt = Math.max(0, time - s.start), n = s.end_beat - s.start_beat;
  const k = n > 0 ? (s.tempo_end - s.tempo_start) / n : 0;
  return Math.min(n, Math.max(0, Math.abs(k) < 1e-10 ? dt * s.tempo_start / 60 : s.tempo_start / k * Math.expm1(k * dt / 60)));
}
export function sectionTime(s: Section, beat: number) {
  const n = s.end_beat - s.start_beat, k = n > 0 ? (s.tempo_end - s.tempo_start) / n : 0;
  return s.start + (Math.abs(k) < 1e-10 ? beat * 60 / s.tempo_start : 60 / k * Math.log1p(k * beat / s.tempo_start));
}
export function activeConductor(summary: Summary, time: number) {
  const s = summary.sections.find(s => time >= s.start && time < s.end) ?? (time >= summary.music_seconds ? summary.sections[summary.sections.length - 1] : summary.sections[0]);
  if (!s) return { tempo: summary.tempo, meter: summary.meter, key: summary.key, position: "1.1" };
  const beat = localBeat(s, time), n = s.end_beat - s.start_beat;
  const tempo = s.tempo_start + (n > 0 ? (s.tempo_end - s.tempo_start) * beat / n : 0);
  const denominator = Number(s.meter.split("/")[1].split(" ")[0]);
  const bar = Math.min(s.bar + s.bars - 1e-8, s.bar + beat / s.beats_per_bar);
  const pulse = Math.min(Number(s.meter.split("/")[0]), Math.floor((bar - Math.floor(bar)) * s.beats_per_bar * denominator / 4 + 1e-6) + 1);
  return { tempo, meter: s.meter, key: s.key, position: `${Math.floor(Math.max(0, bar)) + 1}.${pulse}` };
}
export const bpmText = (n: number) => String(Number(n.toFixed(1)));
export const tempoText = (s: Section) => s.tempo_start === s.tempo_end ? bpmText(s.tempo_start) : `${bpmText(s.tempo_start)} → ${bpmText(s.tempo_end)}`;
