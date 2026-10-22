import { Component, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./styles.css";

class Boundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="crash">
        <h2>The Studio hit a bug</h2>
        <pre>{String(this.state.error.stack ?? this.state.error)}</pre>
        <button onClick={() => this.setState({ error: null })}>Try again</button> <button onClick={() => location.reload()}>Reload</button>
        <p className="muted">Your last save is on disk; unsaved edits since then may be lost on reload.</p>
      </div>
    );
  }
}

createRoot(document.getElementById("root")!).render(<Boundary><App /></Boundary>);
