import sys
sys.path.insert(0, ".")
from backend.tools.db_engine import get_lineup_and_roles, get_formation_estimate, get_pass_network_windowed

print("Testing get_lineup_and_roles (Home)...")
res = get_lineup_and_roles(team="Home")
for pid, info in list(res["lineup"].items())[:3]:
    print(f"  {pid}: role={info['role']}, avg_x={info['avg_x']}, p1={info['in_period_1']}, p2={info['in_period_2']}")

print("Testing get_formation_estimate...")
f = get_formation_estimate(team="Home", period=1)
print(f"  Home formation: {f['formation']}")
f2 = get_formation_estimate(team="Away", period=1)
print(f"  Away formation: {f2['formation']}")

print("Testing get_pass_network_windowed (30-45 min)...")
net = get_pass_network_windowed(team="Home", start_minute=30, end_minute=45)
print(f"  Nodes: {len(net['nodes'])}, Edges: {len(net['edges'])}, Total passes: {net['total_passes']}")

print("All OK!")
