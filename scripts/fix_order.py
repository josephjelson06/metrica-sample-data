"""Fix: move the if (!context) null guard BEFORE the orientation mode check."""
from pathlib import Path

src = Path("frontend/components/analysis-workspace.tsx")
content = src.read_text(encoding="utf-8").replace("\r\n", "\n")

ORIENT_BLOCK = '''  if (context.mode === "orientation") {
    return (
      <div style={{ display: "grid", gap: 14 }}>
        <div style={{ ...cardStyle(), padding: 20 }}>
          <h3 style={sectionTitleStyle()}>Team Orientation</h3>
          <p style={{ margin: "8px 0 16px", color: "var(--muted)", lineHeight: 1.6 }}>{context.query}</p>
          {renderOrientationPanel(orientation)}
        </div>
        {renderExplanationPanel(context)}
        {renderReportPanel(context, onCopyReport, reportCopied)}
      </div>
    );
  }

  if (!context) {
    return (
      <div style={cardStyle()}>
        <h3 style={sectionTitleStyle()}>No Result Yet</h3>
        <p style={{ margin: "10px 0 0", color: "var(--muted)", lineHeight: 1.6 }}>
          Submit a query to load the first football analysis result.
        </p>
      </div>
    );
  }'''

FIXED_BLOCK = '''  if (!context) {
    return (
      <div style={cardStyle()}>
        <h3 style={sectionTitleStyle()}>No Result Yet</h3>
        <p style={{ margin: "10px 0 0", color: "var(--muted)", lineHeight: 1.6 }}>
          Submit a query to load the first football analysis result.
        </p>
      </div>
    );
  }

  if (context.mode === "orientation") {
    return (
      <div style={{ display: "grid", gap: 14 }}>
        <div style={{ ...cardStyle(), padding: 20 }}>
          <h3 style={sectionTitleStyle()}>Team Orientation</h3>
          <p style={{ margin: "8px 0 16px", color: "var(--muted)", lineHeight: 1.6 }}>{context.query}</p>
          {renderOrientationPanel(orientation)}
        </div>
        {renderExplanationPanel(context)}
        {renderReportPanel(context, onCopyReport, reportCopied)}
      </div>
    );
  }'''

if ORIENT_BLOCK in content:
    content = content.replace(ORIENT_BLOCK, FIXED_BLOCK)
    print("Fixed order: null guard now before orientation check.")
else:
    # Show what's at the relevant area for debugging
    idx = content.find('if (context.mode === "orientation")')
    idx2 = content.find('if (!context)')
    print(f"Orientation check at char: {idx}")
    print(f"Null guard at char: {idx2}")
    print("Pattern not found verbatim — applying line-based swap...")
    lines = content.splitlines()
    orient_start = next((i for i,l in enumerate(lines) if 'if (context.mode === "orientation")' in l), -1)
    null_start = next((i for i,l in enumerate(lines) if 'if (!context)' in l and i > orient_start - 5), -1)
    print(f"  orient_start line: {orient_start}, null_start line: {null_start}")

src.write_text(content, encoding="utf-8")
print("Done.")
