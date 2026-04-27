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
# CSS CORRIGIDO (🔥 SEM FUNDO BRANCO + IMAGEM PADRÃO)
# =====================
st.markdown("""
<style>

/* CARD */
.card {
    border-radius: 15px;
    padding: 12px;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    background-color: var(--secondary-background-color);
    margin-bottom: 15px;
}

/* IMAGEM PADRONIZADA (🔥 ISSO RESOLVE TUDO) */
[data-testid="stImage"] img {
    height: 220px !important;
    width: 100% !important;
    object-fit: contain !important;  /* 🔥 mantém proporção */
    border-radius: 10px;
}

/* TEXTO */
.card h4 {
    margin-top: 10px;
    margin-bottom: 5px;
    color: var(--text-color);
}

.card p {
    margin: 0;
    color: var(--text-color);
}

/* BOTÕES */
.card-actions {
    margin-top: 10px;
}

/* REMOVE QUALQUER FUNDO BRANCO */
img {
    background: transparent !important;
}

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
df = df[df["ativo"] == True].copy()
df = df.sort_values(by="produto")

# =====================
# HEADER
# =====================
st.title("🛍️ Modarte")
st.caption("Escolha seu look ✨")

# =====================
# BUSCA + FILTRO
# =====================
c1, c2 = st.columns([3, 2])

with c1:
    busca = st.text_input("", placeholder="🔎 Buscar produto...")

with c2:
    filtro = st.radio(
        "",
        ["Todos", "👗 Vestido", "🩳 Macaquinho", "✨ Nina"],
        horizontal=True
    )

if busca:
    df = df[df["produto"].str.contains(busca, case=False, na=False)]

if filtro != "Todos":
    termo = filtro.split(" ")[-1]
    df = df[df["produto"].str.contains(termo, case=False)]

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

st.sidebar.markdown("---")
st.sidebar.write(f"**Total: R$ {total:.2f}**")

if st.session_state.carrinho:
    pedido = "\n".join([f"{i['produto']} x{i['qtd']}" for i in st.session_state.carrinho])
    msg = urllib.parse.quote(f"Olá! Quero fazer um pedido:\n{pedido}")
    link = f"https://wa.me/5511999999999?text={msg}"
    st.sidebar.markdown(f"[📲 Finalizar pedido]({link})")

# =====================
# FAVORITOS
# =====================
mostrar_fav = st.checkbox("❤️ Ver favoritos")

if mostrar_fav:
    df = df[df["id"].isin(st.session_state.favoritos)]

# =====================
# GRID 4 COLUNAS
# =====================
cols = st.columns(4)

for i, (_, row) in enumerate(df.iterrows()):
    col = cols[i % 4]

    with col:
        img_path = PASTA_IMAGENS / f"{row['codigo']}.jpg"
        img_logo = BASE_DIR / "Logo_Modarte.jpg"

        img = str(img_path) if img_path.exists() else str(img_logo)

        # 🔥 CARD
        st.markdown('<div class="card">', unsafe_allow_html=True)

        # 🔥 IMAGEM (AGORA PADRONIZADA)
        st.image(img, use_container_width=True)

        # 🔥 TEXTO
        st.markdown(f"<h4>{row['produto']}</h4>", unsafe_allow_html=True)
        st.markdown(f"<p><b>R$ {float(row['preco']):,.2f}</b></p>", unsafe_allow_html=True)

        # 🔥 BOTÕES
        b1, b2, b3 = st.columns(3)

        # ❤️ FAVORITO
        with b1:
            icone = "❤️" if row["id"] in st.session_state.favoritos else "🤍"
            if st.button(icone, key=f"fav_{row['id']}"):
                if row["id"] in st.session_state.favoritos:
                    st.session_state.favoritos.remove(row["id"])
                else:
                    st.session_state.favoritos.add(row["id"])

        # 🛒 CARRINHO
        with b2:
            if st.button("🛒", key=f"cart_{row['id']}"):
                item_existente = next(
                    (i for i in st.session_state.carrinho if i["id"] == row["id"]),
                    None
                )

                if item_existente:
                    item_existente["qtd"] += 1
                else:
                    st.session_state.carrinho.append({
                        "id": row["id"],
                        "produto": row["produto"],
                        "preco": float(row["preco"]),
                        "qtd": 1
                    })

        # 📲 WHATS
        with b3:
            msg = urllib.parse.quote(f"Olá! Quero o produto: {row['produto']}")
            link = f"https://wa.me/5511999999999?text={msg}"
            st.markdown(f"[💬]({link})")

        st.markdown('</div>', unsafe_allow_html=True)
