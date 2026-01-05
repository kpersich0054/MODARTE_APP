import streamlit as st
import pandas as pd
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from datetime import datetime
import tempfile
import os
import signal

def salvar_planilha(df, caminho):
    df.to_excel(caminho, index=False)

def validar_produto(dados):
    campos_texto = ["PRODUTO", "FOTO DO PRODUTO", "CODIGO N"]
    campos_num = ["ESTOQUE INICIAL", "ESTOQUE ATUAL", "PREÇO FINAL", "LUCRO LIQUIDO"]

    for campo in campos_texto:
        if not dados[campo] or str(dados[campo]).strip() == "":
            return False, f"Campo '{campo}' não pode ficar vazio."

    for campo in campos_num:
        if dados[campo] <= 0:
            return False, f"Campo '{campo}' deve ser maior que zero."

    if dados["ESTOQUE ATUAL"] > dados["ESTOQUE INICIAL"]:
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
    c.drawString(2 * cm, y, f"Renda Total: R$ {df['RENDA ATUAL'].sum():,.2f}")
    y -= 0.6 * cm
    c.drawString(2 * cm, y, f"Lucro Total: R$ {df['LUCRO ATUAL'].sum():,.2f}")
    y -= 1 * cm

    # TABELA
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2 * cm, y, "Produtos:")
    y -= 0.5 * cm

    c.setFont("Helvetica", 9)
    for _, row in df.iterrows():
        texto = (
            f"{row['PRODUTO']} | "
            f"Vendidos: {int(row['VENDIDOS'])} | "
            f"Renda: R$ {row['RENDA ATUAL']:,.2f}"
        )
        c.drawString(2 * cm, y, texto)
        y -= 0.45 * cm

        if y < 2 * cm:
            c.showPage()
            y = altura - 2 * cm
            c.setFont("Helvetica", 9)

    c.save()
    return temp_file.name

# =====================
# CONFIGURAÇÕES
# =====================
BASE_DIR = Path(__file__).parent
PLANILHA = BASE_DIR / "PLANILHA_MODARTE.xlsx"
ESTOQUE_MINIMO = 5

st.set_page_config(
    page_title="MODARTE",
    layout="wide",
    initial_sidebar_state="expanded",
    page_icon=Logo_Modarte.jpg
)

# =====================
# CARREGAR DADOS
# =====================
df = pd.read_excel(PLANILHA)

# Garantir tipos corretos
df["ESTOQUE INICIAL"] = pd.to_numeric(df["ESTOQUE INICIAL"], errors="coerce").fillna(0)
df["ESTOQUE ATUAL"] = pd.to_numeric(df["ESTOQUE ATUAL"], errors="coerce").fillna(0)
df["PREÇO FINAL"] = pd.to_numeric(df["PREÇO FINAL"], errors="coerce").fillna(0)
df["LUCRO LIQUIDO"] = pd.to_numeric(df["LUCRO LIQUIDO"], errors="coerce").fillna(0)

# =====================
# CÁLCULOS
# =====================
df["VENDIDOS"] = (df["ESTOQUE INICIAL"] - df["ESTOQUE ATUAL"]).clip(lower=0)
df["RENDA ATUAL"] = df["VENDIDOS"] * df["PREÇO FINAL"]
df["LUCRO ATUAL"] = df["VENDIDOS"] * df["LUCRO LIQUIDO"]

# =====================
# GERENCIAMENTO
# =====================

st.sidebar.title("⚙️ Gerenciamento")

acao = st.sidebar.radio(
    "Escolha uma ação:",
    ["📦 Visualizar Produtos", "➕ Inserir Produto", "✏️ Alterar Produto", "🗑️ Excluir Produto"]
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
            "PRODUTO": produto,
            "FOTO DO PRODUTO": foto,
            "ESTOQUE INICIAL": estoque_inicial,
            "ESTOQUE ATUAL": estoque_atual,
            "PREÇO FINAL": preco,
            "LUCRO LIQUIDO": lucro,
            "CODIGO NF": codigo
        }

        valido, msg = validar_produto(novo)

        if not valido:
            st.error(f"❌ {msg}")
        else:
            df = pd.concat([df, pd.DataFrame([novo])], ignore_index=True)
            salvar_planilha(df, PLANILHA)
            st.success("✅ Produto inserido com sucesso!")
            st.rerun()

if acao == "✏️ Alterar Produto":
    st.subheader("✏️ Alterar produto")

    produto_sel = st.selectbox("Selecione o produto", df["PRODUTO"])

    idx = df[df["PRODUTO"] == produto_sel].index[0]
    row = df.loc[idx]

    with st.form("form_editar"):
        produto = st.text_input("Produto", row["PRODUTO"])
        estoque_inicial = st.number_input("Estoque inicial", value=int(row["ESTOQUE INICIAL"]))
        estoque_atual = st.number_input("Estoque atual", value=int(row["ESTOQUE ATUAL"]))
        preco = st.number_input("Preço final", value=float(row["PREÇO FINAL"]))
        lucro = st.number_input("Lucro líquido (unidade)", value=float(row["LUCRO LIQUIDO"]))
        codigo = st.text_input("Código do produto", row["CODIGO NF"])

        submit = st.form_submit_button("Atualizar")

    if submit:
        df.at[idx, "PRODUTO"] = produto
        df.at[idx, "ESTOQUE INICIAL"] = estoque_inicial
        df.at[idx, "ESTOQUE ATUAL"] = estoque_atual
        df.at[idx, "PREÇO FINAL"] = preco
        df.at[idx, "LUCRO LIQUIDO"] = lucro
        df.at[idx, "CODIGO NF"] = codigo

        salvar_planilha(df, PLANILHA)
        st.success("✏️ Produto atualizado com sucesso!")
        st.rerun()

if acao == "🗑️ Excluir Produto":
    st.subheader("🗑️ Excluir produto")

    produto_sel = st.selectbox(
        "Selecione o produto",
        df["PRODUTO"].unique()
    )

    st.warning("⚠️ Esta ação não pode ser desfeita.")

    confirmar = st.checkbox("Confirmo que desejo excluir este produto")

    if confirmar:
        if st.button("🗑️ Excluir definitivamente"):
            df = df[df["PRODUTO"] != produto_sel]
            salvar_planilha(df, PLANILHA)
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
    st.metric("💰 Renda Total", f"R$ {df['RENDA ATUAL'].sum():,.2f}")

with kpi2:
    st.metric("📈 Lucro Total", f"R$ {df['LUCRO ATUAL'].sum():,.2f}")

with kpi3:
    st.metric("🛒 Produtos Vendidos", int(df["VENDIDOS"].sum()))

with kpi4:
    st.metric("📦 Estoque Total", int(df["ESTOQUE ATUAL"].sum()))
    
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
produtos = ["Todos"] + sorted(df["PRODUTO"].dropna().unique().tolist())
produto_selecionado = st.selectbox("🔎 Filtrar produto:", produtos)

if produto_selecionado != "Todos":
    df = df[df["PRODUTO"] == produto_selecionado]

# =====================
# ALERTA ESTOQUE BAIXO
# =====================
estoque_baixo = df[df["ESTOQUE ATUAL"] <= ESTOQUE_MINIMO]

if not estoque_baixo.empty:
    st.error("🚨 Produtos com estoque baixo!")
    st.dataframe(
        estoque_baixo[["PRODUTO", "ESTOQUE ATUAL"]],
        use_container_width=True
    )

st.markdown("---")

# =====================
# DASHBOARD DE VENDAS
# =====================
st.subheader("📊 Dashboard de Vendas")

col_g1, col_g2 = st.columns(2)

with col_g1:
    st.bar_chart(
        df.set_index("PRODUTO")["VENDIDOS"],
        use_container_width=True
    )

with col_g2:
    st.bar_chart(
        df.set_index("PRODUTO")["RENDA ATUAL"],
        use_container_width=True
    )

st.markdown("---")

# =====================
# LISTAGEM DE PRODUTOS
# =====================
st.subheader("🧾 Lista de Produtos")

for _, row in df.iterrows():
    #st.markdown("—")
    col1, col2 = st.columns([1, 3])

    with col1:
        img_path = BASE_DIR / str(row["FOTO DO PRODUTO"])
        img_logo = BASE_DIR / "Logo_Modarte.jpg"
        if img_path.exists():
            st.image(str(img_path), use_container_width=True)
        else:
            st.image(str(img_logo), use_container_width=True)

    with col2:
        st.subheader(row["PRODUTO"])
        st.write(f"📦 **Estoque Inicial:** {int(row['ESTOQUE INICIAL'])}")
        st.write(f"📦 **Estoque Atual:** {int(row['ESTOQUE ATUAL'])}")
        st.write(f"🛒 **Vendidos:** {int(row['VENDIDOS'])}")
        st.write(f"💰 **Preço:** R$ {row['PREÇO FINAL']:,.2f}")
        st.write(f"📈 **Lucro unidade:** R$ {row['LUCRO LIQUIDO']:,.2f}")
        st.write(f"💵 **Renda Atual:** R$ {row['RENDA ATUAL']:,.2f}")
        st.write(f"🏆 **Lucro Atual:** R$ {row['LUCRO ATUAL']:,.2f}")
    
    st.markdown("---")
