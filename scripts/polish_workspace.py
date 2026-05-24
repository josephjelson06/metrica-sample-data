"""
Polish pass for analysis-workspace.tsx:
1. Extend getPrimaryResultTitle with all modes
2. Replace old static suggestedQueries with analyst-level starter prompts
3. Upgrade Status display to show connection dot + turn counter
4. Fix the left-panel label from "Next.js Frontend" to empty
"""
from pathlib import Path

src = Path("frontend/components/analysis-workspace.tsx")
content = src.read_text(encoding="utf-8").replace("\r\n", "\n")

# ── 1. Extend getPrimaryResultTitle ──────────────────────────────────────────
OLD_TITLE_FN = '''function getPrimaryResultTitle(context: AnalysisContext | null) {
  if (!context) {
    return "Waiting For Analysis";
  }

  switch (context.mode) {
    case "aggregate":
      return "Aggregate View";
    case "comparison":
      return "Comparison View";
    case "buildup":
      return "Buildup View";
    case "transition":
      return "Transition View";
    case "sequence_event":
      return "Sequence Event View";
    case "frame":
      return "Frame View";
    case "event":
    default:
      return "Match View";
  }
}'''

NEW_TITLE_FN = '''function getPrimaryResultTitle(context: AnalysisContext | null) {
  if (!context) {
    return "Waiting For Analysis";
  }

  switch (context.mode) {
    case "orientation":  return "Team Orientation";
    case "pass_network": return "Pass Network";
    case "pass_sonars":  return "Pass Sonars";
    case "physicality":  return "Physicality Dashboard";
    case "auto_insights":return "Dangerous Transitions";
    case "set_piece":    return "Set-Piece Analysis";
    case "aggregate":    return "Aggregate View";
    case "comparison":   return "Comparison View";
    case "buildup":      return "Buildup View";
    case "transition":   return "Transition View";
    case "sequence_event": return "Sequence Event View";
    case "frame":        return "Frame View";
    case "synthesis":    return "Multi-Primitive Synthesis";
    case "event":
    default:             return "Match View";
  }
}'''

if OLD_TITLE_FN in content:
    content = content.replace(OLD_TITLE_FN, NEW_TITLE_FN)
    print("✓ Extended getPrimaryResultTitle")
else:
    print("✗ Could not find getPrimaryResultTitle")

# ── 2. Replace static suggestedQueries ──────────────────────────────────────
OLD_QUERIES = '''const suggestedQueries = [
  "Show me the away team's second corner",
  "How many away shots were there in period 2?",
  "Show me the buildup to the goal",
  "Show me the transition after the first away recovery",
  "Compare the transition after the first and second away recoveries",
  "Write a report on the away team's second corner",
];'''

NEW_QUERIES = '''// Level 1 → Level 2 → Level 3 starter prompts for the coach
const suggestedQueries = [
  "Show me the lineups",
  "Show me the Home team pass network",
  "Show pass sonars for Away",
  "Show physicality for Home",
  "Show dangerous transitions for Home",
  "Analyze set piece marking for Away",
  "Show me Home pass network from 30 to 45 minutes",
  "Show me the away team's second corner",
];'''

if OLD_QUERIES in content:
    content = content.replace(OLD_QUERIES, NEW_QUERIES)
    print("✓ Updated suggestedQueries")
else:
    print("✗ Could not find suggestedQueries")

# ── 3. Remove "Next.js Frontend" label (replace with level indicator) ────────
OLD_LABEL = '        <p style={{ margin: 0, letterSpacing: "0.18em", textTransform: "uppercase", fontSize: 12, color: "var(--accent)" }}>\n          Next.js Frontend\n        </p>'
NEW_LABEL = '        <p style={{ margin: 0, letterSpacing: "0.18em", textTransform: "uppercase", fontSize: 12, color: "var(--accent)" }}>\n          Football Intelligence · {conversationContext ? `Turn ${conversationContext.turn_count}` : "Ready"}\n        </p>'

if OLD_LABEL in content:
    content = content.replace(OLD_LABEL, NEW_LABEL)
    print("✓ Replaced label text")
else:
    print("✗ Could not find label — checking variant...")
    # Fallback: search for the exact text
    idx = content.find("Next.js Frontend")
    if idx != -1:
        print(f"  Found 'Next.js Frontend' at char {idx}")
        content = content.replace("Next.js Frontend", "Football Intelligence · Analyst Tablet")
        print("✓ Replaced via simple string replace")

# ── 4. Upgrade the Status block to show a live dot ───────────────────────────
OLD_STATUS = '''          <strong>Status:</strong> {getStatusLabel(status)}
          {errorMessage ? (
            <p style={{ margin: "8px 0 0", color: "var(--accent)" }}>{errorMessage}</p>
          ) : null}'''

NEW_STATUS = '''          <span style={{
            display: "inline-block",
            width: 8,
            height: 8,
            borderRadius: "50%",
            background: status === "connected" ? "#2ecc71" : status === "connecting" ? "#f1c40f" : status === "error" ? "#e74c3c" : "#aaa",
            marginRight: 8,
            verticalAlign: "middle",
            boxShadow: status === "connected" ? "0 0 6px rgba(46,204,113,0.6)" : "none",
          }} />
          <strong>{getStatusLabel(status)}</strong>
          {errorMessage ? (
            <p style={{ margin: "8px 0 0", color: "var(--accent)" }}>{errorMessage}</p>
          ) : null}'''

if OLD_STATUS in content:
    content = content.replace(OLD_STATUS, NEW_STATUS)
    print("✓ Upgraded status indicator")
else:
    print("✗ Could not find status block")

# ── 5. Rename "Quick prompts" to "Analyst Starters" ──────────────────────────
content = content.replace(
    "<strong style={{ fontSize: 14 }}>Quick prompts</strong>",
    "<strong style={{ fontSize: 14 }}>Analyst Starters</strong>"
)
print("✓ Renamed prompt section label")

# ── 6. Add a level-of-analysis badge next to query textarea ──────────────────
OLD_QUERY_LABEL = '          Natural language query\n          <textarea'
NEW_QUERY_LABEL = '          <span style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>\n            Natural language query\n            <span style={{ fontSize: 11, fontWeight: 400, color: "var(--muted)", padding: "2px 8px", borderRadius: 999, background: "rgba(0,0,0,0.05)" }}>\n              {!context ? "L1 Orientation" :\n                context.mode === "orientation" ? "L1 → L2 Ready" :\n                context.mode === "pass_network" || context.mode === "pass_sonars" ? "L2 Functional" :\n                context.mode === "physicality" || context.mode === "auto_insights" ? "L3 Tactical" :\n                context.mode === "set_piece" || context.mode === "comparison" ? "L3 Tactical" : "L2 Functional"}\n            </span>\n          </span>\n          <textarea'

if OLD_QUERY_LABEL in content:
    content = content.replace(OLD_QUERY_LABEL, NEW_QUERY_LABEL)
    print("✓ Added level badge to query label")
else:
    print("✗ Could not find query label")

src.write_text(content, encoding="utf-8")
print(f"\nDone. File: {len(content.splitlines())} lines.")
