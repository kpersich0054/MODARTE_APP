import streamlit as st
import pandas as pd
import psycopg2
from pathlib import Path
import urllib.parse

# =====================
# CONFIG
# =====================
st.set_page_config(page_title="Modarte Catálogo", layout="wide")

# =====================
# CSS FINAL
# =====================
st.markdown("""
<style>

/* RESET */
div[data-testid="column"] > div,
div[data-testid="stVerticalBlock"] > div,
div[data-testid="element-container"] {
    background: transparent !important;
    box-shadow: none !important;
    border: none !important;
}

div[data-testid="stNumberInput"] > div {
    background: transparent !important;
}

div[data-testid="column"] {
    padding: 0 !important;
}

/* CARD */
html[data-theme="light"] .card {
    background: #ffffff;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}

html[data-theme="dark"] .card {
    background: linear-gradient(145deg, #1e1e1e, #252525);
    box-shadow: 0 6px 18px rgba(0,0,0,0.4);
}

.card {
    border-radius: 18px;
    padding: 16px;
    display: flex;
    flex-direction: column;
    height: 100%;
}

.card:hover {
    transform: translateY(-4px);
}

.prod-title {
    font-size: 14px;
    font-weight: 600;
}

.price {
    color: #00c853;
    font-weight: bold;
    font-size: 20px;
}

.stock {
    font-size: 12px;
    color: #888;
}

/* BOTÕES */
.card-actions button {
    width: 100%;
    height: 40px;
}

.buy-btn button {
    background-color: #00c853;
    color: white;
    font-weight: bold;
    border-radius: 10px;
}

</style>
""", unsafe_allow_html=True)

BASE_DIR = Path(__file__).parent

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
df = df[df["ativo"] == True].copy()
df = df.sort_values(by="produto")

# =====================
# HEADER
# =====================
st.title("🛍️ Modarte")
st.caption("Escolha seu look ✨")

# =====================
# FILTRO
# =====================
busca = st.text_input("", placeholder="🔎 Buscar produto...")

if busca:
    df = df[df["produto"].str.contains(busca, case=False, na=False)]

# =====================
# ESTADO
# =====================
if "favoritos" not in st.session_state:
    st.session_state.favoritos = set()

if "carrinho" not in st.session_state:
    st.session_state.carrinho = []

# =====================
# SIDEBAR
# =====================
st.sidebar.title("🛒 Carrinho")

total = 0
for item in st.session_state.carrinho:
    st.sidebar.write(f"{item['produto']} x{item['qtd']} - R$ {item['preco']:.2f}")
    total += item["preco"] * item["qtd"]

st.sidebar.write(f"Total: R$ {total:.2f}")

# =====================
# GRID
# =====================
cols = st.columns(4)

for i, (_, row) in enumerate(df.iterrows()):
    with cols[i % 4]:

        st.markdown('<div class="card">', unsafe_allow_html=True)

        st.image("Logo_Modarte.jpg", use_container_width=True)

        st.markdown(f"<div class='prod-title'>{row['produto']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='price'>R$ {float(row['preco']):,.2f}</div>", unsafe_allow_html=True)

        if row["estoque_atual"] > 0:
            st.markdown(f"<div class='stock'>Estoque: {int(row['estoque_atual'])}</div>", unsafe_allow_html=True)
            qtd = st.number_input("", min_value=1, max_value=int(row["estoque_atual"]), value=1, key=f"qtd_{row['id']}")
        else:
            st.markdown("<div class='stock' style='color:red'>Sem estoque</div>", unsafe_allow_html=True)
            qtd = 0

        # AÇÕES
        col1, col2 = st.columns(2)

        with col1:
            icone = "❤️" if row["id"] in st.session_state.favoritos else "🤍"
            if st.button(icone, key=f"fav_{row['id']}"):
                if row["id"] in st.session_state.favoritos:
                    st.session_state.favoritos.remove(row["id"])
                else:
                    st.session_state.favoritos.add(row["id"])

        with col2:
            if st.button("🛒", key=f"cart_{row['id']}") and qtd > 0:
                item_existente = next(
                    (i for i in st.session_state.carrinho if i["id"] == row["id"]),
                    None
                )

                if item_existente:
                    item_existente["qtd"] += qtd
                else:
                    st.session_state.carrinho.append({
                        "id": row["id"],
                        "produto": row["produto"],
                        "preco": float(row["preco"]),
                        "qtd": qtd
                    })

                st.success("Adicionado!")

        if st.button("Comprar agora", key=f"buy_{row['id']}") and qtd > 0:
            msg = urllib.parse.quote(
                f"Olá! Quero o produto:\n{row['produto']}\nQuantidade: {qtd}"
            )
            link = f"https://wa.me/5511964336480?text={msg}"

            st.success("Reservado!")
            st.markdown(f"[👉 Abrir WhatsApp]({link})")

        st.markdown('</div>', unsafe_allow_html=True)
