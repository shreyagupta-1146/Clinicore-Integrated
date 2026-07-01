/**
 * components/DiffViewer.tsx
 *
 * Side-by-side config diff — ported from weave-heal (PRISM) mesh/DiffViewer.
 * Shows the current config (removed lines red) vs the agent-proposed fix
 * (added lines green). Used in the Self-Healing SRE console so a human sees
 * exactly what `kubectl apply` would change before approving.
 */

function diffLines(oldText: string, newText: string) {
  const a = oldText.split("\n");
  const b = newText.split("\n");
  const setA = new Set(a);
  const setB = new Set(b);
  return {
    left: a.map((line) => ({ line, kind: (setB.has(line) ? "same" : "removed") as "same" | "removed" })),
    right: b.map((line) => ({ line, kind: (setA.has(line) ? "same" : "added") as "same" | "added" })),
  };
}

export function DiffViewer({ oldText, newText }: { oldText: string; newText: string }) {
  const { left, right } = diffLines(oldText, newText);
  return (
    <div className="grid grid-cols-2 gap-3 font-mono text-[11px]">
      <pre className="overflow-x-auto rounded-lg border p-3" style={{ borderColor: "color-mix(in oklab, var(--destructive) 30%, transparent)", background: "color-mix(in oklab, var(--destructive) 5%, white)" }}>
        <div className="mb-2 text-[10px] font-semibold uppercase tracking-widest" style={{ color: "var(--destructive)" }}>— current</div>
        {left.map((l, i) => (
          <div key={i} style={l.kind === "removed" ? { background: "color-mix(in oklab, var(--destructive) 14%, transparent)", color: "var(--destructive)" } : { color: "var(--muted-foreground)" }}>
            <span className="mr-2 select-none opacity-50">{l.kind === "removed" ? "-" : " "}</span>{l.line || " "}
          </div>
        ))}
      </pre>
      <pre className="overflow-x-auto rounded-lg border p-3" style={{ borderColor: "color-mix(in oklab, var(--success) 30%, transparent)", background: "color-mix(in oklab, var(--success) 5%, white)" }}>
        <div className="mb-2 text-[10px] font-semibold uppercase tracking-widest" style={{ color: "var(--success)" }}>+ agent fix</div>
        {right.map((l, i) => (
          <div key={i} style={l.kind === "added" ? { background: "color-mix(in oklab, var(--success) 14%, transparent)", color: "color-mix(in oklab, var(--success) 55%, black)" } : { color: "var(--muted-foreground)" }}>
            <span className="mr-2 select-none opacity-50">{l.kind === "added" ? "+" : " "}</span>{l.line || " "}
          </div>
        ))}
      </pre>
    </div>
  );
}
