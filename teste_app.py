import streamlit as st
import pandas as pd
import psycopg2
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from datetime import datetime, timedelta
import tempfile

# =====================
# CONFIG
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

st.set_page_config(
    page_title="MODARTE",
    layout="wide"
)

# =====================
# CARREGAR DADOS
# =====================
conn = get_conn()

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

df_vendas["data_venda"] = pd.to_datetime(df_vendas["data_venda"])

# =====================
# FILTRO DE PERÍODO
# =====================
st.markdown("### 📅 Filtro de Período")

col1, col2, col3 = st.columns(3)

with col1:
    tipo_periodo = st.selectbox(
        "Tipo de período",
        ["Hoje", "Últimos 7 dias", "Últimos 30 dias", "Personalizado"]
    )

hoje = datetime.today()

if tipo_periodo == "Hoje":
    data_inicio = hoje
    data_fim = hoje

elif tipo_periodo == "Últimos 7 dias":
    data_inicio = hoje - timedelta(days=7)
    data_fim = hoje

elif tipo_periodo == "Últimos 30 dias":
    data_inicio = hoje - timedelta(days=30)
    data_fim = hoje

else:
    with col2:
        data_inicio = st.date_input("Data início", value=hoje)
    with col3:
        data_fim = st.date_input("Data fim", value=hoje)

# =====================
# FILTRAR VENDAS
# =====================
df_filtrado = df_vendas[
    (df_vendas["data_venda"] >= pd.to_datetime(data_inicio)) &
    (df_vendas["data_venda"] <= pd.to_datetime(data_fim))
]

# =====================
# KPIs (BASEADOS EM VENDAS)
# =====================
renda_total = (df_filtrado["quantidade"] * df_filtrado["preco_unit"]).sum()
lucro_total = (df_filtrado["quantidade"] * df_filtrado["lucro_unit"]).sum()
produtos_vendidos = df_filtrado["quantidade"].sum()
estoque_total = df["estoque_atual"].sum()

# =====================
# VISUAL KPIs
# =====================
st.title("📦 Painel de Produtos")

st.caption(
    f"Período: {pd.to_datetime(data_inicio).strftime('%d/%m/%Y')} "
    f"até {pd.to_datetime(data_fim).strftime('%d/%m/%Y')}"
)

# CSS leve pra melhorar visual
st.markdown("""
<style>
[data-testid="stMetric"] {
    background-color: #111;
    padding: 15px;
    border-radius: 10px;
    text-align: center;
}
</style>
""", unsafe_allow_html=True)

kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.metric("💰 Renda Total", f"R$ {renda_total:,.2f}")

with kpi2:
    st.metric("📈 Lucro Total", f"R$ {lucro_total:,.2f}")

with kpi3:
    st.metric("🛒 Produtos Vendidos", int(produtos_vendidos))

with kpi4:
    st.metric("📦 Estoque Total", int(estoque_total))

st.markdown("---")

# =====================
# GRÁFICO DE VENDAS
# =====================
st.subheader("📊 Vendas no Período")

if not df_filtrado.empty:
    vendas_por_dia = df_filtrado.groupby(
        df_filtrado["data_venda"].dt.date
    )["quantidade"].sum()

    st.line_chart(vendas_por_dia)

    st.dataframe(df_filtrado, use_container_width=True)

else:
    st.info("Nenhuma venda no período selecionado.")

st.markdown("---")

# =====================
# LISTA DE PRODUTOS
# =====================
st.subheader("🧾 Lista de Produtos")

for _, row in df.iterrows():
    col1, col2 = st.columns([1, 3])

    with col2:
        st.subheader(row["produto"])
        st.write(f"📦 Estoque Atual: {int(row['estoque_atual'])}")
        st.write(f"💰 Preço: R$ {row['preco']:,.2f}")
        st.write(f"📈 Lucro unidade: R$ {row['lucro']:,.2f}")

    st.markdown("---")
