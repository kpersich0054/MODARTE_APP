import streamlit as st
import pandas as pd
import psycopg2
from pathlib import Path
from datetime import datetime, timedelta
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
import io

def estornar_venda(venda_id):
    conn = get_conn()
    try:
        cursor = conn.cursor()

        # 🔥 pega dados da venda (e status)
        cursor.execute("""
            SELECT produto_id, quantidade, status
            FROM public.vendas_modarte
            WHERE id = %s
        """, (venda_id,))

        venda = cursor.fetchone()

        if not venda:
            raise Exception("Venda não encontrada")

        produto_id, quantidade, status = venda

        # 🔥 evita estorno duplicado
        if status == "estornado":
            raise Exception("Essa venda já foi estornada")

        # 🔥 devolve estoque
        cursor.execute("""
            UPDATE public.produtos
            SET estoque_atual = estoque_atual + %s
            WHERE id = %s
        """, (quantidade, produto_id))

        # 🔥 marca como estornada (AO INVÉS DE DELETAR)
        cursor.execute("""
            UPDATE public.vendas_modarte
            SET status = 'estornado'
            WHERE id = %s
        """, (venda_id,))

        conn.commit()

    except Exception as e:
        conn.rollback()
        raise e
    finally:
        conn.close()
        
def calcular_dre(df_vendas):
    if df_vendas.empty:
        return None

    df = df_vendas[df_vendas["status"] == "pago"].copy()

    # =====================
    # BASE
    # =====================
    df["receita"] = df["quantidade"] * df["preco_unit"]
    df["custo"] = df["quantidade"] * (df["preco_unit"] - df["lucro_unit"])
    df["lucro_bruto"] = df["quantidade"] * df["lucro_unit"]

    # =====================
    # TAXAS (simulação)
    # =====================
    def taxa(row):
        if row["forma_pagamento"] == "Cartão (Maquininha)":
            return row["receita"] * 0.05  # 5%
        elif row["forma_pagamento"] == "Pix":
            return row["receita"] * 0.01  # 1%
        else:
            return 0

    df["taxa"] = df.apply(taxa, axis=1)

    # =====================
    # AGREGADOS
    # =====================
    receita_bruta = df["receita"].sum()
    custo_total = df["custo"].sum()
    lucro_bruto = df["lucro_bruto"].sum()
    taxas = df["taxa"].sum()

    lucro_operacional = lucro_bruto - taxas

    return {
        "receita_bruta": receita_bruta,
        "custo_total": custo_total,
        "lucro_bruto": lucro_bruto,
        "taxas": taxas,
        "lucro_operacional": lucro_operacional
    }
    
def gerar_pdf(df_vendas, df_produtos, inicio, fim):
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()

    elements = []

    # Título
    elements.append(Paragraph(f"Relatório de Vendas", styles["Title"]))
    elements.append(Spacer(1, 10))

    elements.append(Paragraph(
        f"Período: {inicio.strftime('%d/%m/%Y')} até {fim.strftime('%d/%m/%Y')}",
        styles["Normal"]
    ))

    elements.append(Spacer(1, 20))

    # =====================
    # RESUMO POR PAGAMENTO
    # =====================
    elements.append(Paragraph("Resumo por Forma de Pagamento", styles["Heading2"]))

    resumo_pag = df_vendas[df_vendas["status"] == "pago"].copy()
    resumo_pag["total"] = resumo_pag["quantidade"] * resumo_pag["preco_unit"]

    resumo = resumo_pag.groupby("forma_pagamento")["total"].sum()

    for forma, valor in resumo.items():
        elements.append(Paragraph(f"{forma}: R$ {valor:,.2f}", styles["Normal"]))

    elements.append(Spacer(1, 20))

    # =====================
    # VENDAS DETALHADAS
    # =====================
    elements.append(Paragraph("Vendas", styles["Heading2"]))

    for _, row in df_vendas.iterrows():
        texto = f"{row['produto']} | QTD: {int(row['quantidade'])} | R$ {row['preco_unit']:,.2f} | {row['forma_pagamento']}"
        elements.append(Paragraph(texto, styles["Normal"]))

    elements.append(Spacer(1, 20))

    # =====================
    # DRE Vendas
    # =====================
    
    dre = calcular_dre(df_vendas)

    elements.append(Paragraph("DRE - Resultado", styles["Heading2"]))

    elements.append(Paragraph(f"Receita Bruta: R$ {dre['receita_bruta']:,.2f}", styles["Normal"]))
    elements.append(Paragraph(f"Custo (CPV): R$ {dre['custo_total']:,.2f}", styles["Normal"]))
    elements.append(Paragraph(f"Lucro Bruto: R$ {dre['lucro_bruto']:,.2f}", styles["Normal"]))
    elements.append(Paragraph(f"Taxas: R$ {dre['taxas']:,.2f}", styles["Normal"]))
    elements.append(Paragraph(f"Lucro Operacional: R$ {dre['lucro_operacional']:,.2f}", styles["Normal"]))
    
    # =====================
    # ESTOQUE
    # =====================
    elements.append(Paragraph("Estoque Atual", styles["Heading2"]))

    for _, row in df_produtos.iterrows():
        texto = f"{row['produto']} - Estoque: {int(row['estoque_atual'])}"
        elements.append(Paragraph(texto, styles["Normal"]))

    doc.build(elements)

    buffer.seek(0)
    return buffer

# =====================
# CONFIG
# =====================
BASE_DIR = Path(__file__).parent
PASTA_IMAGENS = BASE_DIR

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

# =====================
# QUERY SEGURA
# =====================
def query_df(sql):
    conn = get_conn()
    try:
        return pd.read_sql(sql, conn)
    finally:
        conn.close()

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

def registrar_venda(produto_id, quantidade, preco, lucro, data_venda, forma_pagamento):
    conn = get_conn()
    try:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO public.vendas_modarte
            (produto_id, quantidade, data_venda, preco_unit, lucro_unit, forma_pagamento, status)
            VALUES (%s,%s,%s,%s,%s,%s,%s)
        """, (produto_id, quantidade, data_venda, preco, lucro, "pago"))

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
# DADOS (SEGURO)
# =====================
df = query_df("SELECT * FROM public.produtos")

df_vendas = query_df("""
SELECT
    v.id,
    v.produto_id,
    p.produto,
    v.data_venda,
    v.quantidade,
    v.preco_unit,
    v.lucro_unit,
    v.forma_pagamento,
    v.status
FROM public.vendas_modarte v
JOIN public.produtos p ON p.id = v.produto_id
""")

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
            conn = get_conn()
            try:
                cursor = conn.cursor()

                cursor.execute("""
                    INSERT INTO public.produtos
                    (produto, estoque_inicial, estoque_atual, preco, lucro)
                    VALUES (%s,%s,%s,%s,%s)
                    RETURNING id
                """, (produto, estoque_inicial, estoque_atual, preco, lucro))

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

            except Exception as e:
                conn.rollback()
                st.error(f"Erro ao inserir produto: {e}")
            finally:
                conn.close()

# =====================
# ALTERAR PRODUTO
# =====================
elif acao == "✏️ Alterar Produto":
    st.subheader("✏️ Alterar produto")

    df["label"] = df["id"].astype(str) + " - " + df["produto"]

    produto_sel = st.selectbox("Selecione o produto", df["label"])

    produto_id = int(produto_sel.split(" - ")[0])
    row = df[df["id"] == produto_id].iloc[0]

    with st.form("form_editar"):
        produto = st.text_input("Produto", row["produto"])
        estoque_inicial = st.number_input("Estoque inicial", value=int(row["estoque_inicial"]))
        estoque_atual = st.number_input("Estoque atual", value=int(row["estoque_atual"]))
        preco = st.number_input("Preço", value=float(row["preco"]))
        lucro = st.number_input("Lucro", value=float(row["lucro"]))

        submit = st.form_submit_button("Atualizar")

    if submit:
        conn = get_conn()
        try:
            cursor = conn.cursor()

            # 🔥 SANITIZAÇÃO
            produto = produto if produto else row["produto"]
            estoque_inicial = int(estoque_inicial)
            estoque_atual = int(estoque_atual)
            preco = float(preco)
            lucro = float(lucro)

            # 🔥 NOVO: GERAR CODIGO E FOTO
            codigo = gerar_codigo_produto(produto, produto_id)
            foto_path = str(BASE_DIR / f"{codigo}.jpg")

            cursor.execute("""
                UPDATE public.produtos
                SET produto=%s,
                    preco=%s,
                    lucro=%s,
                    estoque_inicial=%s,
                    estoque_atual=%s,
                    codigo=%s,
                    foto=%s
                WHERE id=%s
            """, (
                produto,
                preco,
                lucro,
                estoque_inicial,
                estoque_atual,
                codigo,
                foto_path,
                produto_id
            ))

            conn.commit()

            st.success(f"Produto atualizado! Novo código: {codigo}")
            st.rerun()

        except Exception as e:
            conn.rollback()
            st.error(f"Erro: {e}")
        finally:
            conn.close()

# =====================
# REGISTRAR VENDA
# =====================
elif acao == "💰 Registrar Venda":
    st.subheader("💰 Registrar Venda")

    data_venda = st.date_input("Data da venda", value=datetime.today())

    df_disponivel = df[df["estoque_atual"] > 0].copy()

    if df_disponivel.empty:
        st.warning("⚠️ Nenhum produto com estoque disponível.")
        st.stop()

    df_disponivel["label"] = df_disponivel.apply(
        lambda x: f"{x['produto']} (Estoque: {int(x['estoque_atual'])})",
        axis=1
    )

    produto_sel = st.selectbox("Produto", df_disponivel["label"])

    row = df_disponivel[df_disponivel["label"] == produto_sel].iloc[0]

    estoque_disp = int(row["estoque_atual"])

    quantidade = st.number_input("Quantidade", min_value=1, max_value=estoque_disp, step=1)

    # 💰 CALCULO
    preco_base = float(row["preco"])
    lucro_base = float(row["lucro"])

    # 🔥 REGRA ATACADO
    if quantidade >= 3:
        desconto = 5
        preco_final = preco_base - desconto
        lucro_final = lucro_base - desconto
        st.success(f"💸 Desconto atacado aplicado: -R$ {desconto} por peça")
    else:
        preco_final = preco_base
        lucro_final = lucro_base

    valor_total = quantidade * preco_final

    st.info(f"💵 Valor total: R$ {valor_total:,.2f}")

    # 💳 FORMA DE PAGAMENTO
    forma_pagamento = st.selectbox(
        "Forma de pagamento",
        ["Pix", "Cartão (Maquininha)", "Dinheiro"]
    )

    pagamento_confirmado = False

    # =====================
    # PIX (FASE 1 SIMULADO)
    # =====================
    if forma_pagamento == "Pix":
        st.warning("⚠️ Pix ainda não integrado (fase futura)")
        
        pagamento_confirmado = st.checkbox("Confirmar pagamento via Pix?")

    # =====================
    # CARTÃO (MANUAL)
    # =====================
    elif forma_pagamento == "Cartão (Maquininha)":
        st.info("Passe o cartão na maquininha")

        pagamento_confirmado = st.checkbox("Pagamento aprovado na maquininha?")

    # =====================
    # DINHEIRO
    # =====================
    elif forma_pagamento == "Dinheiro":
        pagamento_confirmado = st.checkbox("Pagamento recebido?")

    # =====================
    # CONFIRMA VENDA
    # =====================
    if st.button("✅ Finalizar venda"):
        if not pagamento_confirmado:
            st.error("❌ Confirme o pagamento antes de continuar.")
            st.stop()

        registrar_venda(
            produto_id=int(row["id"]),
            quantidade=quantidade,
            preco=preco_final,
            lucro=lucro_final,
            data_venda=datetime.combine(data_venda, datetime.min.time()),
            forma_pagamento=forma_pagamento
        )

        st.success("✅ Venda registrada com sucesso!")
        st.rerun()

        st.markdown("---")
        
        st.subheader("↩️ Estornar Venda")

        df_vendas_view = query_df("""
        SELECT 
            v.id, 
            p.produto, 
            v.quantidade, 
            v.data_venda,
            v.status
        FROM public.vendas_modarte v
        JOIN public.produtos p ON p.id = v.produto_id
        ORDER BY v.data_venda DESC
        """)

        # 🔥 opcional: mostrar TODAS ou só ativas
        mostrar_estornadas = st.checkbox("Mostrar vendas estornadas", value=False)

        if not mostrar_estornadas:
            df_vendas_view = df_vendas_view[df_vendas_view["status"] == "pago"]

        if not df_vendas_view.empty:

            # 🔥 label mais completo
            df_vendas_view["label"] = df_vendas_view.apply(
                lambda x: f"{x['id']} - {x['produto']} | QTD: {x['quantidade']} | {x['status']}",
                axis=1
            )

            venda_sel = st.selectbox("Selecione a venda", df_vendas_view["label"])

            venda_id = int(venda_sel.split(" - ")[0])

            # 🔥 pega status da venda selecionada
            venda_row = df_vendas_view[df_vendas_view["id"] == venda_id].iloc[0]

            if venda_row["status"] == "estornado":
                st.warning("⚠️ Essa venda já foi estornada")
            else:
                if st.button("❌ Estornar venda"):
                    try:
                        estornar_venda(venda_id)
                        st.success("✅ Venda estornada com sucesso!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Erro ao estornar: {e}")
        else:
            st.info("Nenhuma venda encontrada.")
# =====================
# EXCLUIR PRODUTO
# =====================
elif acao == "🗑️ Excluir Produto":
    st.subheader("🗑️ Excluir produto")

    produto_sel = st.selectbox("Produto", df["produto"])

    if st.checkbox("Confirmar exclusão"):
        if st.button("Excluir"):
            conn = get_conn()
            try:
                cursor = conn.cursor()

                cursor.execute(
                    "DELETE FROM public.produtos WHERE produto=%s",
                    (produto_sel,)
                )

                conn.commit()
                st.success("Produto excluído!")
                st.rerun()

            except Exception as e:
                conn.rollback()
                st.error(f"Erro: {e}")
            finally:
                conn.close()

# =====================
# DASHBOARD
# =====================
if acao == "📦 Visualizar Produtos":

    st.markdown("### 📅 Filtro de Período")

    tipo = st.selectbox("Período", ["Hoje", "7 dias", "30 dias", "Personalizado"])

    hoje = datetime.today()

    if tipo == "Hoje":
        inicio = hoje.replace(hour=0, minute=0, second=0, microsecond=0)
        fim = hoje.replace(hour=23, minute=59, second=59, microsecond=999999)
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

    dre = calcular_dre(df_f)

    if dre:
        st.markdown("## 📊 DRE (Resultado do Período)")

        c1, c2, c3 = st.columns(3)

        c1.metric("💰 Receita Bruta", f"R$ {dre['receita_bruta']:,.2f}")
        c2.metric("📉 Custo (CPV)", f"R$ {dre['custo_total']:,.2f}")
        c3.metric("📈 Lucro Bruto", f"R$ {dre['lucro_bruto']:,.2f}")

        c4, c5 = st.columns(2)

        c4.metric("💳 Taxas", f"R$ {dre['taxas']:,.2f}")
        c5.metric("🏆 Lucro Real", f"R$ {dre['lucro_operacional']:,.2f}")

        margem = 0
        if dre["receita_bruta"] > 0:
            margem = (dre["lucro_operacional"] / dre["receita_bruta"]) * 100

        st.metric("📊 Margem Líquida", f"{margem:.2f}%")
        
    st.markdown("---")

    st.markdown("### 📄 Exportar Relatório")

    if not df_f.empty:
        pdf_file = gerar_pdf(df_f, df, inicio, fim)

        st.download_button(
            label="📥 Baixar PDF",
            data=pdf_file,
            file_name=f"relatorio_{inicio.strftime('%Y%m%d')}_{fim.strftime('%Y%m%d')}.pdf",
            mime="application/pdf"
        )
    else:
        st.info("Sem vendas para gerar PDF.")
        st.subheader("🧾 Lista de Produtos")

    st.markdown("---")
    
    for _, row in df.iterrows():
        col1, col2 = st.columns([1, 3])

        with col1:
            img_path = PASTA_IMAGENS / f"{row['codigo']}.jpg"
            img_logo = BASE_DIR / "Logo_Modarte.jpg"

            if img_path.exists():
                st.image(str(img_path), width="stretch")
            else:
                st.image(str(img_logo), width="stretch")

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

            st.write(f"📦 Estoque Inicial: {estoque_inicial}")
            st.write(f"📦 Estoque Atual: {estoque_atual}")
            st.write(f"🛒 Vendidos: {int(vendidos_real)}")
            st.write(f"💰 Preço: R$ {preco:,.2f}")
            st.write(f"📈 Lucro unidade: R$ {lucro_unit:,.2f}")
            st.write(f"💵 Renda Total: R$ {renda_real:,.2f}")
            st.write(f"🏆 Lucro Total: R$ {lucro_real:,.2f}")

        st.markdown("---")
