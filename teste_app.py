import streamlit as st
import pandas as pd
import psycopg2
from pathlib import Path
from datetime import datetime, timedelta

# =====================
# CONFIG
# =====================
BASE_DIR = Path(__file__).parent
PASTA_IMAGENS = BASE_DIR

@st.cache_resource
def get_conn():
    return psycopg2.connect(
        host=st.secrets["database"]["host"],
        port=st.secrets["database"]["port"],
        database=st.secrets["database"]["dbname"],
        user=st.secrets["database"]["user"],
        password=st.secrets["database"]["password"],
        sslmode=st.secrets["database"]["sslmode"]
    )

st.set_page_config(page_title="MODARTE", layout="wide")

conn = get_conn()

# =====================
# FUNÇÕES
# =====================
def gerar_codigo_produto(nome_produto, produto_id):
    palavras = nome_produto.strip().split()
    iniciais = ''.join([p[0].upper() for p in palavras if p])
    return f"{iniciais}{produto_id}"

def validar_produto(dados):
    if not dados["produto"]:
        return False, "Nome obrigatório"
    if dados["preco"] <= 0:
        return False, "Preço inválido"
    return True, ""

def registrar_venda(produto_id, quantidade, preco, lucro, data_venda):
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO public.vendas_modarte
        (produto_id, quantidade, data_venda, preco_unit, lucro_unit)
        VALUES (%s,%s,%s,%s,%s)
    """, (produto_id, quantidade, data_venda, preco, lucro))

    cursor.execute("""
        UPDATE public.produtos
        SET estoque_atual = estoque_atual - %s
        WHERE id = %s
    """, (quantidade, produto_id))

    conn.commit()

# =====================
# SIDEBAR
# =====================
st.sidebar.title("⚙️ Gerenciamento")

acao = st.sidebar.radio(
    "Escolha uma ação:",
    ["📦 Visualizar Produtos", "➕ Inserir Produto", "✏️ Alterar Produto", "💰 Registrar Venda", "🗑️ Excluir Produto"]
)

if st.sidebar.button("❌ Encerrar aplicação"):
    st.stop()

# =====================
# DADOS
# =====================
df = pd.read_sql("SELECT * FROM public.produtos", conn)

df_vendas = pd.read_sql("""
SELECT
    v.id,
    v.produto_id,
    p.produto,
    v.data_venda,
    v.quantidade,
    v.preco_unit,
    v.lucro_unit
FROM public.vendas_modarte v
JOIN public.produtos p ON p.id = v.produto_id
""", conn)

# =====================
# NORMALIZAÇÃO
# =====================
cols_num = ["estoque_inicial", "estoque_atual", "preco", "lucro"]

for col in cols_num:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

df_vendas["quantidade"] = pd.to_numeric(df_vendas["quantidade"], errors="coerce").fillna(0)
df_vendas["preco_unit"] = pd.to_numeric(df_vendas["preco_unit"], errors="coerce").fillna(0)
df_vendas["lucro_unit"] = pd.to_numeric(df_vendas["lucro_unit"], errors="coerce").fillna(0)
df_vendas["data_venda"] = pd.to_datetime(df_vendas["data_venda"], errors="coerce")

# =====================
# CRUD
# =====================

# =====================
# INSERIR PRODUTO
# =====================

if acao == "➕ Inserir Produto":
    st.subheader("➕ Inserir novo produto")

    with st.form("form_inserir"):
        produto = st.text_input("Produto")
        estoque_inicial = st.number_input("Estoque inicial", min_value=0)
        estoque_atual = st.number_input("Estoque atual", min_value=0)
        preco = st.number_input("Preço", min_value=0.0)
        lucro = st.number_input("Lucro", min_value=0.0)

        submit = st.form_submit_button("Salvar")

    if submit:
        dados = {
            "produto": produto,
            "estoque_inicial": estoque_inicial,
            "estoque_atual": estoque_atual,
            "preco": preco,
            "lucro": lucro,
        }

        valido, msg = validar_produto(dados)

        if not valido:
            st.error(msg)
        else:
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO public.produtos
                (produto, estoque_inicial, estoque_atual, preco, lucro)
                VALUES (%s,%s,%s,%s,%s)
                RETURNING id
            """, (
                produto,
                estoque_inicial,
                estoque_atual,
                preco,
                lucro
            ))

            produto_id = cursor.fetchone()[0]

            codigo = gerar_codigo_produto(produto, produto_id)
            foto_path = str(BASE_DIR / f"{codigo}.jpg")

            cursor.execute("""
                UPDATE public.produtos
                SET codigo=%s, foto=%s
                WHERE id=%s
            """, (codigo, foto_path, produto_id))

            conn.commit()
            st.success(f"Produto cadastrado! Código: {codigo}")
            st.rerun()

# =====================
# ALTERAR PRODUTO
# =====================
elif acao == "✏️ Alterar Produto":
    st.subheader("✏️ Alterar produto")

    produto_sel = st.selectbox("Selecione o produto", df["produto"])

    row = df[df["produto"] == produto_sel].iloc[0]
    produto_id = int(row["id"])

    with st.form("form_editar"):
        produto = st.text_input("Produto", row["produto"])
        estoque_inicial = st.number_input("Estoque inicial", value=int(row["estoque_inicial"]))
        estoque_atual = st.number_input("Estoque atual", value=int(row["estoque_atual"]))
        preco = st.number_input("Preço", value=float(row["preco"]))
        lucro = st.number_input("Lucro", value=float(row["lucro"]))

        submit = st.form_submit_button("Atualizar")

    if submit:
        cursor = conn.cursor()

        cursor.execute("""
        UPDATE public.produtos
        SET produto=%s, preco=%s, lucro=%s,
            estoque_inicial=%s, estoque_atual=%s
        WHERE id=%s
        """, (
            produto,
            preco,
            lucro,
            estoque_inicial,
            estoque_atual,
            produto_id
        ))

        conn.commit()
        st.success("Produto atualizado!")
        st.rerun()


# =====================
# REGISTRAR VENDA
# =====================
elif acao == "💰 Registrar Venda":
    st.subheader("💰 Registrar Venda")

    data_venda = st.date_input("Data da venda", value=datetime.today())

    # 🔥 FILTRO IMPORTANTE
    df_disponivel = df[df["estoque_atual"] > 0]

    if df_disponivel.empty:
        st.warning("⚠️ Nenhum produto com estoque disponível.")
        st.stop()

    produto_sel = st.selectbox(
        "Produto",
        df_disponivel["produto"]
    )

    row = df_disponivel[df_disponivel["produto"] == produto_sel].iloc[0]

    estoque_disp = int(row["estoque_atual"])

    quantidade = st.number_input(
        "Quantidade",
        min_value=1,
        max_value=estoque_disp,
        step=1
    )
    
    produto_sel = st.selectbox(
        "Produto",
        df_disponivel.apply(
            lambda x: f"{x['produto']} (Estoque: {int(x['estoque_atual'])})",
            axis=1
        )
    )

    if st.button("Confirmar venda"):
        registrar_venda(
            produto_id=int(row["id"]),
            quantidade=quantidade,
            preco=float(row["preco"]),
            lucro=float(row["lucro"]),
            data_venda=datetime.combine(data_venda, datetime.min.time())
        )

        st.success("Venda registrada!")
        st.rerun()

# =====================
# EXCLUIR PRODUTO
# =====================
elif acao == "🗑️ Excluir Produto":
    st.subheader("🗑️ Excluir produto")

    produto_sel = st.selectbox("Produto", df["produto"])

    if st.checkbox("Confirmar exclusão"):
        if st.button("Excluir"):
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM public.produtos WHERE produto=%s",
                (produto_sel,)
            )

            conn.commit()
            st.success("Produto excluído!")
            st.rerun()
            
# =====================
# DASHBOARD
# =====================
if acao == "📦 Visualizar Produtos":

    st.markdown("### 📅 Filtro de Período")

    tipo = st.selectbox("Período", ["Hoje", "7 dias", "30 dias", "Personalizado"])

    hoje = datetime.today()

    if tipo == "Hoje":
        inicio = hoje.replace(hour=0, minute=0, second=0)
        fim = hoje.replace(hour=23, minute=59, second=59)
    elif tipo == "7 dias":
        inicio = hoje - timedelta(days=7)
        fim = hoje
    elif tipo == "30 dias":
        inicio = hoje - timedelta(days=30)
        fim = hoje
    else:
        inicio = st.date_input("Início", hoje)
        fim = st.date_input("Fim", hoje)
        inicio = datetime.combine(inicio, datetime.min.time())
        fim = datetime.combine(fim, datetime.max.time())

    df_f = df_vendas[
        (df_vendas["data_venda"] >= inicio) &
        (df_vendas["data_venda"] <= fim)
    ]

    renda = (df_f["quantidade"] * df_f["preco_unit"]).sum()
    lucro = (df_f["quantidade"] * df_f["lucro_unit"]).sum()
    vendidos = df_f["quantidade"].sum()
    estoque = df["estoque_atual"].sum()

    st.title("📦 Painel de Produtos")
    st.caption(f"{inicio.strftime('%d/%m/%Y')} até {fim.strftime('%d/%m/%Y')}")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("💰 Renda", f"R$ {renda:,.2f}")
    c2.metric("📈 Lucro", f"R$ {lucro:,.2f}")
    c3.metric("🛒 Vendidos", int(vendidos))
    c4.metric("📦 Estoque", int(estoque))

    st.markdown("---")

    if not df_f.empty:
        st.line_chart(df_f.groupby(df_f["data_venda"].dt.date)["quantidade"].sum())

    st.markdown("---")

    # =====================
    # LISTA COMPLETA
    # =====================
    st.subheader("🧾 Lista de Produtos")

    for _, row in df.iterrows():
        col1, col2 = st.columns([1, 3])

        with col1:
            img_path = PASTA_IMAGENS / f"{row['codigo']}.jpg"
            img_logo = BASE_DIR / "Logo_Modarte.jpg"

            if img_path.exists():
                st.image(str(img_path), use_container_width=True)
            else:
                st.image(str(img_logo), use_container_width=True)

        with col2:
            st.subheader(row["produto"])

            estoque_inicial = int(row["estoque_inicial"])
            estoque_atual = int(row["estoque_atual"])
            preco = float(row["preco"])
            lucro_unit = float(row["lucro"])

            vendidos_real = df_vendas[
                df_vendas["produto_id"] == row["id"]
            ]["quantidade"].sum()

            renda_real = vendidos_real * preco
            lucro_real = vendidos_real * lucro_unit

            st.write(f"📦 **Estoque Inicial:** {estoque_inicial}")
            st.write(f"📦 **Estoque Atual:** {estoque_atual}")
            st.write(f"🛒 **Vendidos:** {int(vendidos_real)}")
            st.write(f"💰 **Preço:** R$ {preco:,.2f}")
            st.write(f"📈 **Lucro unidade:** R$ {lucro_unit:,.2f}")
            st.write(f"💵 **Renda Total:** R$ {renda_real:,.2f}")
            st.write(f"🏆 **Lucro Total:** R$ {lucro_real:,.2f}")

        st.markdown("---")
