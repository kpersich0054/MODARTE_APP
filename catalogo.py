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
# CSS
# =====================
st.markdown("""
<style>

/* =========================
   RESET GERAL
========================= */
div[data-testid="column"] > div,
div[data-testid="stVerticalBlock"] > div {
    background: transparent !important;
    box-shadow: none !important;
    border: none !important;
}

/* REMOVE FUNDO DO NUMBER INPUT (CAUSADOR DO BUG) */
div[data-testid="stNumberInput"] > div {
    background: transparent !important;
}

/* REMOVE PADDING DAS COLUNAS */
div[data-testid="column"] {
    padding: 0 !important;
}

/* =========================
   CARD (LIGHT / DARK)
========================= */

/* 🌞 LIGHT MODE */
html[data-theme="light"] .card {
    background: #ffffff;
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
}

/* 🌙 DARK MODE */
html[data-theme="dark"] .card {
    background: linear-gradient(145deg, #1e1e1e, #252525);
    box-shadow: 0 6px 18px rgba(0,0,0,0.4);
}

/* CARD BASE */
.card {
    border-radius: 18px;
    padding: 16px;

    display: flex;
    flex-direction: column;
    justify-content: space-between;

    height: 100%;
    transition: 0.2s;
}

.card:hover {
    transform: translateY(-4px);
}

/* CONTEÚDO */
.card-content {
    flex-grow: 1;
}

/* AÇÕES */
.card-actions {
    margin-top: 10px;
}

/* BOTÕES COLADOS */
.card-actions > div {
    gap: 6px !important;
}

/* BOTÕES PEQUENOS */
.card-actions button {
    width: 40px !important;
    height: 40px !important;
    padding: 0 !important;
}

/* IMAGEM */
[data-testid="stImage"] img {
    height: 250px !important;
    width: 150% !important;
    object-fit: cover !important;
    border-radius: 12px;
}

/* TITULO */
.prod-title {
    font-weight: 600;
    font-size: 14px;
    min-height: 42px;
}

/* PREÇO */
.price {
    font-size: 20px;
    font-weight: bold;
    color: #00c853;
}

/* ESTOQUE */
.stock {
    font-size: 12px;
    color: #888;
}

/* BOTÃO PRINCIPAL */
.buy-btn button {
    background-color: #00c853;
    color: white;
    font-weight: bold;
    border-radius: 10px;
    height: 38px;
}

/* INPUT */
.stNumberInput {
    min-height: 70px;
}


</style>
""", unsafe_allow_html=True)

BASE_DIR = Path(__file__).parent
PASTA_IMAGENS = BASE_DIR

# =====================
# CONEXÃO SEGURA
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
    try:
        conn = get_conn()
        df = pd.read_sql(sql, conn)
        conn.close()
        return df
    except Exception as e:
        st.error(f"Erro ao conectar no banco: {e}")
        return pd.DataFrame()
       
# =====================
# FUNÇÃO DE CÁLCULO
# =====================
def calcular_total(carrinho):
    total_bruto = sum(i["preco"] * i["qtd"] for i in carrinho)
    qtd_total = sum(i["qtd"] for i in carrinho)

    desconto = 5 * qtd_total if qtd_total >= 3 else 0
    total = total_bruto - desconto

    return total_bruto, desconto, total

# =====================
# DADOS
# =====================
df = query_df("SELECT * FROM public.produtos")

if df.empty:
    st.warning("Nenhum produto carregado.")
    st.stop()

df = df[df["ativo"] == True].copy()
df = df.sort_values(by="produto")

# =====================
# ESTADO
# =====================
if "favoritos" not in st.session_state:
    st.session_state.favoritos = set()

if "carrinho" not in st.session_state:
    st.session_state.carrinho = []

if "checkout" not in st.session_state:
    st.session_state.checkout = []

if "show_dialog" not in st.session_state:
    st.session_state.show_dialog = False

# =====================
# HEADER
# =====================
st.title("🛍️ Modarte")
st.caption("Escolha seu look ✨")

# =====================
# FILTROS
# =====================
c1, c2 = st.columns([3,2])

with c1:
    busca = st.text_input("", placeholder="🔎 Buscar produto...")

with c2:
    filtro = st.radio("", ["Todos", "👗 Vestido", "🩳 Macaquinho", "✨ Nina"], horizontal=True)

if busca:
    df = df[df["produto"].str.contains(busca, case=False, na=False)]

if filtro != "Todos":
    termo = filtro.split(" ")[-1]
    df = df[df["produto"].str.contains(termo, case=False)]

# =====================
# SIDEBAR
# =====================
st.sidebar.title("🛒 Carrinho")

total_bruto, desconto, total = calcular_total(st.session_state.carrinho)

for item in st.session_state.carrinho:
    st.sidebar.write(f"{item['produto']} x{item['qtd']}")

st.sidebar.write(f"Subtotal: R$ {total_bruto:.2f}")

if desconto > 0:
    st.sidebar.write(f"Desconto: -R$ {desconto:.2f} 🎉")

st.sidebar.write(f"**Total: R$ {total:.2f}**")
st.sidebar.markdown("---")

# =====================
# CONFIRMAR PEDIDO (ABRE DIALOG)
# =====================
if st.session_state.carrinho:
    if st.sidebar.button("📦 Confirmar pedido"):
        st.session_state.checkout = st.session_state.carrinho.copy()
        st.session_state.show_dialog = True
        st.rerun()

# =====================
# DIALOG
# =====================
@st.dialog("Finalizar pedido")
def dialog_checkout():

    carrinho = st.session_state.checkout
    total_bruto, desconto, total = calcular_total(carrinho)

    st.subheader("🧾 Resumo do pedido")

    for item in carrinho:
        st.write(f"{item['produto']} x{item['qtd']}")

    st.markdown("---")
    st.write(f"Subtotal: R$ {total_bruto:.2f}")

    if desconto > 0:
        st.write(f"Desconto: -R$ {desconto:.2f} 🎉")

    st.write(f"**Total: R$ {total:.2f}**")

    # WhatsApp
    pedido_linhas = []

    for item in carrinho:
        preco_unit = item["preco"]
        qtd = item["qtd"]
        total_item = preco_unit * qtd

        pedido_linhas.append(
            f"{item['produto']} x{qtd}\n"
            f"  • Unitário: R$ {preco_unit:.2f}\n"
            f"  • Total: R$ {total_item:.2f}"
        )

    pedido_txt = "\n\n".join(pedido_linhas)

    msg = f"""Olá! Quero fazer um pedido:

{pedido_txt}

Subtotal: R$ {total_bruto:.2f}
Desconto: -R$ {desconto:.2f}
Total: R$ {total:.2f}
"""

    link = f"https://wa.me/5511964336480?text={urllib.parse.quote_plus(msg)}"

    st.markdown(f"""
    <a href="{link}" target="_blank"
       style="display:block;text-align:center;background:#25D366;
       color:black;padding:12px;border-radius:10px;font-weight:bold;">
       📲 Abrir WhatsApp
    </a>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns(2)

    # CONFIRMAR
    with col1:
        if st.button("✔ Já enviei"):

            conn = get_conn()
            cur = conn.cursor()

            for item in carrinho:
                cur.execute("""
                    INSERT INTO pedidos 
                    (produto_id, quantidade, preco_unitario, desconto, total, status)
                    VALUES (%s,%s,%s,%s,%s,%s)
                """, (
                    item["id"],
                    item["qtd"],
                    item["preco"],
                    desconto,
                    total,
                    "confirmado"
                ))

            conn.commit()
            conn.close()

            # limpa tudo
            st.session_state.carrinho = []
            st.session_state.checkout = []
            st.session_state.show_dialog = False

            st.success("Pedido confirmado!")
            st.rerun()

    # CANCELAR
    with col2:
        if st.button("❌ Cancelar"):
            st.session_state.show_dialog = False
            st.rerun()

# abrir dialog
if st.session_state.show_dialog:
    dialog_checkout()
    
# =====================
# SUCESSO
# =====================
if st.session_state.get("sucesso"):
    st.sidebar.success("Pedido em analise")
    if st.sidebar.button("OK"):
        st.session_state.sucesso = False
        st.rerun()

# =====================
# FAVORITOS
# =====================
mostrar_fav = st.checkbox("❤️ Ver favoritos")

if mostrar_fav:
    df = df[df["id"].isin(st.session_state.favoritos)]

# =====================
# GRID
# =====================
n_cols = 4
rows = [df[i:i+n_cols] for i in range(0, len(df), n_cols)]

for row_group in rows:
    cols = st.columns(n_cols)

    for col, (_, row) in zip(cols, row_group.iterrows()):
        with col:

            img_path = PASTA_IMAGENS / f"{row['codigo']}.jpg"
            img_logo = BASE_DIR / "Logo_Modarte.jpg"
            img = str(img_path) if img_path.exists() else str(img_logo)

            st.markdown('<div class="card">', unsafe_allow_html=True)

            st.image(img, use_container_width=True)

            st.markdown(f"<div class='prod-title'>{row['produto']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='price'>R$ {float(row['preco']):,.2f}</div>", unsafe_allow_html=True)

            if row["estoque_atual"] > 0:
                st.markdown(f"<div class='stock'>Estoque: {int(row['estoque_atual'])}</div>", unsafe_allow_html=True)
                qtd = st.number_input("", 1, int(row["estoque_atual"]), 1, key=f"qtd_{row['id']}")
            else:
                st.markdown("<div class='stock' style='color:#ff5252'>Sem estoque</div>", unsafe_allow_html=True)
                qtd = 0

            col1, col2 = st.columns(2)

            with col1:
                if st.button("❤️" if row["id"] in st.session_state.favoritos else "🤍", key=f"fav_{row['id']}"):
                    if row["id"] in st.session_state.favoritos:
                        st.session_state.favoritos.remove(row["id"])
                    else:
                        st.session_state.favoritos.add(row["id"])

            with col2:
                if st.button("🛒", key=f"cart_{row['id']}") and qtd > 0:
                    st.session_state.carrinho.append({
                        "id": row["id"],
                        "produto": row["produto"],
                        "preco": float(row["preco"]),
                        "qtd": qtd
                    })
                    st.rerun()

            # comprar agora (usa MESMO fluxo)
            if st.button("Comprar agora", key=f"buy_{row['id']}") and qtd > 0:
                st.session_state.checkout = [{
                    "id": row["id"],
                    "produto": row["produto"],
                    "preco": float(row["preco"]),
                    "qtd": qtd
                }]
                st.session_state.show_dialog = True
                st.rerun()

            st.markdown('</div>', unsafe_allow_html=True)
