// The code pane: CodeMirror 6 with SongMap highlighting and live diagnostics from the server's check.
import { useEffect, useRef } from "react";
import { EditorState } from "@codemirror/state";
import { EditorView, keymap, lineNumbers, highlightActiveLine, drawSelection } from "@codemirror/view";
import { defaultKeymap, history, historyKeymap, indentWithTab } from "@codemirror/commands";
import { StreamLanguage, syntaxHighlighting, HighlightStyle, bracketMatching } from "@codemirror/language";
import { linter, lintGutter, type Diagnostic as CMDiagnostic } from "@codemirror/lint";
import { tags } from "@lezer/highlight";
import type { Diagnostic } from "./api";

const DIRECTIVES = new Set(["song", "inst", "kit", "groove", "feel", "chords", "prog", "motif", "cue", "mix", "master", "qa", "set"]);
const KEYWORDS = new Set(["for", "in", "if", "elif", "else", "every", "def", "return", "form", "with", "and", "or", "not",
  "true", "false", "none", "as", "at", "bars", "bar", "song"]);

// A small stream tokenizer for the .sm language (and good enough for YAML song maps).
const smLanguage = StreamLanguage.define<{ lineStart: boolean }>({
  startState: () => ({ lineStart: true }),
  token(stream, state) {
    if (stream.sol()) state.lineStart = true;
    if (stream.eatSpace()) return null;
    const first = state.lineStart;
    state.lineStart = false;
    if (stream.peek() === "#" && (stream.pos === 0 || /\s/.test(stream.string[stream.pos - 1]))) {
      stream.skipToEnd();
      return "comment";
    }
    if (stream.match(/^"(?:[^"\\]|\\.)*"?/) || stream.match(/^'(?:[^'\\]|\\.)*'?/)) return "string";
    if (stream.match(/^![A-Za-z_]\w*/)) return "atom";                       // events
    if (stream.match(/^[\d.]+/)) return "number";
    const w = stream.match(/^[A-Za-z_]\w*/) as RegExpMatchArray | null;
    if (w) {
      const word = w[0];
      if (first && DIRECTIVES.has(word)) return "keyword";
      if (KEYWORDS.has(word)) return "keyword";
      if (first) return "def";                                                 // section or variable name
      if (stream.peek() === ":" || stream.peek() === "=") return "propertyName";
      return "variableName";
    }
    if (stream.match(/^\|/)) return "punctuation";
    stream.next();
    return null;
  },
});

const style = HighlightStyle.define([
  { tag: tags.comment, color: "var(--muted)", fontStyle: "italic" },
  { tag: tags.string, color: "var(--str)" },
  { tag: tags.keyword, color: "var(--kw)", fontWeight: "600" },
  { tag: tags.atom, color: "var(--evt)", fontWeight: "600" },
  { tag: tags.number, color: "var(--num)" },
  { tag: tags.definition(tags.variableName), color: "var(--def)", fontWeight: "600" },
  { tag: tags.propertyName, color: "var(--prop)" },
  { tag: tags.punctuation, color: "var(--muted)" },
]);

type Props = {
  value: string;
  onChange: (text: string) => void;
  diagnostics: Diagnostic[];
  gotoLine?: { line: number; n: number } | null;
};

export function CodeEditor({ value, onChange, diagnostics, gotoLine }: Props) {
  const host = useRef<HTMLDivElement>(null);
  const view = useRef<EditorView | null>(null);
  const diags = useRef<Diagnostic[]>(diagnostics);
  const changeCb = useRef(onChange);
  changeCb.current = onChange;

  useEffect(() => {
    const lint = linter((v) => {
      const out: CMDiagnostic[] = [];
      for (const d of diags.current) {
        const ln = d.line && d.line <= v.state.doc.lines ? v.state.doc.line(d.line) : v.state.doc.line(1);
        out.push({ from: ln.from, to: ln.to, severity: d.severity === "error" ? "error" : "warning",
          message: d.message + (d.suggestion ? ` (${d.suggestion})` : "") });
      }
      return out;
    }, { delay: 0 });
    view.current = new EditorView({
      parent: host.current!,
      state: EditorState.create({
        doc: value,
        extensions: [
          lineNumbers(), history(), drawSelection(), highlightActiveLine(), bracketMatching(),
          keymap.of([...defaultKeymap, ...historyKeymap, indentWithTab]),
          smLanguage, syntaxHighlighting(style), lintGutter(), lint,
          EditorView.updateListener.of((u) => { if (u.docChanged) changeCb.current(u.state.doc.toString()); }),
          EditorView.theme({ "&": { height: "100%" }, ".cm-scroller": { fontFamily: "var(--mono)", fontSize: "13px" } }),
        ],
      }),
    });
    return () => view.current?.destroy();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // external value changes (opening another file, an operation from another pane)
  useEffect(() => {
    const v = view.current;
    if (v && v.state.doc.toString() !== value) v.dispatch({ changes: { from: 0, to: v.state.doc.length, insert: value } });
  }, [value]);

  // refresh lint marks when the server's diagnostics change
  useEffect(() => {
    diags.current = diagnostics;
    const v = view.current;
    if (v) v.dispatch({});        // the linter re-runs on the next update
  }, [diagnostics]);

  useEffect(() => {
    const v = view.current;
    if (v && gotoLine && gotoLine.line <= v.state.doc.lines) {
      const ln = v.state.doc.line(gotoLine.line);
      v.dispatch({ selection: { anchor: ln.from }, scrollIntoView: true });
      v.focus();
    }
  }, [gotoLine]);

  return <div className="code" ref={host} />;
}
