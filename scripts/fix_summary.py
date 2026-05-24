"""Add mode-aware summary text to renderPrimarySummary for the new modes."""
from pathlib import Path

src = Path("frontend/components/analysis-workspace.tsx")
content = src.read_text(encoding="utf-8").replace("\r\n", "\n")

OLD_SUMMARY = '''function renderPrimarySummary(context: AnalysisContext | null, activeFrame: number, hasSequence: boolean, clipStartLabel: string | null, clipEndLabel: string | null) {
  if (!context) {
    return "Waiting for your first query.";
  }

  const eventContext = context.event;
  if (context.mode === "aggregate" && context.aggregate) {'''

NEW_SUMMARY = '''function renderPrimarySummary(context: AnalysisContext | null, activeFrame: number, hasSequence: boolean, clipStartLabel: string | null, clipEndLabel: string | null) {
  if (!context) {
    return "Ask your first question — try \\"Show me the lineups\\" to begin.";
  }

  // Descriptive summaries for analyst-tablet modes
  if (context.mode === "orientation") {
    return (
      <>
        <strong>Team Orientation</strong>
        {" — lineup, estimated formation, and substitution events derived from tracking data. Role labels (GK, CB, CM…) are inferred from average match positions."}
      </>
    );
  }

  if (context.mode === "pass_network") {
    return (
      <>
        <strong>Pass Network</strong>
        {" — nodes show average passing position, sized by volume. Edges show pass frequency between pairs. Thicker lines = more passes."}
      </>
    );
  }

  if (context.mode === "pass_sonars") {
    return (
      <>
        <strong>Pass Sonars</strong>
        {" — each player's directional pass distribution shown as a radar. Length of each spoke = proportion of passes in that direction."}
      </>
    );
  }

  if (context.mode === "physicality") {
    return (
      <>
        <strong>Physicality Dashboard</strong>
        {" — total distance, high-speed running (HSR), and sprint distance per player, ranked by total load."}
      </>
    );
  }

  if (context.mode === "auto_insights") {
    return (
      <>
        <strong>Dangerous Transitions</strong>
        {" — algorithmically detected moments where a team rapidly moved from defensive to attacking phase within a tight time window."}
      </>
    );
  }

  if (context.mode === "set_piece") {
    return (
      <>
        <strong>Set-Piece Analysis</strong>
        {" — defensive marking pairs at the set piece moment. Distance between each attacker-defender pair shown, sorted by proximity."}
      </>
    );
  }

  if (context.mode === "synthesis") {
    return (
      <>
        <strong>Multi-Primitive Synthesis</strong>
        {" — combined view across pass network, sonars, and physicality for a full tactical picture."}
      </>
    );
  }

  const eventContext = context.event;
  if (context.mode === "aggregate" && context.aggregate) {'''

if OLD_SUMMARY in content:
    content = content.replace(OLD_SUMMARY, NEW_SUMMARY)
    print("Fixed renderPrimarySummary")
else:
    print("Pattern not found — trying partial match...")
    idx = content.find('function renderPrimarySummary(')
    print(f"Function found at char: {idx}")

src.write_text(content, encoding="utf-8")
print(f"Done. {len(content.splitlines())} lines.")
