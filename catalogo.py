import streamlit as st
import pandas as pd
import psycopg2
import uuid
from pathlib import Path
import urllib.parse
from streamlit_autorefresh import st_autorefresh   
import base64
import streamlit as st
from pathlib import Path

def image_to_base64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("utf-8")

# =====================
# CONFIG
# =====================
st_autorefresh(interval=3000, key="refresh_stock")

st.set_page_config(page_title="Modarte Catálogo", layout="wide")

BASE_DIR = Path(__file__).parent
PASTA_IMAGENS = BASE_DIR

bg_path = BASE_DIR / "Modarte_background.jpg"

if not bg_path.exists():
    st.write("BASE_DIR:", str(BASE_DIR))
    st.write("Arquivos em BASE_DIR:")
    st.write([p.name for p in BASE_DIR.iterdir()])

    st.write("PNGs encontrados:")
    st.write([str(p) for p in BASE_DIR.rglob("*.jpg")])
    st.error(f"Não encontrei: {bg_path}\n Confira nome (maiúsculas/minúsculas) e commit.")
    st.stop()

bg_b64 = image_to_base64(bg_path)

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
# CSS
# =====================
def get_config():
    df = query_df("SELECT * FROM config_loja LIMIT 1")

    if df.empty:
        return {
            "primary_light": "#03B6FD",
            "secondary_light": "#A8D7FF",
            "background_light": "#E6F2FF",
            "card_light": "#FFFFFF",
            "text_light": "#002436",
            "primary_dark": "#028EC7",
            "secondary_dark": "#016893",
            "background_dark": "#021317",
            "card_dark": "#0A2E36",
            "text_dark": "#E6F2FF"
        }

    return df.iloc[0]

config = get_config()

st.markdown(f"""
<style>
header[data-testid="stHeader"] {{
  background: transparent !important;
  height: 0px !important;
}}

div[data-testid="stToolbar"] {{
  top: 0;
}}

.modarte-hero {{
  position: relative;
  left: 50%;
  margin-left: -50vw;
  width: 100vw;
}}

.modarte-hero img {{
  width: 100%;
  height: 250px;
  object-fit: cover;
  display: block;
}}

/* MOBILE */
@media (max-width: 768px) {{
  .modarte-hero img {{
    height: auto;
    max-height: 180px;
    object-fit: contain;
  }}
}}

/* conteúdo acima do overlay */
.modarte-content {{
  position: relative;
  z-index: 2;
  color: white;
  font-size: 42px;
  font-weight: bold;
}}

/* ===== APP CONTAINER ===== */
section[data-testid="stAppViewContainer"] {{
  padding-top: 0 !important;
  background: var(--bg-light) !important;
  color: var(--text-light) !important;
}}

html[data-theme="dark"] section[data-testid="stAppViewContainer"] {{
  padding-top: 0 !important;
  background: var(--bg-dark) !important;
  color: var(--text-dark) !important;
}}

</style>

<div class="modarte-hero">
    <img src="data:image/png;base64,{bg_b64}">
</div>

""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

st.markdown(f"""
<style>
/* =========================
   VARIÁVEIS
========================= */
:root {{
    --primary-light: {config['primary_light']};
    --secondary-light: {config['secondary_light']};
    --bg-light: {config['background_light']};
    --card-light: {config['card_light']};
    --text-light: {config['text_light']};

    --primary-dark: {config['primary_dark']};
    --secondary-dark: {config['secondary_dark']};
    --bg-dark: {config['background_dark']};
    --card-dark: {config['card_dark']};
    --text-dark: {config['text_dark']};
}}

/* ===== RESET / BASE ===== */
html, body {{
  margin: 0 !important;
  padding: 0 !important;
  width: 100% !important;
  overflow-x: hidden !important;   /* mata scroll horizontal */
}}

*, *::before, *::after {{
  box-sizing: border-box !important;
}}

/* ===== FUNDO GLOBAL (pega o topo também) ===== */
html, body, #root {{
  background: var(--bg-light) !important;
}}

html[data-theme="dark"] html,
html[data-theme="dark"] body,
html[data-theme="dark"] #root {{
  background: var(--bg-dark) !important;
}}

/* ===== SIDEBAR ===== */
section[data-testid="stSidebar"] {{
  background: var(--secondary-light) !important;
}}
html[data-theme="dark"] section[data-testid="stSidebar"] {{
  background: var(--secondary-dark) !important;
}}

/* ===== IMAGEM (CORRIGE SCROLL HORIZONTAL) ===== */
[data-testid="stImage"] img {{
  width: 100% !important;      /* era 150% -> isso criava scroll embaixo */
  height: 250px !important;
  object-fit: cover !important;
  border-radius: 12px !important;
  display: block !important;
}}

/* =========================
   FORÇA TEXTO (IMPORTANTE)
========================= */
section[data-testid="stAppViewContainer"] * {{
    color: var(--text-light);
}}

html[data-theme="dark"] section[data-testid="stAppViewContainer"] * {{
    color: var(--text-dark);
}}

/* =========================
   BOTÃO
========================= */
.buy-btn button {{
    background: var(--primary-light);
    color: white;
    border-radius: 10px;
    font-weight: bold;
}}

html[data-theme="dark"] .buy-btn button {{
    background: var(--primary-dark);
    color: black;
    border-radius: 10px;
    font-weight: bold;
}}

/* =========================
   PREÇO
========================= */
.price {{
    color: var(--primary-light);
    font-size: 20px;
    font-weight: bold;
}}

html[data-theme="dark"] .price {{
    color: var(--primary-dark);
    font-size: 20px;
    font-weight: bold;
}}

/* =========================
   CARDS
========================= */
.card {{
    background: transparent !important;
    border: 1px solid rgba(255,255,255,.10);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    height: 100%;
    transition: 0.2s;
}}

html[data-theme="dark"] .card {{
    background: transparent !important;
    border: 1px solid rgba(255,255,255,.10);
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    height: 100%;
    transition: 0.2s;
}}

/* =========================
   TEXTO
========================= */
.prod-title {{
    font-weight: 600;
    font-size: 14px;
    min-height: 42px;
}}

.stock {{
    font-size: 14px;
    color: #888;
}}

</style>
""", unsafe_allow_html=True)

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

st.title("Escolha seu look ✨")

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

            pedido_id = str(uuid.uuid4())
            
            for item in carrinho:
                cur.execute("""
                    INSERT INTO pedidos 
                    (pedido_id, produto_id, quantidade, preco_unitario, desconto, total, status)
                    VALUES (%s,%s,%s,%s,%s,%s,%s)
                """, (
                    pedido_id,
                    item["id"],
                    item["qtd"],
                    item["preco"],
                    desconto,
                    total,
                    "envio_whatsap"
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

            else:
                st.markdown("<div class='stock' style='color:#ff5252'>Sem estoque</div>", unsafe_allow_html=True)
                qtd = 0
