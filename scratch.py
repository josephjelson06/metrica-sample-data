import duckdb
import json

con = duckdb.connect()
res = con.query("DESCRIBE SELECT * FROM 'data/parquet/metrica_tracking.parquet'").fetchall()
print(json.dumps([col[0] for col in res]))
