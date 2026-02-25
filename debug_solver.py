import json
from src.engine.solver import LogisticsSolver
from src.config import LOCATIONS_FILE

with open(LOCATIONS_FILE, 'r', encoding='utf-8') as f:
    data = json.load(f)

solver = LogisticsSolver(data)
print(f"Nodes: {len(solver.nodes)}")
print(f"Matrix shape: {solver.distance_matrix.shape}")
routes = solver.solve()
if routes:
    print("Success")
else:
    print("Failed to find solution")
