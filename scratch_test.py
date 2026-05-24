import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))

from backend.tools.db_engine import get_pass_network, get_pass_sonars, get_physicality_summary, find_dangerous_transitions

print("Testing get_pass_network...")
try:
    res = get_pass_network(team="Home")
    print("Pass network OK", len(res.get("nodes", [])))
except Exception as e:
    print("Pass network ERROR", e)

print("Testing get_pass_sonars...")
try:
    res = get_pass_sonars(team="Home")
    print("Pass sonars OK", len(res.get("players", {})))
except Exception as e:
    print("Pass sonars ERROR", e)

print("Testing get_physicality_summary...")
try:
    res = get_physicality_summary(team="Home")
    print("Physicality OK", len(res.get("leaderboard", [])))
except Exception as e:
    print("Physicality ERROR", e)

print("Testing find_dangerous_transitions...")
try:
    res = find_dangerous_transitions(team="Home")
    print("Transitions OK", len(res))
except Exception as e:
    print("Transitions ERROR", e)
