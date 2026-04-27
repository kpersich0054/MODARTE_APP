import streamlit as st
import pandas as pd
import psycopg2
from pathlib import Path

# =====================
# CONFIG
# =====================
st.set_page_config(page_title="Modarte Catálogo", layout="wide")

# 🔥 REMOVE SIDEBAR
st.markdown("""
<style>
[data-testid="stSidebar"] {display: none;}
</style>
""", unsafe_allow_html=True)

BASE_DIR = Path(__file__).parent
PASTA_IMAGENS = BASE_DIR

# =====================
# CONEXÃO
# =====================
def get_conn():
    return psycopg2.connect(
        host=st.secrets["database"]["host"],
        port=st.secrets["database"]["port"],
        database=st.secrets["database"]["dbname"],
        user=st.secrets["database"]["user"],
        password=st.secrets["database"]["password"],
        sslmode=st.secrets["database"]["sslmode"]
    )

def query_df(sql):
    conn = get_conn()
    try:
        return pd.read_sql(sql, conn)
    finally:
        conn.close()

# =====================
# DADOS
# =====================
df = query_df("SELECT * FROM public.produtos")

# 🔥 SOMENTE ATIVOS
df = df[df["ativo"] == True].copy()

# 🔤 ORDEM ALFABÉTICA
df = df.sort_values(by="produto")

# =====================
# HEADER
# =====================
st.title("🛍️ Modarte")
st.caption("Escolha seu look ✨")

# =====================
# BUSCA
# =====================
busca = st.text_input("", placeholder="🔎 Buscar produto...")

if busca:
    df = df[df["produto"].str.contains(busca, case=False, na=False)]

# =====================
# FILTROS
# =====================
filtro = st.radio(
    "",
    ["Todos", "👗 Vestido", "🩳 Macaquinho", "✨ Nina"],
    horizontal=True
)

if filtro != "Todos":
    termo = filtro.split(" ")[-1]
    df = df[df["produto"].str.contains(termo, case=False)]

# =====================
# GRID DE PRODUTOS
# =====================
cols = st.columns(3)

for i, (_, row) in enumerate(df.iterrows()):
    col = cols[i % 3]

    with col:
        img_path = PASTA_IMAGENS / f"{row['codigo']}.jpg"
        img_logo = BASE_DIR / "Logo_Modarte.jpg"

        if img_path.exists():
            st.image(str(img_path), use_container_width=True)
        else:
            st.image(str(img_logo), use_container_width=True)

        st.markdown(f"### {row['produto']}")
        st.markdown(f"💰 **R$ {float(row['preco']):,.2f}**")

        # 🔥 BOTÃO WHATSAPP
        import urllib.parse

        msg = urllib.parse.quote(f"Olá! Tenho interesse no produto: {row['produto']}")
        link = f"https://wa.me/SEUNUMERO?text={msg}"

        st.markdown(f"[🛒 Comprar]({link})")
