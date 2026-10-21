// Render TeX to HTML at build time. stdin: JSON [[tex, display], ...]; stdout: JSON [{html} | {error}, ...].
const katex = require("katex");

let input = "";
process.stdin.setEncoding("utf8");
process.stdin.on("data", (d) => { input += d; });
process.stdin.on("end", () => {
  const out = JSON.parse(input).map(([tex, display]) => {
    try {
      return { html: katex.renderToString(tex, { displayMode: display, throwOnError: true, strict: "ignore", output: "html" }) };
    } catch (e) {
      return { error: String(e.message || e) };
    }
  });
  process.stdout.write(JSON.stringify(out));
});
