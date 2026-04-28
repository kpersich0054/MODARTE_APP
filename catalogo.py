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
# DADOS
# =====================
df = query_df("SELECT * FROM public.produtos")

if df.empty:
    st.warning("Nenhum produto carregado.")
    st.stop()

df = df[df["ativo"] == True].copy()
df = df.sort_values(by="produto")

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

# =====================
# CONFIRMAR PEDIDO
# =====================
if st.session_state.carrinho:

    if st.sidebar.button("📦 Confirmar pedido"):

        try:
            pedido_txt = "\n".join([f"{i['produto']} x{i['qtd']}" for i in st.session_state.carrinho])
            msg = f"Olá! Quero fazer um pedido:\n{pedido_txt}"
            link = f"https://wa.me/5511964336480?text={urllib.parse.quote_plus(msg)}"

            conn = get_conn()
            cursor = conn.cursor()

            for item in st.session_state.carrinho:
                cursor.execute("""
                    INSERT INTO pedidos (produto_id, quantidade, status)
                    VALUES (%s, %s, 'pendente')
                """, (item["id"], item["qtd"]))

            conn.commit()
            conn.close()

            st.session_state.link_whatsapp = link
            st.session_state.aguardando_whatsapp = True

            st.rerun()

        except Exception as e:
            st.error(f"Erro ao finalizar pedido: {e}")

# =====================
# CONFIRMAR VIA WHATSAPP
# =====================
if st.session_state.get("aguardando_whatsapp"):

    st.info("Finalize seu pedido no WhatsApp 👇")

    col1, col2 = st.columns([1,1])

    with col1:
        if st.button("📲 Abrir WhatsApp"):
            st.session_state.pedido_confirmado = True
            st.session_state.aguardando_whatsapp = False
            st.session_state.carrinho = []
            st.markdown(f"""
            <script>
                window.open("{st.session_state.link_whatsapp}", "_blank");
            </script>
            """, unsafe_allow_html=True)
            st.rerun()

    with col2:
        if st.button("Cancelar"):
            st.session_state.aguardando_whatsapp = False
            st.rerun()
            
# =====================
# SUCESSO FINAL
# =====================
if st.session_state.get("pedido_confirmado"):

    st.success("🎉 Pedido enviado com sucesso!")

    if st.button("OK"):
        st.session_state.pedido_confirmado = False
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

            if st.button("Comprar agora", key=f"buy_{row['id']}") and qtd > 0:
                msg = urllib.parse.quote(f"Olá! Quero o produto:\n{row['produto']}\nQuantidade: {qtd}")
                link = f"https://wa.me/5511964336480?text={msg}"
                st.markdown(f"[👉 Abrir WhatsApp]({link})")

            st.markdown('</div>', unsafe_allow_html=True)
