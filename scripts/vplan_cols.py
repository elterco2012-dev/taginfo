"""Solo muestra columnas de vplan. SOLO LECTURA."""
import pyodbc
conn = pyodbc.connect("DSN=MSPA;", autocommit=True)
cur  = conn.cursor()
cur.execute("SELECT * FROM vplan WHERE 1=0")
print([d[0] for d in cur.description])
conn.close()
