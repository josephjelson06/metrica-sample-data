import sys
sys.path.insert(0, ".")
from backend.core.llm_router import route_analysis_query

tests = [
    ("Show me the lineups", {}),
    ("Show me the Home team pass network", {}),
    ("Show me Home pass network from 30 to 45 minutes", {"current_team": "Home"}),
    ("Show pass sonars for Away", {}),
    ("Show physicality for Home", {}),
    ("Show dangerous transitions for Away", {}),
    # Context inheritance: team not mentioned, should fall back to ctx_team
    ("Show the pass network", {"current_team": "Away", "current_period": None}),
]

for q, ctx in tests:
    try:
        res = route_analysis_query(q, ctx)
        mode = res.get("context", {}).get("mode")
        suggestions = res.get("follow_up_suggestions", [])
        print(f"OK  [{mode:16}]  '{q[:50]}' -> {len(suggestions)} suggestions")
    except Exception as e:
        print(f"ERR [{q[:50]}]: {e}")
