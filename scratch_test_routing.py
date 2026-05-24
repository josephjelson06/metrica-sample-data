import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from backend.core.llm_router import route_analysis_query

queries = [
    "Show me the Home team's pass network",
    "Show me pass sonars for the Away team",
    "Show me the physicality dashboard for the Home team",
    "Analyze the Home team's set piece marking",
    "Show me dangerous transitions for the Home team",
]

for q in queries:
    print(f"\nQuery: {q}")
    try:
        res = route_analysis_query(q)
        mode = res.get("context", {}).get("mode")
        print(f"Success! Mode = {mode}")
    except Exception as e:
        print(f"Error! {e}")
