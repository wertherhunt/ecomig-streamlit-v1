import streamlit as st
import pandas as pd
import plotly.express as px
import re # Biblioteca nativa movida para o topo, junto com as outras

# 1. Configuração Inicial da Página
st.set_page_config(page_title="Gestão de Demandas - Complexo de Museus", layout="wide", page_icon="🏛️")
st.title("🏛️ Painel de Controle de Demandas")
st.markdown("Acompanhamento operacional das instalações e acervos.")
st.markdown("---")

# 2. Funções Auxiliares (O que o app sabe fazer)
@st.cache_data
def carregar_dados():
    # Lê especificamente a primeira aba (índice 0)
    df = pd.read_excel("demandas.xlsx", sheet_name=0)
    
    # Padronizando o nome das colunas caso haja espaços extras
    df.columns = df.columns.str.strip().str.upper()
    
    # Convertendo as colunas de datas para o formato datetime do Pandas
    colunas_de_data = ['DATA SOLICITAÇÃO', 'FINALIZADO', 'PREVISÃO']
    for col in colunas_de_data:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors='coerce')
            
    return df

def gerar_lista_de_compras(df):
    st.markdown("---")
    st.subheader("📦 Lista Consolidada de Materiais")
    
    # Filtra apenas as demandas que têm algo escrito na coluna de materiais e que NÃO estão finalizadas
    df_pendentes_mat = df[
        (~df['STATUS'].str.contains('Solucionado|Finalizado', case=False, na=False)) & 
        (df['MATERIAIS NECESSÁRIOS'].notna())
    ]
    
    if df_pendentes_mat.empty:
        st.info("Nenhum material pendente para os filtros selecionados.")
        return

    lista_compras = {}
    
    # Varre cada linha da coluna de materiais
    for linha in df_pendentes_mat['MATERIAIS NECESSÁRIOS']:
        # Divide os itens por vírgula ou ponto e vírgula
        itens = re.split(r'[,;]', str(linha))
        
        for item in itens:
            item = item.strip().lower()
            if not item: 
                continue
            
            # Tenta encontrar um número no início do texto
            match = re.search(r'(\d+)\s*(.*)', item)
            
            if match:
                qtd = int(match.group(1))
                nome_material = match.group(2).strip().capitalize()
                # Limpa caracteres extras como 'x' se a pessoa digitou "10x"
                if nome_material.startswith('x '):
                    nome_material = nome_material[2:].capitalize()
            else:
                # Se a pessoa não botou número, assume que é 1
                qtd = 1
                nome_material = item.capitalize()
                
            # Soma no dicionário
            if nome_material in lista_compras:
                lista_compras[nome_material] += qtd
            else:
                lista_compras[nome_material] = qtd
                
    # Converte o dicionário para um DataFrame do Pandas
    df_compras = pd.DataFrame(list(lista_compras.items()), columns=['Material / Especificação', 'Quantidade Total'])
    df_compras = df_compras.sort_values(by='Quantidade Total', ascending=False).reset_index(drop=True)
    
    # Mostra a tabela e um botão para baixar como CSV
    col1, col2 = st.columns([2, 1])
    with col1:
        st.dataframe(df_compras, use_container_width=True)
    with col2:
        csv = df_compras.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Baixar Lista de Compras (CSV)",
            data=csv,
            file_name='lista_de_materiais.csv',
            mime='text/csv',
        )


# 3. Execução Principal do Painel (Aqui o app roda de fato)
try:
    df = carregar_dados()

    # Barra Lateral (Filtros)
    st.sidebar.header("Filtros de Visualização")
    
    lista_locais = df['LOCAL'].dropna().unique().tolist()
    locais_selecionados = st.sidebar.multiselect("📍 Selecione o Local:", options=lista_locais, default=lista_locais)

    lista_status = df['STATUS'].dropna().unique().tolist()
    status_selecionados = st.sidebar.multiselect("📌 Status da Demanda:", options=lista_status, default=lista_status)

    df_filtrado = df[
        (df['LOCAL'].isin(locais_selecionados)) & 
        (df['STATUS'].isin(status_selecionados))
    ]

    # Indicadores Principais (KPIs)
    st.subheader("Visão Geral")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total de Demandas (Filtro)", len(df_filtrado))
    with col2:
        pendentes = len(df_filtrado[df_filtrado['STATUS'].str.contains('Pendente', case=False, na=False)])
        st.metric("⏳ Pendentes", pendentes)
    with col3:
        criticas = len(df_filtrado[(df_filtrado['URGÊNCIA'].isin([1, 2])) & (~df_filtrado['STATUS'].str.contains('Solucionado|Finalizado', case=False, na=False))])
        st.metric("🚨 Críticas em Aberto (Urgência 1 e 2)", criticas)
    with col4:
        solucionadas = len(df_filtrado[df_filtrado['STATUS'].str.contains('Solucionado|Finalizado', case=False, na=False)])
        st.metric("✅ Solucionadas", solucionadas)

    st.markdown("---")

    # Gráficos Interativos
    c1, c2 = st.columns(2)

    with c1:
        st.subheader("Volume de Demandas por Local")
        contagem_local = df_filtrado['LOCAL'].value_counts().reset_index()
        contagem_local.columns = ['LOCAL', 'CONTAGEM']
        fig_local = px.bar(contagem_local, x='LOCAL', y='CONTAGEM', 
                           text_auto=True, color='LOCAL',
                           color_discrete_sequence=px.colors.qualitative.Pastel)
        fig_local.update_layout(xaxis_title="", yaxis_title="Quantidade", showlegend=False)
        st.plotly_chart(fig_local, use_container_width=True)

    with c2:
        st.subheader("Distribuição por Natureza")
        fig_natureza = px.pie(df_filtrado, names='NATUREZA', hole=0.4,
                              color_discrete_sequence=px.colors.qualitative.Set3)
        st.plotly_chart(fig_natureza, use_container_width=True)

    # Chama a função que processa os materiais passando os dados filtrados!
    gerar_lista_de_compras(df_filtrado)

    # Tabela de Detalhamento
    st.markdown("---")
    st.subheader("📋 Detalhamento de Ações Pendentes")
    
    df_pendentes = df_filtrado[~df_filtrado['STATUS'].str.contains('Solucionado|Finalizado', case=False, na=False)]
    df_pendentes = df_pendentes.sort_values(by=['URGÊNCIA', 'DATA SOLICITAÇÃO'], ascending=[True, True])
    
    colunas_tabela = ['URGÊNCIA', 'LOCAL', 'AÇÃO', 'RESPONSÁVEL', 'DATA SOLICITAÇÃO', 'PREVISÃO']
    st.dataframe(df_pendentes[colunas_tabela], use_container_width=True, hide_index=True)

except Exception as e:
    st.error(f"Erro ao carregar ou processar os dados: {e}")
    st.info("Certifique-se de que o arquivo 'demandas.xlsx' está na mesma pasta que este script e que não está aberto no Excel.")