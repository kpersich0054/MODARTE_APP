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
# CSS CORRIGIDO
# =====================
st.markdown("""
<style>

/* REMOVE FUNDO DOS BLOCOS DAS COLUNAS (retângulo cinza) */
div[data-testid="column"] > div {
    background: transparent !important;
    box-shadow: none !important;
    border: none !important;
}

/* REMOVE PADDING DAS COLUNAS */
div[data-testid="column"] {
    padding: 0 !important;
}

/* CARD */
.card {
    border-radius: 18px;
    padding: 16px;
    background: linear-gradient(145deg, #1e1e1e, #252525);
    box-shadow: 0 6px 18px rgba(0,0,0,0.25);

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
    height: 200px !important;
    width: 100% !important;
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
    color: #00e676;
}

/* ESTOQUE */
.stock {
    font-size: 12px;
    color: #bbb;
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
# FUNÇÃO
# =====================
def registrar_pre_compra(produto_id, quantidade):
    conn = get_conn()
    try:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO public.pre_compras (produto_id, quantidade, status)
            VALUES (%s, %s, 'pendente')
        """, (produto_id, quantidade))

        cursor.execute("""
            UPDATE public.produtos
            SET estoque_atual = estoque_atual - %s
            WHERE id = %s
        """, (quantidade, produto_id))

        conn.commit()

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()

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

            # CONTEÚDO
            st.markdown('<div class="card-content">', unsafe_allow_html=True)

            st.image(img, use_container_width=True)

            st.markdown(f"<div class='prod-title'>{row['produto']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='price'>R$ {float(row['preco']):,.2f}</div>", unsafe_allow_html=True)

            if row["estoque_atual"] > 0:
                st.markdown(f"<div class='stock'>Estoque: {int(row['estoque_atual'])}</div>", unsafe_allow_html=True)
                qtd = st.number_input("", min_value=1, max_value=int(row["estoque_atual"]), value=1, key=f"qtd_{row['id']}")
            else:
                st.markdown("<div class='stock' style='color:#ff5252'>Sem estoque</div>", unsafe_allow_html=True)
                st.number_input("", min_value=0, max_value=0, value=0, disabled=True, key=f"qtd_{row['id']}")
                qtd = 0

            st.markdown('</div>', unsafe_allow_html=True)

            # AÇÕES
            st.markdown('<div class="card-actions">', unsafe_allow_html=True)

            b1, b2 = st.columns([1,1], gap="small")

            with b1:
                icone = "❤️" if row["id"] in st.session_state.favoritos else "🤍"
                if st.button(icone, key=f"fav_{row['id']}"):
                    if row["id"] in st.session_state.favoritos:
                        st.session_state.favoritos.remove(row["id"])
                    else:
                        st.session_state.favoritos.add(row["id"])

            with b2:
                if st.button("🛒", key=f"cart_{row['id']}") and qtd > 0:
                    item_existente = next((i for i in st.session_state.carrinho if i["id"] == row["id"]), None)

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

            st.markdown('<div class="buy-btn">', unsafe_allow_html=True)

            if st.button("Comprar agora", key=f"buy_{row['id']}") and qtd > 0:
                try:
                    registrar_pre_compra(row["id"], qtd)

                    msg = urllib.parse.quote(f"Olá! Quero o produto:\n{row['produto']}\nQuantidade: {qtd}")
                    link = f"https://wa.me/5511964336480?text={msg}"

                    st.success("Reservado!")
                    st.markdown(f"[👉 Abrir WhatsApp]({link})")

                except Exception as e:
                    st.error(f"Erro: {e}")

            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
