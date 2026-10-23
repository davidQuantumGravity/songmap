// Typed client for the Studio server (songmap/gui/server.py, docs/GUI.md §7).

export type Diagnostic = {
  severity: "error" | "warning";
  line: number | null;
  section?: string | null;
  message: string;
  suggestion: string | null;
  text: string;
};

export type Section = { name: string; index: number; bar: number; bars: number; start: number; end: number; line: number | null };
// [start s, length s, pitch (MIDI, float) | null for drums, velocity 0..1, kit piece]
export type Note = [number, number, number | null, number, string];
export type InsertSpec = { fx: string } & Record<string, number | string>;
export type PartMix = { gain_db: number; pan: number; send: Record<string, number>; sidechain: boolean; inserts: InsertSpec[] };
export type Part = { name: string; kit: boolean; instrument: string | null; count: number; notes: Note[]; mix: PartMix };
export type Voice = {
  use: string; instrument: string; preset: string | null; patch?: string; patch_source?: "song" | "library";
  schema?: ParamSpec[]; error?: string;
  params: Record<string, number | string>;              // the song's overrides
  values: Record<string, number | string>;              // every param, resolved (default < preset < song)
  preset_values?: Record<string, number | string>;
};
export type PartVoice = ({ kit: false } & Voice) | { kit: true; pieces: Record<string, Voice> } | { error: string; kit?: undefined };
export type ParamSpec = { name: string; default: number; lo: number; hi: number; unit: string; curve: "lin" | "log"; group: string; doc: string };
export type InstrumentSpec = { name: string; family: string; mono: boolean; params: ParamSpec[] };
export type Preset = { name: string; ref: string; description: string; tags: string[]; params: Record<string, number> };
export type UnitSpec = { name: string; doc: string; params: ParamSpec[] };
export type GuideBlock = { id: string; label: string; kind: string; what: string; params: string[]; to: string[] };
export type Guide = {
  title: string; family: string; ancestor: string; summary: string; how: string; why: string; chain: GuideBlock[];
  params: Record<string, { says: string; up: string; down: string }>; velocity: string;
  recipes: { name: string; set: Record<string, number>; listen: string }[]; pattern?: string; try_next: string;
};
export type ModuleKnob = { name: string; default: number; lo: number; hi: number; unit: string; curve: string; mod: string; doc: string; choices: string[] };
export type ModuleSpec = { name: string; kind: string; doc: string; audio_in: boolean; output: string; knobs: ModuleKnob[] };
export type PatchData = { modules: Record<string, Record<string, number | string>>; wires: string[]; description?: string };
export type Catalog = {
  instruments: InstrumentSpec[]; presets: Record<string, Preset[]>; samplers: { name: string; title: string; license: string; family: string }[];
  inserts: UnitSpec[]; guides: Record<string, Guide>; modules: ModuleSpec[]; sources: string[]; patch_library: Record<string, PatchData>;
};
export type AuditionNote = { t: number; pitch: number; vel: number; gate: number };

export type SongEvent = { type: string; at: string; time: number; start: number; section: string | null };

export type Summary = {
  title: string; tempo: number; meter: string; key: string; tuning: string; mood: string | null; fps: number;
  bars: number; seconds: number; music_seconds: number; frames: number; length: string; digest: string;
  sections: Section[]; parts: Part[]; events: SongEvent[]; bar_times: number[];
  chords: [number, number, string][]; returns: string[]; voices: Record<string, PartVoice>; master_inserts: InsertSpec[];
  patches: Record<string, PatchData>; return_inserts: Record<string, InsertSpec[]>;
};

// What the video shows and how (docs/GUI.md §4.4; S6 grows this into layers).
export type Layer = { type: string; box: [number, number, number, number]; show?: boolean; panel?: boolean } & Record<string, unknown>;
export type View = {
  size: [number, number]; theme: "light" | "dark"; page_seconds: number; parts: string[] | null;
  colors: Record<string, string>; color_by: "spelling" | "part"; part_colors: Record<string, string>; layers: Layer[];
};

export type Check = { ok: boolean; diagnostics: Diagnostic[]; summary: Summary | null; ms: number };

export type QA = {
  lufs: number; true_peak_db: number; clipped: number;
  sections: { name: string; loudness: number }[];
  stems: Record<string, number>;
};

export type RenderResult =
  | { ok: true; key: string; seconds: number; elapsed: number; remixed: boolean; audio: string; check: Check; qa: QA }
  | { ok: false; check: Check };

export type Files = Record<string, string[]>;

async function json<T>(r: Promise<Response>): Promise<T> {
  const res = await r;
  if (!res.ok) {
    let detail = res.statusText;
    try { detail = (await res.json()).detail ?? detail; } catch { /* not JSON */ }
    throw new Error(`${res.status} ${detail}`);
  }
  return res.json() as Promise<T>;
}

const post = (url: string, body: unknown, method = "POST") =>
  fetch(url, { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });

export const api = {
  files: () => json<Files>(fetch("/api/files")),
  project: (path: string) => json<{ path: string; text: string; check: Check }>(fetch(`/api/project?path=${encodeURIComponent(path)}`)),
  check: (path: string, text: string) => json<Check>(post("/api/check", { path, text })),
  save: (path: string, text: string) => json<{ saved: boolean; check: Check }>(post("/api/project", { path, text }, "PUT")),
  create: (path: string) => json<{ path: string; text: string; check: Check }>(post("/api/new", { path })),
  render: (path: string, text: string, mute: string[] = [], solo: string[] = []) =>
    json<RenderResult>(post("/api/render", { path, text, mute, solo })),
  op: (path: string, text: string, op: string, args: object) => json<{ text: string; check: Check }>(post("/api/op", { path, text, op, args })),
  exportFiles: (path: string, text: string, formats: string[], view: object) =>
    json<{ ok: boolean; files?: Record<string, string>; check?: Check }>(post("/api/export", { path, text, formats, view })),
  frameUrl: async (path: string, text: string, t: number, view: object) => {
    const res = await post("/api/frame", { path, text, t, view });
    if (!res.ok) throw new Error(`${res.status}`);
    return URL.createObjectURL(await res.blob());
  },
  catalog: () => json<Catalog>(fetch("/api/catalog")),
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  teach: (path: string, text: string) => json<any>(post("/api/teach", { path, text })),
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  clip: (path: string, text: string, index: number, part: string) => json<any>(post("/api/clip", { path, text, index, part })),
  audition: async (path: string, text: string, part: string, notes: AuditionNote[], piece: string | null, overrides: object) => {
    const res = await post("/api/audition", { path, text, part, notes, piece, overrides });
    if (!res.ok) { let d = res.statusText; try { d = (await res.json()).detail ?? d; } catch { /* */ } throw new Error(d); }
    return URL.createObjectURL(await res.blob());
  },
  getView: (path: string) => json<{ view: View; saved: boolean; file: string; default: View; sizes: Record<string, [number, number]>; error?: string }>(
    fetch(`/api/view?path=${encodeURIComponent(path)}`)),
  saveView: (path: string, view: View) => json<{ saved: boolean; file: string }>(post("/api/view", { path, view }, "PUT")),
  fileUrl: (path: string) => `/api/file?path=${encodeURIComponent(path)}`,
};
