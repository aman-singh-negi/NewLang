import { useCallback, useEffect, useState } from "react";
import Editor, { type OnMount } from "@monaco-editor/react";
import { Group, Panel, Separator } from "react-resizable-panels";
import { IntroSplash } from "./components/IntroSplash";
import { fetchHealth, getApiBase, postCode, type ApiEnvelope } from "./lib/api";
import { setupMonaco } from "./monacoSetup";

const DEFAULT_CODE = `func greet() {
  show 42
}

var n = 3
loop n > 0 {
  show n
  var n = n - 1
}

greet()
show 100
`;

type TabId = "output" | "pipeline" | "ai";

function IconPlay() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M8 5v14l11-7z" />
    </svg>
  );
}

function IconCpu() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <rect x="4" y="4" width="16" height="16" rx="2" />
      <path d="M9 9h6v6H9z" />
    </svg>
  );
}

function IconSparkles() {
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
      <path d="M12 2l1.5 4.5L18 8l-4.5 1.5L12 14l-1.5-4.5L6 8l4.5-1.5L12 2zM4 14l1 3h3l-3 1-1 3-1-3-3-1 3-1 1-3z" />
    </svg>
  );
}

function IconCopy() {
  return (
    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" aria-hidden>
      <rect x="9" y="9" width="13" height="13" rx="2" />
      <path d="M5 15H4a2 2 0 01-2-2V4a2 2 0 012-2h9a2 2 0 012 2v1" />
    </svg>
  );
}

export default function App() {
  const [splashDone, setSplashDone] = useState(false);
  const [code, setCode] = useState(DEFAULT_CODE);
  const [busy, setBusy] = useState(false);
  const [connected, setConnected] = useState<boolean | null>(null);
  const [tab, setTab] = useState<TabId>("output");
  const [lastRun, setLastRun] = useState<ApiEnvelope | null>(null);
  const [lastCompile, setLastCompile] = useState<ApiEnvelope | null>(null);
  const [lastAi, setLastAi] = useState<ApiEnvelope | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchHealth()
      .then(() => {
        if (!cancelled) setConnected(true);
      })
      .catch(() => {
        if (!cancelled) setConnected(false);
      });
    const id = setInterval(() => {
      fetchHealth()
        .then(() => setConnected(true))
        .catch(() => setConnected(false));
    }, 15000);
    return () => {
      cancelled = true;
      clearInterval(id);
    };
  }, []);

  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(null), 3200);
    return () => clearTimeout(t);
  }, [toast]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        document.getElementById("btn-run")?.click();
      }
      if ((e.ctrlKey || e.metaKey) && e.key === "b") {
        e.preventDefault();
        document.getElementById("btn-compile")?.click();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const showToast = (msg: string) => setToast(msg);

  const handleCompile = useCallback(async () => {
    setBusy(true);
    try {
      const data = await postCode("/compile", code);
      setLastCompile(data);
      setTab("pipeline");
      showToast(data.success ? "Compile finished" : "Compile reported issues");
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      showToast(msg);
      setLastCompile({
        success: false,
        message: msg,
        input: { code },
        output: { error: msg },
      });
      setTab("pipeline");
    } finally {
      setBusy(false);
    }
  }, [code]);

  const handleRun = useCallback(async () => {
    setBusy(true);
    try {
      const data = await postCode("/run", code);
      setLastRun(data);
      setTab("output");
      showToast(data.success ? "Run finished" : "Run failed");
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      showToast(msg);
      setLastRun({
        success: false,
        message: msg,
        input: { code },
        output: { error: msg },
      });
      setTab("output");
    } finally {
      setBusy(false);
    }
  }, [code]);

  const handleAi = useCallback(async () => {
    setBusy(true);
    try {
      const data = await postCode("/ai-suggest", code);
      setLastAi(data);
      setTab("ai");
      showToast("AI insight updated");
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e);
      showToast(msg);
      setLastAi({
        success: false,
        message: msg,
        input: { code },
        output: { error: msg },
      });
      setTab("ai");
    } finally {
      setBusy(false);
    }
  }, [code]);

  const copyJson = (obj: unknown) => {
    void navigator.clipboard.writeText(JSON.stringify(obj, null, 2));
    showToast("Copied to clipboard");
  };

  const handleEditorMount: OnMount = (_editor, monaco) => {
    monaco.editor.setTheme("frost-language");
  };

  return (
    <>
      {!splashDone && <IntroSplash onDone={() => setSplashDone(true)} />}
      <div className="vscode-app">
      {toast && (
        <div className="vscode-toast" role="status">
          {toast}
        </div>
      )}

      <div className="vscode-titlebar">
        <div className="vscode-titlebar-menu">
          <span className="tb-item">File</span>
          <span className="tb-item">Edit</span>
          <span className="tb-item">Selection</span>
          <span className="tb-item">Run</span>
        </div>
        <div className="vscode-titlebar-title">language — main.lang</div>
        <div className="vscode-titlebar-actions">
          <span
            className={`vscode-conn ${connected === true ? "ok" : connected === false ? "bad" : "pending"}`}
            title={connected === true ? "Backend OK" : connected === false ? "Offline" : "…"}
          />
        </div>
      </div>

      <div className="vscode-main">
        <aside className="vscode-activity" aria-label="Activity bar">
          <button type="button" className="act-btn active" title="Explorer">
            <IconExplorer />
          </button>
          <button type="button" className="act-btn" title="Run (Ctrl+Enter)" onClick={handleRun}>
            <IconPlay />
          </button>
          <button type="button" className="act-btn" title="AI insight" onClick={handleAi}>
            <IconSparkles />
          </button>
        </aside>

        <aside className="vscode-sidebar">
          <div className="sb-section-head">Explorer</div>
          <div className="sb-tree">
            <div className="sb-folder open">LANGUAGE</div>
            <div className="sb-file active">main.lang</div>
          </div>
        </aside>

        <div className="vscode-center">
          <Group orientation="vertical" className="vscode-panel-group">
            <Panel defaultSize={60} minSize={38} className="vscode-panel-editor" id="editor">
              <div className="vscode-editor-col">
                <div className="vscode-tabrow">
                  <span className="vscode-tab active">main.lang</span>
                  <span className="vscode-tab-hint">Ctrl+Enter Run · Ctrl+B Compile</span>
                  <div className="vscode-toolbar">
                    <button id="btn-compile" type="button" className="tb-btn" disabled={busy} onClick={handleCompile}>
                      <IconCpu /> Compile
                    </button>
                    <button id="btn-run" type="button" className="tb-btn primary" disabled={busy} onClick={handleRun}>
                      <IconPlay /> Run
                    </button>
                    <button type="button" className="tb-btn" disabled={busy} onClick={handleAi}>
                      <IconSparkles /> AI
                    </button>
                  </div>
                </div>
                <div className="monaco-host">
                  <Editor
                    height="100%"
                    language="language"
                    theme="frost-language"
                    value={code}
                    onChange={(v) => setCode(v ?? "")}
                    beforeMount={setupMonaco}
                    onMount={handleEditorMount}
                    loading={<div className="monaco-loading">Loading editor…</div>}
                    options={{
                      minimap: { enabled: true, scale: 0.75, side: "right" },
                      fontSize: 14,
                      fontLigatures: true,
                      fontFamily: "'Cascadia Code', 'JetBrains Mono', Consolas, monospace",
                      lineNumbers: "on",
                      glyphMargin: true,
                      scrollBeyondLastLine: false,
                      automaticLayout: true,
                      padding: { top: 8, bottom: 8 },
                      cursorBlinking: "smooth",
                      smoothScrolling: true,
                      bracketPairColorization: { enabled: true },
                      renderLineHighlight: "all",
                      wordWrap: "on",
                      folding: true,
                    }}
                  />
                </div>
              </div>
            </Panel>

            <Separator className="vscode-separator">
              <div className="vscode-sep-grip" />
            </Separator>

            <Panel defaultSize={40} minSize={18} className="vscode-panel-bottom" id="bottom">
              <div className="vscode-panel-inner">
                <div className="bottom-tabs" role="tablist">
                  <button
                    type="button"
                    role="tab"
                    aria-selected={tab === "output"}
                    className={tab === "output" ? "btab active" : "btab"}
                    onClick={() => setTab("output")}
                  >
                    Terminal
                  </button>
                  <button
                    type="button"
                    role="tab"
                    aria-selected={tab === "pipeline"}
                    className={tab === "pipeline" ? "btab active" : "btab"}
                    onClick={() => setTab("pipeline")}
                  >
                    Compiler
                  </button>
                  <button
                    type="button"
                    role="tab"
                    aria-selected={tab === "ai"}
                    className={tab === "ai" ? "btab active" : "btab"}
                    onClick={() => setTab("ai")}
                  >
                    AI
                  </button>
                </div>
                <div className="bottom-body">
                  {tab === "output" && (
                    <OutputView data={lastRun} onCopy={() => lastRun && copyJson(lastRun)} />
                  )}
                  {tab === "pipeline" && (
                    <PipelineView data={lastCompile} onCopy={() => lastCompile && copyJson(lastCompile)} />
                  )}
                  {tab === "ai" && <AiView data={lastAi} onCopy={() => lastAi && copyJson(lastAi)} />}
                </div>
              </div>
            </Panel>
          </Group>
        </div>
      </div>

      <footer className="vscode-statusbar">
        <div className="sb-left">
          <span className="sb-branch">language</span>
          <span className="sb-item">{connected === true ? "●" : connected === false ? "○" : "…"} backend</span>
          <span className="sb-item">{busy ? "Working…" : "Ready"}</span>
        </div>
        <div className="sb-right">
          <code className="sb-api">{getApiBase()}</code>
          <span className="sb-lang">language</span>
        </div>
      </footer>
    </div>
    </>
  );
}

function IconExplorer() {
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
      <path d="M3 7h5l2 2h11v10H3V7z" />
    </svg>
  );
}

function OutputView({
  data,
  onCopy,
}: {
  data: ApiEnvelope | null;
  onCopy: () => void;
}) {
  if (!data) {
    return (
      <div className="empty-state">
        <p className="empty-title">No run yet</p>
        <p className="empty-desc">Click Run or press Ctrl+Enter to execute on the VM.</p>
      </div>
    );
  }

  const out = data.output as Record<string, unknown>;
  const ok = data.success && out.status === "ok";
  const stdout = typeof out.stdout === "string" ? out.stdout : "";

  if (!data.success || !ok) {
    return (
      <div className="result-block error-block">
        <div className="result-head">
          <span className="badge bad">Failed</span>
          <button type="button" className="icon-btn" onClick={onCopy} title="Copy JSON">
            <IconCopy />
          </button>
        </div>
        <pre className="json-pre">{JSON.stringify(data, null, 2)}</pre>
      </div>
    );
  }

  return (
    <div className="result-block success-block">
      <div className="result-head">
        <span className="badge ok">Success</span>
        <span className="exit-code">exit {String(out.exit_code ?? 0)}</span>
        <button type="button" className="icon-btn" onClick={onCopy} title="Copy JSON">
          <IconCopy />
        </button>
      </div>
      <div className="terminal-out">{stdout || "(no stdout)"}</div>
    </div>
  );
}

function PipelineView({
  data,
  onCopy,
}: {
  data: ApiEnvelope | null;
  onCopy: () => void;
}) {
  if (!data) {
    return (
      <div className="empty-state">
        <p className="empty-title">No compile yet</p>
        <p className="empty-desc">Compile to see tokens, AST, IR, and bytecode.</p>
      </div>
    );
  }

  const out = data.output as Record<string, unknown>;
  const tokens = out.tokens as unknown[] | undefined;
  const ir = out.ir_optimized as string[] | undefined;
  const bc = out.bytecode as string[] | undefined;

  if (!data.success || out.status !== "ok") {
    return (
      <div className="result-block error-block">
        <div className="result-head">
          <span className="badge bad">Compile error</span>
          <button type="button" className="icon-btn" onClick={onCopy} title="Copy JSON">
            <IconCopy />
          </button>
        </div>
        <pre className="json-pre">{JSON.stringify(data, null, 2)}</pre>
      </div>
    );
  }

  const sem = out.semantic as { success?: boolean; errors?: string[] } | undefined;
  const semWarn = sem && sem.success === false;

  return (
    <div className="pipeline-grid">
      {semWarn && (
        <div className="semantic-warn" role="alert">
          <strong>Semantic issues</strong>
          <ul>
            {(sem.errors ?? []).map((err, i) => (
              <li key={i}>{err}</li>
            ))}
          </ul>
        </div>
      )}
      <div className="stat-cards">
        <div className="stat-card">
          <span className="stat-label">Tokens</span>
          <span className="stat-val">{tokens?.length ?? 0}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">IR lines</span>
          <span className="stat-val">{ir?.length ?? 0}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Bytecode</span>
          <span className="stat-val">{bc?.length ?? 0}</span>
        </div>
        <div className="stat-card">
          <span className="stat-label">Semantic</span>
          <span className="stat-val">
            {sem == null ? "—" : sem.success ? "OK" : "Issues"}
          </span>
        </div>
      </div>
      <div className="code-columns">
        <div className="mini-panel">
          <div className="mini-h">Optimized IR</div>
          <pre className="mini-pre">{ir?.join("\n") ?? ""}</pre>
        </div>
        <div className="mini-panel">
          <div className="mini-h">Bytecode</div>
          <pre className="mini-pre">{bc?.join("\n") ?? ""}</pre>
        </div>
      </div>
      <button type="button" className="btn-text" onClick={onCopy}>
        <IconCopy /> Copy full response JSON
      </button>
    </div>
  );
}

function AiView({
  data,
  onCopy,
}: {
  data: ApiEnvelope | null;
  onCopy: () => void;
}) {
  if (!data) {
    return (
      <div className="empty-state">
        <p className="empty-title">No AI insight yet</p>
        <p className="empty-desc">Train a model (see README) or get placeholder hints from the server.</p>
      </div>
    );
  }

  const out = data.output as Record<string, unknown>;
  const suggestions = out.suggestions as string[] | undefined;
  const conf = typeof out.confidence === "number" ? out.confidence : null;
  const label = typeof out.label === "string" ? out.label : null;

  return (
    <div className="ai-block">
      <div className="result-head">
        <span className="badge soft">{String(out.status ?? "—")}</span>
        {label && <span className="ai-label">{label}</span>}
        {conf !== null && (
          <span className="conf-meter">
            <span className="conf-bar" style={{ width: `${Math.round(conf * 100)}%` }} />
            <span className="conf-text">{Math.round(conf * 100)}% confidence</span>
          </span>
        )}
        <button type="button" className="icon-btn" onClick={onCopy} title="Copy JSON">
          <IconCopy />
        </button>
      </div>
      <ul className="ai-list">
        {(suggestions ?? []).map((s, i) => (
          <li key={i}>{s}</li>
        ))}
      </ul>
    </div>
  );
}
