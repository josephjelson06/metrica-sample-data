"""
Make the query input feel like a modern chat input:
- Enter submits, Shift+Enter for newline
- "Ask the analyst" placeholder text
- Send button styled as a tight action pill next to textarea
"""
from pathlib import Path

src = Path("frontend/components/analysis-workspace.tsx")
content = src.read_text(encoding="utf-8").replace("\r\n", "\n")

OLD_INPUT = '''        <label style={{ display: "flex", flexDirection: "column", gap: 10, fontWeight: 700 }}>
          <span style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            Natural language query
            <span style={{ fontSize: 11, fontWeight: 400, color: "var(--muted)", padding: "2px 8px", borderRadius: 999, background: "rgba(0,0,0,0.05)" }}>
              {!context ? "L1 Orientation" :
                context.mode === "orientation" ? "L1 → L2 Ready" :
                context.mode === "pass_network" || context.mode === "pass_sonars" ? "L2 Functional" :
                context.mode === "physicality" || context.mode === "auto_insights" ? "L3 Tactical" :
                context.mode === "set_piece" || context.mode === "comparison" ? "L3 Tactical" : "L2 Functional"}
            </span>
          </span>
          <textarea
            value={query}
            onChange={(event) => {
              const nextQuery = event.target.value;
              startTransition(() => setQuery(nextQuery));
            }}
            style={{
              minHeight: 124,
              resize: "vertical",
              borderRadius: 18,
              border: "1px solid rgba(20, 32, 19, 0.14)",
              padding: "14px 16px",
              background: "rgba(255,255,255,0.86)",
              color: "var(--ink)",
            }}
          />
        </label>

        <button
          type="button"
          onClick={() => sendQuery(query)}
          disabled={status === "connecting"}
          style={{
            border: 0,
            borderRadius: 999,
            padding: "14px 20px",
            fontWeight: 700,
            color: "#fff8ef",
            background: "linear-gradient(135deg, #a43408, #d75b1f)",
            boxShadow: "0 16px 30px rgba(194,65,12,0.26)",
            cursor: status === "connecting" ? "wait" : "pointer",
          }}
        >
          Run Analysis Query
        </button>'''

NEW_INPUT = '''        <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <strong style={{ fontSize: 14 }}>Ask the analyst</strong>
            <span style={{ fontSize: 11, fontWeight: 400, color: "var(--muted)", padding: "2px 8px", borderRadius: 999, background: "rgba(0,0,0,0.05)" }}>
              {!context ? "L1 Orientation" :
                context.mode === "orientation" ? "L1 → L2 Ready" :
                context.mode === "pass_network" || context.mode === "pass_sonars" ? "L2 Functional" :
                context.mode === "physicality" || context.mode === "auto_insights" ? "L3 Tactical" :
                context.mode === "set_piece" || context.mode === "comparison" ? "L3 Tactical" : "L2 Functional"}
            </span>
          </div>
          <div style={{ position: "relative" }}>
            <textarea
              value={query}
              placeholder="e.g. Show me the lineups, Show Home pass network from 30 to 45 mins…"
              onChange={(event) => {
                const nextQuery = event.target.value;
                startTransition(() => setQuery(nextQuery));
              }}
              onKeyDown={(event) => {
                if (event.key === "Enter" && !event.shiftKey) {
                  event.preventDefault();
                  if (query.trim() && status !== "connecting") {
                    sendQuery(query);
                  }
                }
              }}
              style={{
                width: "100%",
                minHeight: 96,
                resize: "vertical",
                borderRadius: 16,
                border: "1px solid rgba(20, 32, 19, 0.14)",
                padding: "12px 14px 44px 14px",
                background: "rgba(255,255,255,0.9)",
                color: "var(--ink)",
                boxSizing: "border-box",
                outline: "none",
                transition: "border-color 0.15s, box-shadow 0.15s",
              }}
              onFocus={(e) => {
                e.currentTarget.style.borderColor = "rgba(20,32,19,0.3)";
                e.currentTarget.style.boxShadow = "0 0 0 3px rgba(27,54,92,0.08)";
              }}
              onBlur={(e) => {
                e.currentTarget.style.borderColor = "rgba(20,32,19,0.14)";
                e.currentTarget.style.boxShadow = "none";
              }}
            />
            <button
              type="button"
              onClick={() => sendQuery(query)}
              disabled={status === "connecting" || !query.trim()}
              style={{
                position: "absolute",
                bottom: 10,
                right: 10,
                border: 0,
                borderRadius: 12,
                padding: "8px 18px",
                fontWeight: 700,
                fontSize: 13,
                color: "#fff8ef",
                background: query.trim() ? "linear-gradient(135deg, #a43408, #d75b1f)" : "rgba(0,0,0,0.12)",
                boxShadow: query.trim() ? "0 4px 14px rgba(194,65,12,0.3)" : "none",
                cursor: (status === "connecting" || !query.trim()) ? "not-allowed" : "pointer",
                transition: "all 0.2s",
              }}
            >
              {status === "connecting" ? "…" : "Send ↵"}
            </button>
          </div>
          <p style={{ margin: 0, fontSize: 11, color: "var(--muted)" }}>
            Press Enter to send · Shift+Enter for new line
          </p>
        </div>'''

if OLD_INPUT in content:
    content = content.replace(OLD_INPUT, NEW_INPUT)
    print("Upgraded query input to chat-style")
else:
    print("Pattern not found")
    # Debug
    idx = content.find('Run Analysis Query')
    print(f"'Run Analysis Query' at char {idx}")

src.write_text(content, encoding="utf-8")
print(f"Done. {len(content.splitlines())} lines.")
