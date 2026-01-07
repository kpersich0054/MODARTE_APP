import sqlite3
import psycopg2
import os

# SQLite
sqlite_conn = sqlite3.connect("modarte.db")
sqlite_conn.row_factory = sqlite3.Row
sqlite_cursor = sqlite_conn.cursor()

# Postgres (Supabase)
pg_conn = psycopg2.connect(
    host="db.tkmopzgpuvwgvhoekjnv.supabase.co",
    database="postgres",
    user="postgres",
    password="Pudim0206.2026",
    port=5432,
    sslmode="require"
)
pg_cursor = pg_conn.cursor()

# =============================
# MIGRAR PRODUTOS
# =============================
sqlite_cursor.execute("SELECT * FROM produtos")

for row in sqlite_cursor.fetchall():
    pg_cursor.execute("""
        INSERT INTO produtos (
            id, produto, codigo, preco, lucro,
            estoque_inicial, estoque_atual,
            foto, renda_atual, lucro_atual
        ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (id) DO NOTHING
    """, tuple(row))

pg_conn.commit()
print("✅ Produtos migrados")

# =============================
# MIGRAR VENDAS
# =============================
sqlite_cursor.execute("SELECT * FROM vendas")

for row in sqlite_cursor.fetchall():
    pg_cursor.execute("""
        INSERT INTO vendas (
            id, produto_id, quantidade,
            preco_unitario, data_venda
        ) VALUES (%s,%s,%s,%s,%s)
        ON CONFLICT (id) DO NOTHING
    """, tuple(row))

pg_conn.commit()
print("✅ Vendas migradas")

# =============================
# FECHAR CONEXÕES
# =============================
sqlite_conn.close()
pg_conn.close()

print("🚀 Migração completa!")
