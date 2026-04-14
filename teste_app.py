import streamlit as st
import pandas as pd
import psycopg2
from pathlib import Path
from datetime import datetime, timedelta

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

# =====================
# NORMALIZAÇÃO (CORREÇÃO CRÍTICA)
# =====================
cols_num = ["estoque_inicial", "estoque_atual", "preco", "lucro"]

for col in cols_num:
    df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

df_vendas["quantidade"] = pd.to_numeric(df_vendas["quantidade"], errors="coerce").fillna(0)
df_vendas["preco_unit"] = pd.to_numeric(df_vendas["preco_unit"], errors="coerce").fillna(0)
df_vendas["lucro_unit"] = pd.to_numeric(df_vendas["lucro_unit"], errors="coerce").fillna(0)

df_vendas["data_venda"] = pd.to_datetime(df_vendas["data_venda"], errors="coerce")

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
    data_inicio = hoje.replace(hour=0, minute=0, second=0)
    data_fim = hoje.replace(hour=23, minute=59, second=59)

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

    data_inicio = datetime.combine(data_inicio, datetime.min.time())
    data_fim = datetime.combine(data_fim, datetime.max.time())

# =====================
# FILTRAR VENDAS
# =====================
df_filtrado = df_vendas[
    (df_vendas["data_venda"] >= data_inicio) &
    (df_vendas["data_venda"] <= data_fim)
]

# =====================
# KPIs
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
    f"Período: {data_inicio.strftime('%d/%m/%Y')} até {data_fim.strftime('%d/%m/%Y')}"
)

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
# GRÁFICO
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
# LISTA DE PRODUTOS (CORRIGIDA)
# =====================
st.subheader("🧾 Lista de Produtos")

for _, row in df.iterrows():
    col1, col2 = st.columns([1, 3])

    with col2:
        st.subheader(row["produto"])

        estoque = int(row["estoque_atual"])
        preco = float(row["preco"])
        lucro = float(row["lucro"])

        st.write(f"📦 Estoque Atual: {estoque}")
        st.write(f"💰 Preço: R$ {preco:,.2f}")
        st.write(f"📈 Lucro unidade: R$ {lucro:,.2f}")

    st.markdown("---")
