"""
Adds the conversational analyst tablet UI to analysis-workspace.tsx:
1. Adds renderOrientationPanel, ContextRibbon, FollowUpChips, HistoryStrip helper functions
2. Adds orientation mode handler in renderResultSurface
3. Wires new selectors and new components into AnalysisWorkspace
"""
from pathlib import Path

src = Path("frontend/components/analysis-workspace.tsx")
content = src.read_text(encoding="utf-8")

# ─────────────────────────────────────────────────────────────────────────────
# 1. Add orientation + conversational helper functions before the
#    export function AnalysisWorkspace line
# ─────────────────────────────────────────────────────────────────────────────

NEW_HELPERS = '''
// ── ORIENTATION PANEL ────────────────────────────────────────────────────────

function renderOrientationPanel(orientation: any | null | undefined) {
  if (!orientation) return null;

  const lineupMap: Record<string, any> = orientation.lineup?.lineup ?? {};
  const subs: any[] = orientation.substitutions ?? [];
  const formations: any = orientation.formations ?? {};

  const homeFormation = formations.Home?.formation ?? "—";
  const awayFormation = formations.Away?.formation ?? "—";

  const homePlayers = Object.entries(lineupMap)
    .filter(([, info]: [string, any]) => info.team === "Home")
    .sort((a: any, b: any) => a[1].avg_x - b[1].avg_x);
  const awayPlayers = Object.entries(lineupMap)
    .filter(([, info]: [string, any]) => info.team === "Away")
    .sort((a: any, b: any) => a[1].avg_x - b[1].avg_x);

  const PITCH_W = 420;
  const PITCH_H = 260;

  return (
    <div style={{ display: "grid", gap: 16 }}>
      {/* Formation badges */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        {[
          { label: "Home Formation", value: homeFormation, color: "#d4a96a" },
          { label: "Away Formation", value: awayFormation, color: "#6aafcf" },
        ].map(({ label, value, color }) => (
          <div
            key={label}
            style={{
              borderRadius: 14,
              padding: "14px 18px",
              background: "rgba(255,255,255,0.72)",
              border: "1px solid rgba(21,32,23,0.09)",
              textAlign: "center",
            }}
          >
            <p style={{ margin: "0 0 4px", fontSize: 11, textTransform: "uppercase", letterSpacing: "0.1em", color: "var(--muted)" }}>
              {label}
            </p>
            <strong style={{ fontSize: "1.7rem", color }}>{value}</strong>
            <p style={{ margin: "4px 0 0", fontSize: 11, color: "var(--muted)" }}>estimated</p>
          </div>
        ))}
      </div>

      {/* Average position mini-pitch */}
      <div
        style={{
          borderRadius: 14,
          padding: "16px 18px",
          background: "rgba(255,255,255,0.72)",
          border: "1px solid rgba(21,32,23,0.09)",
        }}
      >
        <h3 style={{ margin: "0 0 12px", fontSize: "0.9rem", textTransform: "uppercase", letterSpacing: "0.08em" }}>
          Average Positions
        </h3>
        <svg
          viewBox={`0 0 ${PITCH_W} ${PITCH_H}`}
          style={{ width: "100%", borderRadius: 8, background: "#2d5a27" }}
        >
          {/* Pitch lines */}
          <rect x={0} y={0} width={PITCH_W} height={PITCH_H} fill="#2d5a27" />
          <rect x={10} y={10} width={PITCH_W - 20} height={PITCH_H - 20} fill="none" stroke="rgba(255,255,255,0.3)" strokeWidth={1} />
          <line x1={PITCH_W / 2} y1={10} x2={PITCH_W / 2} y2={PITCH_H - 10} stroke="rgba(255,255,255,0.3)" strokeWidth={1} />
          <circle cx={PITCH_W / 2} cy={PITCH_H / 2} r={30} fill="none" stroke="rgba(255,255,255,0.3)" strokeWidth={1} />

          {/* Home players (left→right: defensive→attacking) */}
          {homePlayers.map(([pid, info]: [string, any]) => {
            const cx = 10 + info.avg_x * (PITCH_W - 20);
            const cy = 10 + info.avg_y * (PITCH_H - 20);
            const shortName = pid.replace("Home_Player", "H") ;
            return (
              <g key={pid}>
                <circle cx={cx} cy={cy} r={10} fill="#d4a96a" stroke="#fff" strokeWidth={1.5} />
                <text x={cx} y={cy + 4} textAnchor="middle" fontSize={8} fill="#1a1a1a" fontWeight="bold">
                  {shortName}
                </text>
                <text x={cx} y={cy + 17} textAnchor="middle" fontSize={7} fill="rgba(255,255,255,0.8)">
                  {info.role}
                </text>
              </g>
            );
          })}

          {/* Away players */}
          {awayPlayers.map(([pid, info]: [string, any]) => {
            const cx = 10 + (1 - info.avg_x) * (PITCH_W - 20);
            const cy = 10 + info.avg_y * (PITCH_H - 20);
            const shortName = pid.replace("Away_Player", "A");
            return (
              <g key={pid}>
                <circle cx={cx} cy={cy} r={10} fill="#6aafcf" stroke="#fff" strokeWidth={1.5} />
                <text x={cx} y={cy + 4} textAnchor="middle" fontSize={8} fill="#1a1a1a" fontWeight="bold">
                  {shortName}
                </text>
                <text x={cx} y={cy + 17} textAnchor="middle" fontSize={7} fill="rgba(255,255,255,0.8)">
                  {info.role}
                </text>
              </g>
            );
          })}
        </svg>
        <div style={{ display: "flex", gap: 16, marginTop: 10, justifyContent: "center" }}>
          <span style={{ fontSize: 12, color: "var(--muted)", display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#d4a96a", display: "inline-block" }} />
            Home
          </span>
          <span style={{ fontSize: 12, color: "var(--muted)", display: "flex", alignItems: "center", gap: 6 }}>
            <span style={{ width: 10, height: 10, borderRadius: "50%", background: "#6aafcf", display: "inline-block" }} />
            Away
          </span>
        </div>
      </div>

      {/* Lineup tables */}
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 12 }}>
        {[
          { label: "Home", players: homePlayers, color: "#d4a96a" },
          { label: "Away", players: awayPlayers, color: "#6aafcf" },
        ].map(({ label, players, color }) => (
          <div
            key={label}
            style={{
              borderRadius: 14,
              overflow: "hidden",
              border: "1px solid rgba(21,32,23,0.09)",
              background: "rgba(255,255,255,0.72)",
            }}
          >
            <div style={{ padding: "10px 14px", background: color + "22", borderBottom: "1px solid rgba(21,32,23,0.06)" }}>
              <strong style={{ fontSize: 13, color }}>{label}</strong>
            </div>
            <table style={{ width: "100%", borderCollapse: "collapse", fontSize: 12 }}>
              <thead>
                <tr style={{ color: "var(--muted)" }}>
                  <th style={{ padding: "8px 12px", textAlign: "left", fontWeight: 600 }}>Player</th>
                  <th style={{ padding: "8px 12px", textAlign: "left", fontWeight: 600 }}>Role</th>
                  <th style={{ padding: "8px 12px", textAlign: "left", fontWeight: 600 }}>Periods</th>
                </tr>
              </thead>
              <tbody>
                {players.map(([pid, info]: [string, any]) => (
                  <tr key={pid} style={{ borderTop: "1px solid rgba(21,32,23,0.05)" }}>
                    <td style={{ padding: "8px 12px", fontWeight: 600, color: "var(--ink)" }}>
                      {pid.replace("Home_", "").replace("Away_", "")}
                    </td>
                    <td style={{ padding: "8px 12px" }}>
                      <span style={{
                        display: "inline-block",
                        padding: "2px 7px",
                        borderRadius: 999,
                        background: color + "22",
                        color: color,
                        fontWeight: 700,
                        fontSize: 11,
                      }}>
                        {info.role}
                      </span>
                    </td>
                    <td style={{ padding: "8px 12px", color: "var(--muted)" }}>
                      {[info.in_period_1 && "P1", info.in_period_2 && "P2"].filter(Boolean).join(" + ") || "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ))}
      </div>

      {/* Substitutions */}
      {subs.length > 0 && (
        <div
          style={{
            borderRadius: 14,
            padding: "14px 18px",
            background: "rgba(255,255,255,0.72)",
            border: "1px solid rgba(21,32,23,0.09)",
          }}
        >
          <h3 style={{ margin: "0 0 12px", fontSize: "0.9rem", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            Substitution Events (estimated)
          </h3>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8 }}>
            {subs.map((sub: any, i: number) => (
              <div
                key={i}
                style={{
                  padding: "8px 12px",
                  borderRadius: 10,
                  background: sub.event === "subbed_on" ? "rgba(34,100,56,0.12)" : "rgba(180,50,30,0.1)",
                  border: `1px solid ${sub.event === "subbed_on" ? "rgba(34,100,56,0.2)" : "rgba(180,50,30,0.2)"}`,
                  fontSize: 12,
                }}
              >
                <span style={{ fontWeight: 700, color: "var(--ink)" }}>
                  {sub.player.replace("Home_", "").replace("Away_", "")}
                </span>
                <span style={{ color: "var(--muted)", marginLeft: 6 }}>
                  {sub.event === "subbed_on" ? "▲ On" : "▼ Off"} · ~{sub.approx_minute}min · P{sub.period}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

// ── CONTEXT RIBBON ────────────────────────────────────────────────────────────

function ContextRibbon({ conversationContext }: { conversationContext: any | null }) {
  if (!conversationContext || conversationContext.turn_count === 0) return null;

  const pills = [
    conversationContext.current_team && { label: conversationContext.current_team, icon: "⚽" },
    conversationContext.current_period && { label: `Period ${conversationContext.current_period}`, icon: "🕐" },
    conversationContext.current_mode && {
      label: conversationContext.current_mode.replace(/_/g, " ").replace(/\\b\\w/g, (c: string) => c.toUpperCase()),
      icon: "📊",
    },
    conversationContext.start_minute != null && conversationContext.end_minute != null && {
      label: `${conversationContext.start_minute}–${conversationContext.end_minute} min`,
      icon: "⏱",
    },
  ].filter(Boolean) as { label: string; icon: string }[];

  if (pills.length === 0) return null;

  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: 8,
        padding: "10px 0",
        borderBottom: "1px solid rgba(21,32,23,0.07)",
        marginBottom: 4,
      }}
    >
      <span style={{ fontSize: 11, color: "var(--muted)", alignSelf: "center", textTransform: "uppercase", letterSpacing: "0.08em" }}>
        Context:
      </span>
      {pills.map(({ label, icon }) => (
        <span
          key={label}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 5,
            padding: "4px 10px",
            borderRadius: 999,
            background: "rgba(180, 120, 50, 0.1)",
            border: "1px solid rgba(180,120,50,0.22)",
            fontSize: 12,
            fontWeight: 600,
            color: "#8a5c1e",
          }}
        >
          {icon} {label}
        </span>
      ))}
    </div>
  );
}

// ── FOLLOW-UP CHIPS ───────────────────────────────────────────────────────────

function FollowUpChips({
  suggestions,
  onSelect,
}: {
  suggestions: { label: string; query: string }[];
  onSelect: (query: string) => void;
}) {
  if (!suggestions || suggestions.length === 0) return null;

  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        gap: 8,
        padding: "14px 0 4px",
        borderTop: "1px solid rgba(21,32,23,0.07)",
        marginTop: 4,
      }}
    >
      <span style={{ fontSize: 11, color: "var(--muted)", alignSelf: "center", textTransform: "uppercase", letterSpacing: "0.08em" }}>
        Ask next:
      </span>
      {suggestions.map(({ label, query }) => (
        <button
          key={label}
          type="button"
          onClick={() => onSelect(query)}
          style={{
            border: "1px solid rgba(27,54,92,0.22)",
            borderRadius: 999,
            padding: "6px 14px",
            background: "rgba(27,54,92,0.07)",
            color: "#1b365c",
            fontWeight: 600,
            fontSize: 13,
            cursor: "pointer",
            transition: "background 0.15s, box-shadow 0.15s",
          }}
          onMouseEnter={(e) => {
            (e.currentTarget as HTMLButtonElement).style.background = "rgba(27,54,92,0.15)";
          }}
          onMouseLeave={(e) => {
            (e.currentTarget as HTMLButtonElement).style.background = "rgba(27,54,92,0.07)";
          }}
        >
          {label} →
        </button>
      ))}
    </div>
  );
}

// ── HISTORY STRIP ─────────────────────────────────────────────────────────────

const MODE_ICON: Record<string, string> = {
  orientation: "🪪",
  pass_network: "🕸",
  pass_sonars: "📡",
  physicality: "⚡",
  auto_insights: "🔍",
  set_piece: "⛳",
  comparison: "⚖",
  buildup: "📈",
  transition: "⚡",
  aggregate: "🔢",
  synthesis: "🧬",
};

function HistoryStrip({
  history,
  onReplay,
}: {
  history: { turn: number; query: string; mode: string | null; summary: string }[];
  onReplay: (query: string) => void;
}) {
  if (!history || history.length === 0) return null;

  return (
    <div style={{ display: "grid", gap: 6 }}>
      <p style={{ margin: 0, fontSize: 11, color: "var(--muted)", textTransform: "uppercase", letterSpacing: "0.08em" }}>
        Conversation Trail
      </p>
      {[...history].reverse().map((turn) => (
        <button
          key={turn.turn}
          type="button"
          onClick={() => onReplay(turn.query)}
          title={turn.query}
          style={{
            display: "flex",
            alignItems: "flex-start",
            gap: 10,
            padding: "10px 12px",
            borderRadius: 12,
            border: "1px solid rgba(21,32,23,0.08)",
            background: "rgba(255,255,255,0.7)",
            cursor: "pointer",
            textAlign: "left",
            width: "100%",
            transition: "background 0.12s",
          }}
          onMouseEnter={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.95)"; }}
          onMouseLeave={(e) => { (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.7)"; }}
        >
          <span style={{ fontSize: 16, flexShrink: 0, marginTop: 1 }}>
            {MODE_ICON[turn.mode ?? ""] ?? "💬"}
          </span>
          <span style={{ fontSize: 12, color: "var(--ink)", lineHeight: 1.45, overflow: "hidden" }}>
            <strong style={{ display: "block", marginBottom: 2, color: "var(--muted)", fontSize: 11 }}>
              Turn {turn.turn} · {(turn.mode ?? "—").replace(/_/g, " ")}
            </strong>
            {turn.query.length > 80 ? turn.query.slice(0, 80) + "…" : turn.query}
          </span>
        </button>
      ))}
    </div>
  );
}

'''

# Insert before the `export function AnalysisWorkspace` line
ANCHOR = "export function AnalysisWorkspace() {"
idx = content.find(ANCHOR)
if idx == -1:
    raise RuntimeError("Could not find AnalysisWorkspace function")

content = content[:idx] + NEW_HELPERS + content[idx:]
print(f"Inserted helpers. File now has {len(content.splitlines())} lines.")

# ─────────────────────────────────────────────────────────────────────────────
# 2. Add orientation mode to renderResultSurface
# ─────────────────────────────────────────────────────────────────────────────

ORIENTATION_CASE = '''
  if (context.mode === "orientation") {
    return (
      <div style={{ display: "grid", gap: 14 }}>
        <div style={{ ...cardStyle(), padding: 20 }}>
          <h3 style={sectionTitleStyle()}>Team Orientation</h3>
          <p style={{ margin: "8px 0 16px", color: "var(--muted)", lineHeight: 1.6 }}>{context.query}</p>
          {renderOrientationPanel(passNetwork)}
        </div>
        {renderExplanationPanel(context)}
        {renderReportPanel(context, onCopyReport, reportCopied)}
      </div>
    );
  }

'''

# Insert just before the `if (!context)` guard in renderResultSurface
RS_ANCHOR = "  if (!context) {\n    return (\n      <div style={cardStyle()}>\n        <h3 style={sectionTitleStyle()}>No Result Yet</h3>"
idx2 = content.find(RS_ANCHOR)
if idx2 == -1:
    # Try with \r\n
    RS_ANCHOR = "  if (!context) {\r\n    return (\r\n      <div style={cardStyle()}>\r\n        <h3 style={sectionTitleStyle()}>No Result Yet</h3>"
    idx2 = content.find(RS_ANCHOR)

if idx2 == -1:
    print("WARNING: Could not find renderResultSurface guard — skipping orientation mode injection")
else:
    content = content[:idx2] + ORIENTATION_CASE + content[idx2:]
    print("Injected orientation mode into renderResultSurface.")

# ─────────────────────────────────────────────────────────────────────────────
# 3. The renderResultSurface for orientation mode passes `passNetwork` as the
#    orientation arg — we need to fix that. The function is called with
#    latestPayload?.pass_network, but orientation needs latestPayload?.orientation.
#    We need to add orientation as a parameter to renderResultSurface.
# ─────────────────────────────────────────────────────────────────────────────

# Add `orientation` param to renderResultSurface signature
OLD_SIG = "  setPieceAnalysis: any | null,\n  showKinematics: boolean,"
NEW_SIG = "  setPieceAnalysis: any | null,\n  orientation: any | null,\n  showKinematics: boolean,"
content = content.replace(OLD_SIG, NEW_SIG)
print("Added orientation param to renderResultSurface signature.")

# Fix the orientation mode render to use the orientation param, not passNetwork
OLD_ORIENT_RENDER = "          {renderOrientationPanel(passNetwork)}"
NEW_ORIENT_RENDER = "          {renderOrientationPanel(orientation)}"
content = content.replace(OLD_ORIENT_RENDER, NEW_ORIENT_RENDER)
print("Fixed orientation panel to use orientation param.")

# ─────────────────────────────────────────────────────────────────────────────
# 4. Add new store selectors to AnalysisWorkspace
# ─────────────────────────────────────────────────────────────────────────────

OLD_SELECTORS = "  const setPlaying = useAnalysisStore((state) => state.setPlaying);"
NEW_SELECTORS = """  const setPlaying = useAnalysisStore((state) => state.setPlaying);
  const conversationContext = useAnalysisStore((state) => state.conversationContext);
  const conversationHistory = useAnalysisStore((state) => state.conversationHistory);
  const followUpSuggestions = useAnalysisStore((state) => state.followUpSuggestions);"""

# Handle both LF and CRLF
content = content.replace(
    "  const setPlaying = useAnalysisStore((state) => state.setPlaying);\r\n",
    NEW_SELECTORS.replace("\n", "\r\n") + "\r\n"
)
content = content.replace(
    "  const setPlaying = useAnalysisStore((state) => state.setPlaying);\n",
    NEW_SELECTORS + "\n"
)
print("Added conversation selectors to AnalysisWorkspace.")

# ─────────────────────────────────────────────────────────────────────────────
# 5. Add animKey state for smooth transitions
# ─────────────────────────────────────────────────────────────────────────────

OLD_REPORT_COPIED = "  const [reportCopied, setReportCopied] = useState(false);"
NEW_REPORT_COPIED = """  const [reportCopied, setReportCopied] = useState(false);
  const [animKey, setAnimKey] = useState(0);"""

content = content.replace(
    "  const [reportCopied, setReportCopied] = useState(false);\r\n",
    NEW_REPORT_COPIED.replace("\n", "\r\n") + "\r\n"
)
content = content.replace(
    "  const [reportCopied, setReportCopied] = useState(false);\n",
    NEW_REPORT_COPIED + "\n"
)
print("Added animKey state.")

# ─────────────────────────────────────────────────────────────────────────────
# 6. Advance animKey whenever latestPayload changes (triggers CSS transition)
# ─────────────────────────────────────────────────────────────────────────────

OLD_EFFECT = """  useEffect(() => {
    const { connect, disconnect } = useAnalysisStore.getState();
    connect();
    return () => {
      disconnect();
    };
  }, []);"""

NEW_EFFECT = """  useEffect(() => {
    const { connect, disconnect } = useAnalysisStore.getState();
    connect();
    return () => {
      disconnect();
    };
  }, []);

  // Advance animKey whenever a new payload arrives to trigger CSS transitions
  useEffect(() => {
    if (latestPayload) {
      setAnimKey((k) => k + 1);
    }
  }, [latestPayload]);"""

content = content.replace(
    OLD_EFFECT.replace("\n", "\r\n"),
    NEW_EFFECT.replace("\n", "\r\n")
)
content = content.replace(OLD_EFFECT, NEW_EFFECT)
print("Added animKey effect.")

# ─────────────────────────────────────────────────────────────────────────────
# 7. Pass orientation to renderResultSurface call site
# ─────────────────────────────────────────────────────────────────────────────

OLD_CALL = """          latestPayload?.pass_network ?? null,
          latestPayload?.physicality ?? null,
          latestPayload?.pass_sonars ?? null,
          latestPayload?.auto_insights ?? null,
          latestPayload?.set_piece_analysis ?? null,
          showKinematics,"""

NEW_CALL = """          latestPayload?.pass_network ?? null,
          latestPayload?.physicality ?? null,
          latestPayload?.pass_sonars ?? null,
          latestPayload?.auto_insights ?? null,
          latestPayload?.set_piece_analysis ?? null,
          latestPayload?.orientation ?? null,
          showKinematics,"""

content = content.replace(OLD_CALL.replace("\n", "\r\n"), NEW_CALL.replace("\n", "\r\n"))
content = content.replace(OLD_CALL, NEW_CALL)
print("Added orientation to renderResultSurface call.")

# ─────────────────────────────────────────────────────────────────────────────
# 8. Replace the query input panel with the new conversational UI
#    - Add ContextRibbon above the result section
#    - Add FollowUpChips and HistoryStrip to the left panel
#    - Add smooth animation wrapper to the result section
# ─────────────────────────────────────────────────────────────────────────────

# 8a. Add HistoryStrip to the left panel, after the quick prompts section
OLD_DIVIDER = """        <div
          style={{
            display: "grid",
            gap: 12,
            borderRadius: 18,
            padding: 16,
            background: "rgba(255,255,255,0.7)",
            border: "1px solid rgba(21,32,23,0.08)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
            <strong>Frame Controls</strong>"""

NEW_DIVIDER = """        {/* Conversation History Strip */}
        {conversationHistory.length > 0 && (
          <div
            style={{
              borderRadius: 18,
              padding: "14px 16px",
              background: "rgba(255,255,255,0.62)",
              border: "1px solid rgba(21,32,23,0.08)",
            }}
          >
            <HistoryStrip history={conversationHistory} onReplay={runSuggestedQuery} />
          </div>
        )}

        <div
          style={{
            display: "grid",
            gap: 12,
            borderRadius: 18,
            padding: 16,
            background: "rgba(255,255,255,0.7)",
            border: "1px solid rgba(21,32,23,0.08)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12 }}>
            <strong>Frame Controls</strong>"""

content = content.replace(
    OLD_DIVIDER.replace("\n", "\r\n"),
    NEW_DIVIDER.replace("\n", "\r\n")
)
content = content.replace(OLD_DIVIDER, NEW_DIVIDER)
print("Added HistoryStrip to left panel.")

# 8b. Wrap result section title block with ContextRibbon and animKey-keyed div
OLD_RESULT_HEADER = """        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "baseline" }}>
          <h2 style={{ margin: 0, fontFamily: "var(--font-display), serif", fontSize: "1.55rem" }}>
            {getPrimaryResultTitle(context)}
          </h2>
          <p style={{ margin: 0, color: "var(--muted)", fontSize: 14 }}>
            {displayedCoordinates ? `${Object.keys(displayedCoordinates).length} tracked entities` : "Data-first result"}
          </p>
        </div>

        {renderResultMeta(context)}

        <div
          style={{
            borderRadius: 18,
            padding: "14px 16px",
            background: "rgba(255, 248, 239, 0.92)",
            border: "1px solid rgba(186,79,23,0.14)",
            color: "var(--ink)",
            lineHeight: 1.55,
          }}
        >
          {renderPrimarySummary(context, activeFrame, hasSequence, clipStartLabel, clipEndLabel)}
        </div>

        {renderResultSurface("""

NEW_RESULT_HEADER = """        {/* Context Ribbon */}
        <ContextRibbon conversationContext={conversationContext} />

        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, alignItems: "baseline" }}>
          <h2 style={{ margin: 0, fontFamily: "var(--font-display), serif", fontSize: "1.55rem" }}>
            {getPrimaryResultTitle(context)}
          </h2>
          <p style={{ margin: 0, color: "var(--muted)", fontSize: 14 }}>
            {displayedCoordinates ? `${Object.keys(displayedCoordinates).length} tracked entities` : "Data-first result"}
          </p>
        </div>

        {renderResultMeta(context)}

        <div
          style={{
            borderRadius: 18,
            padding: "14px 16px",
            background: "rgba(255, 248, 239, 0.92)",
            border: "1px solid rgba(186,79,23,0.14)",
            color: "var(--ink)",
            lineHeight: 1.55,
          }}
        >
          {renderPrimarySummary(context, activeFrame, hasSequence, clipStartLabel, clipEndLabel)}
        </div>

        {/* Animated result panel — fades in on each new payload */}
        <div
          key={animKey}
          style={{
            animation: "fadeSlideUp 0.35s cubic-bezier(0.22, 1, 0.36, 1) both",
          }}
        >
        {renderResultSurface("""

content = content.replace(
    OLD_RESULT_HEADER.replace("\n", "\r\n"),
    NEW_RESULT_HEADER.replace("\n", "\r\n")
)
content = content.replace(OLD_RESULT_HEADER, NEW_RESULT_HEADER)
print("Added ContextRibbon and animation wrapper.")

# 8c. Close the animation div and add FollowUpChips after renderResultSurface call
OLD_AFTER_SURFACE = """        {renderResultSurface(
          context,
          displayedCoordinates,
          deferredCoordinates,
          activeFrame,
          sequenceEvents,
          replaySequence,
          pitchTransitionMs,
          openResultFrame,
          copyReport,
          reportCopied,
          latestPayload?.pass_network ?? null,
          latestPayload?.physicality ?? null,
          latestPayload?.pass_sonars ?? null,
          latestPayload?.auto_insights ?? null,
          latestPayload?.set_piece_analysis ?? null,
          latestPayload?.orientation ?? null,
          showKinematics,
          showVoronoi,
          showConvexHull,
          showLineHeights,
          showThreatGrid,
        )}
      </section>"""

NEW_AFTER_SURFACE = """        {renderResultSurface(
          context,
          displayedCoordinates,
          deferredCoordinates,
          activeFrame,
          sequenceEvents,
          replaySequence,
          pitchTransitionMs,
          openResultFrame,
          copyReport,
          reportCopied,
          latestPayload?.pass_network ?? null,
          latestPayload?.physicality ?? null,
          latestPayload?.pass_sonars ?? null,
          latestPayload?.auto_insights ?? null,
          latestPayload?.set_piece_analysis ?? null,
          latestPayload?.orientation ?? null,
          showKinematics,
          showVoronoi,
          showConvexHull,
          showLineHeights,
          showThreatGrid,
        )}
        </div>

        {/* Follow-up suggestion chips */}
        <FollowUpChips suggestions={followUpSuggestions} onSelect={runSuggestedQuery} />

      </section>"""

content = content.replace(
    OLD_AFTER_SURFACE.replace("\n", "\r\n"),
    NEW_AFTER_SURFACE.replace("\n", "\r\n")
)
content = content.replace(OLD_AFTER_SURFACE, NEW_AFTER_SURFACE)
print("Added FollowUpChips after result surface.")

# ─────────────────────────────────────────────────────────────────────────────
# 9. Update the header text to reflect the new product identity
# ─────────────────────────────────────────────────────────────────────────────

OLD_HEADER = """          Tactical Cinema Console
        </h1>
        <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.6 }}>
          The frontend is now moving from one pitch-first page into a result-aware football analysis workspace with dedicated surfaces for replay, aggregate, comparison, and report outputs.
        </p>"""

NEW_HEADER = """          Tactical Intelligence Tablet
        </h1>
        <p style={{ margin: 0, color: "var(--muted)", lineHeight: 1.6 }}>
          Ask the analyst anything — lineups, pass patterns, physical intensity, dangerous moments. Each answer builds context for the next question.
        </p>"""

content = content.replace(
    OLD_HEADER.replace("\n", "\r\n"),
    NEW_HEADER.replace("\n", "\r\n")
)
content = content.replace(OLD_HEADER, NEW_HEADER)
print("Updated header text.")

src.write_text(content, encoding="utf-8")
print(f"\nDone. Final file: {len(content.splitlines())} lines.")
