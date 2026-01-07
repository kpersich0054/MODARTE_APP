import streamlit as st
import pandas as pd
import psycopg2
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from datetime import datetime
import tempfile
import os
import signal

def validar_produto(dados):
    campos_texto = ["produto", "foto", "codigo"]
    campos_num = ["estoque_inicial", "estoque_atual", "preco", "lucro"]

    for campo in campos_texto:
        if not dados[campo] or str(dados[campo]).strip() == "":
            return False, f"Campo '{campo}' não pode ficar vazio."

    for campo in campos_num:
        if dados[campo] <= 0:
            return False, f"Campo '{campo}' deve ser maior que zero."

    if dados["estoque_atual"] > dados["estoque_inicial"]:
        return False, "Estoque atual não pode ser maior que o estoque inicial."

    return True, ""

def gerar_pdf(df):
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")

    c = canvas.Canvas(temp_file.name, pagesize=A4)
    largura, altura = A4

    y = altura - 2 * cm

    # TÍTULO
    c.setFont("Helvetica-Bold", 16)
    c.drawString(2 * cm, y, "Relatório de Vendas - MODARTE")
    y -= 1 * cm

    c.setFont("Helvetica", 10)
    c.drawString(2 * cm, y, f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    y -= 1 * cm

    # KPIs
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2 * cm, y, f"Renda Total: R$ {df['renda_atual'].sum():,.2f}")
    y -= 0.6 * cm
    c.drawString(2 * cm, y, f"Lucro Total: R$ {df['lucro_atual'].sum():,.2f}")
    y -= 1 * cm

    # TABELA
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2 * cm, y, "Produtos:")
    y -= 0.5 * cm

    c.setFont("Helvetica", 9)
    for _, row in df.iterrows():
        texto = (
            f"{row['produto']} | "
            f"Vendidos: {int(row['vendidos'])} | "
            f"Renda: R$ {row['renda_atual']:,.2f}"
        )
        c.drawString(2 * cm, y, texto)
        y -= 0.45 * cm

        if y < 2 * cm:
            c.showPage()
            y = altura - 2 * cm
            c.setFont("Helvetica", 9)

    c.save()
    return temp_file.name

def registrar_venda(produto_id, quantidade, preco, lucro, data_venda):
    conn = get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO public.vendas_modarte
        (produto_id, quantidade, data_venda, preco_unit, lucro_unit)
        VALUES (%s,%s,%s,%s,%s)
    """, (
        produto_id,
        quantidade,
        data_venda,
        preco,
        lucro
    ))

    cursor.execute("""
        UPDATE public.produtos
        SET estoque_atual = estoque_atual - %s
        WHERE id = %s
    """, (quantidade, produto_id))

    conn.commit()

# =====================
# CONFIGURAÇÕES
# =====================

BASE_DIR = Path(__file__).parent

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

ESTOQUE_MINIMO = 5

st.set_page_config(
    page_title="MODARTE",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon=str(BASE_DIR / "Logo_Modarte.jpg")
)

# =====================
# CARREGAR DADOS
# =====================

conn = get_conn()

df = pd.read_sql(
    "SELECT * FROM public.produtos",
    conn
)

# Garantir tipos corretos
df["estoque_inicial"] = pd.to_numeric(df["estoque_inicial"], errors="coerce").fillna(0)
df["estoque_atual"] = pd.to_numeric(df["estoque_atual"], errors="coerce").fillna(0)
df["preco"] = pd.to_numeric(df["preco"], errors="coerce").fillna(0)
df["lucro"] = pd.to_numeric(df["lucro"], errors="coerce").fillna(0)

# =====================
# CÁLCULOS
# =====================
df["vendidos"] = (df["estoque_inicial"] - df["estoque_atual"]).clip(lower=0)
df["renda_atual"] = df["vendidos"] * df["preco"]
df["lucro_atual"] = df["vendidos"] * df["lucro"]

# =====================
# GERENCIAMENTO
# =====================

st.sidebar.title("⚙️ Gerenciamento")

acao = st.sidebar.radio(
    "Escolha uma ação:",
    ["📦 Visualizar Produtos", "➕ Inserir Produto", "✏️ Alterar Produto", "💰 Registrar Venda", "🗑️ Excluir Produto"]
)

if st.sidebar.button("❌ Encerrar aplicação"):
    st.warning("Aplicação encerrada.")
    st.stop()

if acao == "➕ Inserir Produto":
    st.subheader("➕ Inserir novo produto")

    with st.form("form_inserir"):
        produto = st.text_input("Produto")
        foto = st.text_input("Caminho da imagem (ex: imagens/001.jpg)")
        estoque_inicial = st.number_input("Estoque inicial", min_value=0, step=1)
        estoque_atual = st.number_input("Estoque atual", min_value=0, step=1)
        preco = st.number_input("Preço final", min_value=0.0, step=0.01)
        lucro = st.number_input("Lucro líquido (unidade)", min_value=0.0, step=0.01)
        codigo = st.text_input("Código do produto")

        submit = st.form_submit_button("Salvar produto")

    if submit:
        novo = {
            "produto": produto,
            "foto": foto,
            "estoque_inicial": estoque_inicial,
            "estoque_atual": estoque_atual,
            "preco": preco,
            "lucro": lucro,
            "codigo": codigo
        }

        valido, msg = validar_produto(novo)

        if not valido:
            st.error(f"❌ {msg}")
        else:
            conn = get_conn()
            cursor = conn.cursor()

            cursor.execute("""
            INSERT INTO public.produtos
            (produto, foto, estoque_inicial, estoque_atual, preco, lucro, codigo)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
            """, (
                produto,
                foto,
                estoque_inicial,
                estoque_atual,
                preco,
                lucro,
                codigo
            ))


if acao == "✏️ Alterar Produto":
    st.subheader("✏️ Alterar produto")

    produto_sel = st.selectbox("Selecione o produto", df["produto"])

    row = df[df["produto"] == produto_sel].iloc[0]
    produto_id = int(row["id"])

    with st.form("form_editar"):
        produto = st.text_input("Produto", row["produto"])
        estoque_inicial = st.number_input("Estoque inicial", value=int(row["estoque_inicial"]))
        estoque_atual = st.number_input("Estoque atual", value=int(row["estoque_atual"]))
        preco = st.number_input("Preço final", value=float(row["preco"]))
        lucro = st.number_input("Lucro líquido (unidade)", value=float(row["lucro"]))
        codigo = st.text_input("Código do produto", row["codigo"])

        submit = st.form_submit_button("Atualizar")

    if submit:
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("""
        UPDATE public.produtos
        SET produto=%s, codigo=%s, preco=%s, lucro=%s,
            estoque_inicial=%s, estoque_atual=%s
        WHERE id=%s
        """, (
            produto,
            codigo,
            preco,
            lucro,
            estoque_inicial,
            estoque_atual,
            produto_id
        ))


        conn.commit()
        st.success("✏️ Produto atualizado com sucesso!")
        st.rerun()

if acao == "💰 Registrar Venda":
    st.subheader("💰 Registrar Venda")

    data_venda = st.date_input(
        "📅 Data da venda",
        value=datetime.today()
    )
    
    produto_sel = st.selectbox(
        "Produto",
        df["produto"].tolist()
    )

    row = df[df["produto"] == produto_sel].iloc[0]

    estoque_disp = int(row["estoque_atual"])

    quantidade = st.number_input(
        "Quantidade vendida",
        min_value=1,
        max_value=estoque_disp,
        step=1
    )

    if st.button("✅ Confirmar venda"):
        registrar_venda(
            produto_id=int(row["id"]),
            quantidade=quantidade,
            preco=float(row["preco"]),
            lucro=float(row["lucro"]),
            data_venda=datetime.combine(data_venda, datetime.min.time())
        )

        st.success("✅ Venda registrada com sucesso!")
        st.rerun()


if acao == "🗑️ Excluir Produto":
    st.subheader("🗑️ Excluir produto")

    produto_sel = st.selectbox(
        "Selecione o produto",
        df["produto"].unique()
    )

    st.warning("⚠️ Esta ação não pode ser desfeita.")

    confirmar = st.checkbox("Confirmo que desejo excluir este produto")

    if confirmar:
        if st.button("🗑️ Excluir definitivamente"):
            conn = get_conn()
            cursor = conn.cursor()

            cursor.execute(
                "DELETE FROM public.produtos WHERE produto=%s",
                (produto_sel,)
            )

            conn.commit()
            st.success("🗑️ Produto excluído com sucesso!")
            st.rerun()

if acao == "📦 Visualizar Produtos":
    # aqui fica TODO o painel que você já construiu
    pass             

# =====================
# KPIs TOPO
# =====================
st.title("📦 Painel de Produtos")

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.metric("💰 Renda Total", f"R$ {df['renda_atual'].sum():,.2f}")

with kpi2:
    st.metric("📈 Lucro Total", f"R$ {df['lucro_atual'].sum():,.2f}")

with kpi3:
    st.metric("🛒 Produtos Vendidos", int(df["vendidos"].sum()))

with kpi4:
    st.metric("📦 Estoque Total", int(df["estoque_atual"].sum()))
    
st.markdown("### 🧾 Relatórios")

if st.button("📄 Exportar relatório em PDF"):
    pdf_path = gerar_pdf(df)
    with open(pdf_path, "rb") as f:
        st.download_button(
            label="⬇️ Baixar PDF",
            data=f,
            file_name="relatorio_modarte.pdf",
            mime="application/pdf"
        )

st.markdown("---")

# =====================
# FILTRO POR PRODUTO
# =====================
produtos = ["Todos"] + sorted(df["produto"].dropna().unique().tolist())
produto_selecionado = st.selectbox("🔎 Filtrar produto:", produtos)

if produto_selecionado != "Todos":
    df = df[df["produto"] == produto_selecionado]

# =====================
# ALERTA ESTOQUE BAIXO
# =====================
estoque_baixo = df[df["estoque_atual"] <= ESTOQUE_MINIMO]

if not estoque_baixo.empty:
    st.error("🚨 Produtos com estoque baixo!")
    st.dataframe(
        estoque_baixo[["produto", "estoque_atual"]],
        use_container_width=True
    )

st.markdown("---")

# =====================
# DASHBOARD DE VENDAS
# =====================
st.subheader("📊 Dashboard - Histórico de Vendas")

conn = get_conn()

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
ORDER BY v.data_venda DESC
""", conn)

if not df_vendas.empty:
    df_vendas["data_venda"] = pd.to_datetime(df_vendas["data_venda"])

    produto_sel = st.selectbox(
        "Produto",
        df_vendas["produto"].unique()
    )

    df_prod = df_vendas[df_vendas["produto"] == produto_sel]

    st.line_chart(
        df_prod.groupby(df_prod["data_venda"].dt.date)["quantidade"].sum()
    )

    st.dataframe(df_prod, use_container_width=True)

    st.markdown("### 🗑️ Excluir Venda")

    produto_excluir = st.selectbox(
        "📦 Selecione o produto",
        df_vendas["produto"].unique()
    )

    df_vendas_produto = df_vendas[
        df_vendas["produto"] == produto_excluir
    ].copy()

    df_vendas_produto["label"] = df_vendas_produto.apply(
        lambda x: f"{x['data_venda'].date()} | {x['quantidade']} un | R$ {(x['quantidade'] * x['preco_unit']):,.2f}",
        axis=1
    )

    venda_sel = st.selectbox(
        "🧾 Selecione a venda",
        df_vendas_produto["label"]
    )

    if st.button("❌ Excluir venda selecionada"):
        venda = df_vendas_produto[
            df_vendas_produto["label"] == venda_sel
        ].iloc[0]
    
        conn = get_conn()
        cursor = conn.cursor()
    
        # Devolver estoque
        cursor.execute("""
            UPDATE public.produtos
            SET estoque_atual = estoque_atual + %s
            WHERE id = %s
        """, (
            int(venda["quantidade"]),
            int(venda["produto_id"])
        ))
    
        # Excluir venda
        cursor.execute("""
            DELETE FROM public.vendas_modarte
            WHERE id = %s
        """, (int(venda["id"]),))
    
        conn.commit()
    
        st.success("🗑️ Venda excluída e estoque ajustado com sucesso!")
        st.rerun()
else:
    st.info("Nenhuma venda registrada ainda.")

# =====================
# LISTAGEM DE PRODUTOS
# =====================
st.subheader("🧾 Lista de Produtos")

for _, row in df.iterrows():
    #st.markdown("—")
    col1, col2 = st.columns([1, 3])

    with col1:
        img_path = BASE_DIR / str(row["foto"])
        img_logo = BASE_DIR / "Logo_Modarte.jpg"
        if img_path.exists():
            st.image(str(img_path), use_container_width=True)
        else:
            st.image(str(img_logo), use_container_width=True)

    with col2:
        st.subheader(row["produto"])
        st.write(f"📦 **Estoque Inicial:** {int(row['estoque_inicial'])}")
        st.write(f"📦 **Estoque Atual:** {int(row['estoque_atual'])}")
        st.write(f"🛒 **Vendidos:** {int(row['vendidos'])}")
        st.write(f"💰 **Preço:** R$ {row['preco']:,.2f}")
        st.write(f"📈 **Lucro unidade:** R$ {row['lucro']:,.2f}")
        st.write(f"💵 **Renda Atual:** R$ {row['renda_atual']:,.2f}")
        st.write(f"🏆 **Lucro Atual:** R$ {row['lucro_atual']:,.2f}")
    

    st.markdown("---")
