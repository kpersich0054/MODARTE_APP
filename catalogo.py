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
# CSS AJUSTADO
# =====================
st.markdown("""
<style>

/* CARD */
.card {
    border-radius: 15px;
    padding: 12px;
    background-color: var(--secondary-background-color);
    box-shadow: 0 4px 12px rgba(0,0,0,0.08);
    margin-bottom: 15px;
}

/* IMAGEM PADRÃO */
[data-testid="stImage"] img {
    height: 180px !important;
    object-fit: contain !important;
    border-radius: 10px;
}

/* TEXTO */
.card h4, .card p {
    color: var(--text-color);
    margin: 0;
}

/* BOTÕES */
.actions {
    margin-top: 10px;
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
# GRID
# =====================

def registrar_pre_compra(produto_id, quantidade):
    conn = get_conn()
    try:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO public.pre_compras (produto_id, quantidade, status)
            VALUES (%s, %s, 'pendente')
        """, (produto_id, quantidade))

        # 🔥 opcional: reserva estoque
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
        
cols = st.columns(4)

for i, (_, row) in enumerate(df.iterrows()):
    col = cols[i % 4]

    with col:
        img_path = PASTA_IMAGENS / f"{row['codigo']}.jpg"
        img_logo = BASE_DIR / "Logo_Modarte.jpg"
        img = str(img_path) if img_path.exists() else str(img_logo)

        st.markdown('<div class="card">', unsafe_allow_html=True)

        # 🔥 LAYOUT HORIZONTAL
        c_img, c_info = st.columns([1, 2])

        with c_img:
            st.image(img, use_container_width=True)

        with c_info:
            st.markdown(f"**{row['produto']}**")
            st.markdown(f"💰 R$ {float(row['preco']):,.2f}")

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

            # QUANTIDADE
            qtd = st.number_input(
                "Qtd",
                min_value=1,
                max_value=int(row["estoque_atual"]),  # 🔥 estoque real
                value=1,
                key=f"qtd_{row['id']}"
            )
            
            with b2:
                if st.button("🛒", key=f"cart_{row['id']}"):

                    item_existente = next(
                        (i for i in st.session_state.carrinho if i["id"] == row["id"]),
                        None
                    )

                    if item_existente:
                        item_existente["qtd"] += qtd  # 🔥 usa o valor escolhido
                    else:
                        st.session_state.carrinho.append({
                        "id": row["id"],
                        "produto": row["produto"],
                        "preco": float(row["preco"]),
                        "qtd": qtd  # 🔥 salva quantidade
                    })

            # 📲 WHATS
            with b3:
                if st.button("📲 Comprar", key=f"buy_{row['id']}"):

                # 🔥 registra pré-compra
                registrar_pre_compra(row["id"], qtd)

                # 🔥 mensagem
                msg = urllib.parse.quote(
                    f"Olá! Quero o produto:\n{row['produto']}\nQuantidade: {qtd}"
                )

                link = f"https://wa.me/5511964336480?text={msg}"

                st.success("Produto reservado! Redirecionando...")

                st.markdown(f"[👉 Clique aqui para abrir o WhatsApp]({link})")

                st.markdown('</div>', unsafe_allow_html=True)
