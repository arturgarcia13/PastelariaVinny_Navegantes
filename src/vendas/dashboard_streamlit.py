"""
Dashboard Streamlit - Pastelaria Vinny Navegantes
Análise completa de vendas com visualizações interativas
"""

import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

# Configuração da página
st.set_page_config(
    page_title="Dashboard Pastelaria Vinny",
    page_icon="🥟",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #2c3e50;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin-bottom: 1rem;
    }
    .insight-box {
        background-color: #f8f9fa;
        padding: 1rem;
        border-left: 4px solid #3498db;
        margin: 1rem 0;
        color: #2c3e50;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def carregar_dados():
    """Carrega e processa os dados de vendas"""
    try:
        # Caminhos dos arquivos
        base_path = os.path.dirname(os.path.abspath(__file__))
        pix_path = os.path.join(base_path, 'outputs', 'reports', 'transacoes_pix.csv')
        credito_path = os.path.join(base_path, 'outputs', 'reports', 'transacoes_credito.csv')
        debito_path = os.path.join(base_path, 'outputs', 'reports', 'transacoes_debito.csv')
        
        # Carregar dados
        pix_df = pd.read_csv(pix_path, delimiter=';')
        credito_df = pd.read_csv(credito_path, delimiter=';')
        debito_df = pd.read_csv(debito_path, delimiter=';')
        
        # Função para limpar valores
        def limpar_valor(valor):
            if isinstance(valor, str):
                return float(valor.replace('R$', '').replace(',', '.').strip())
            return float(valor)
        
        # Padronizar dados
        def padronizar_dados(df, tipo_pagamento):
            df = df.copy()
            df.columns = ['Data', 'Hora', 'Valor', 'Tipo_Venda', 'Arquivo_Referencia']
            df['Valor'] = df['Valor'].apply(limpar_valor)
            df['Metodo_Pagamento'] = tipo_pagamento
            df['DateTime'] = pd.to_datetime(df['Data'] + ' ' + df['Hora'], 
                                          format='%d/%m/%Y %H:%M', errors='coerce')
            df['Hora_Int'] = df['DateTime'].dt.hour
            df['Dia_Semana'] = df['DateTime'].dt.day_name()
            df['Mes'] = df['DateTime'].dt.month
            df['Dia'] = df['DateTime'].dt.day
            df['Data_Apenas'] = df['DateTime'].dt.date
            return df
        
        # Processar dados
        pix_clean = padronizar_dados(pix_df, 'PIX')
        credito_clean = padronizar_dados(credito_df, 'Crédito')
        debito_clean = padronizar_dados(debito_df, 'Débito')
        
        # Combinar dados
        df_completo = pd.concat([pix_clean, credito_clean, debito_clean], ignore_index=True)
        df_completo = df_completo.dropna(subset=['DateTime'])
        
        return df_completo
        
    except Exception as e:
        st.error(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

def criar_metricas_kpi(df_filtrado):
    """Cria as métricas principais (KPIs)"""
    if len(df_filtrado) == 0:
        st.warning("Nenhum dado encontrado com os filtros aplicados")
        return
    
    # Métricas principais
    total_transacoes = len(df_filtrado)
    faturamento_total = df_filtrado['Valor'].sum()
    ticket_medio = df_filtrado['Valor'].mean()
    maior_venda = df_filtrado['Valor'].max()
    
    # Exibir métricas em colunas
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            label="🏪 Total de Transações",
            value=f"{total_transacoes:,}",
            delta=f"+{total_transacoes//30} por dia"
        )
    
    with col2:
        st.metric(
            label="💰 Faturamento Total",
            value=f"R$ {faturamento_total:,.2f}",
            delta=f"R$ {faturamento_total/total_transacoes:.2f} por venda"
        )
    
    with col3:
        st.metric(
            label="🎯 Ticket Médio",
            value=f"R$ {ticket_medio:.2f}",
            delta=f"Máx: R$ {maior_venda:.2f}"
        )
    
    with col4:
        dias_operacao = df_filtrado['Data_Apenas'].nunique()
        st.metric(
            label="📅 Dias de Operação",
            value=f"{dias_operacao}",
            delta=f"R$ {faturamento_total/dias_operacao:.2f} por dia"
        )

def criar_graficos_principais(df_filtrado):
    """Cria os gráficos principais do dashboard"""
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico de pizza - Distribuição por método
        st.subheader("💳 Distribuição por Método de Pagamento")
        metodos_data = df_filtrado.groupby('Metodo_Pagamento')['Valor'].agg(['count', 'sum']).reset_index()
        
        fig_pie = px.pie(
            metodos_data, 
            values='sum', 
            names='Metodo_Pagamento',
            title="Faturamento por Método",
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig_pie.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        # Gráfico de barras - Quantidade por método
        st.subheader("📊 Quantidade de Transações")
        fig_bar = px.bar(
            metodos_data,
            x='Metodo_Pagamento',
            y='count',
            title="Transações por Método",
            color='Metodo_Pagamento',
            color_discrete_sequence=px.colors.qualitative.Pastel
        )
        fig_bar.update_layout(showlegend=False)
        st.plotly_chart(fig_bar, use_container_width=True)

def criar_analise_temporal(df_filtrado):
    """Cria análise temporal das vendas"""
    
    st.subheader("📈 Análise Temporal")
    
    # Vendas por dia
    vendas_diarias = df_filtrado.groupby('Data_Apenas').agg({
        'Valor': ['count', 'sum', 'mean']
    }).round(2)
    vendas_diarias.columns = ['Quantidade', 'Faturamento', 'Ticket_Medio']
    vendas_diarias = vendas_diarias.reset_index()
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Evolução do faturamento
        fig_linha = px.line(
            vendas_diarias,
            x='Data_Apenas',
            y='Faturamento',
            title="Evolução do Faturamento Diário",
            markers=True
        )
        fig_linha.update_traces(line_color='#3498db', line_width=3)
        st.plotly_chart(fig_linha, use_container_width=True)
    
    with col2:
        # Vendas por horário
        vendas_hora = df_filtrado.groupby('Hora_Int').size().reset_index(name='Quantidade')
        fig_hora = px.bar(
            vendas_hora,
            x='Hora_Int',
            y='Quantidade',
            title="Distribuição por Horário",
            color='Quantidade',
            color_continuous_scale='viridis'
        )
        st.plotly_chart(fig_hora, use_container_width=True)

def criar_analise_avancada(df_filtrado):
    """Cria análise avançada com insights"""
    
    st.subheader("🔍 Análise Avançada")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Distribuição de valores
        fig_hist = px.histogram(
            df_filtrado,
            x='Valor',
            nbins=20,
            title="Distribuição dos Valores",
            color_discrete_sequence=['#e74c3c']
        )
        st.plotly_chart(fig_hist, use_container_width=True)
    
    with col2:
        # Boxplot por método
        fig_box = px.box(
            df_filtrado,
            x='Metodo_Pagamento',
            y='Valor',
            title="Distribuição de Valores por Método",
            color='Metodo_Pagamento'
        )
        st.plotly_chart(fig_box, use_container_width=True)

def criar_insights_estrategicos(df_filtrado):
    """Cria seção de insights estratégicos"""
    
    st.subheader("💡 Insights Estratégicos")
    
    if len(df_filtrado) == 0:
        return
    
    # Análise por faixas de valor
    def classificar_valor(valor):
        if valor <= 10:
            return 'Até R$ 10'
        elif valor <= 20:
            return 'R$ 11-20'
        elif valor <= 30:
            return 'R$ 21-30'
        elif valor <= 50:
            return 'R$ 31-50'
        else:
            return 'Acima R$ 50'
    
    df_filtrado['Faixa_Valor'] = df_filtrado['Valor'].apply(classificar_valor)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 🎯 Top Insights")
        
        # Horário de pico
        horario_pico = df_filtrado.groupby('Hora_Int').size().idxmax()
        vendas_pico = df_filtrado.groupby('Hora_Int').size().max()
        
        # Método mais usado
        metodo_top = df_filtrado['Metodo_Pagamento'].value_counts().index[0]
        metodo_percent = (df_filtrado['Metodo_Pagamento'].value_counts().iloc[0] / len(df_filtrado) * 100)
        
        # Dia com maior faturamento
        melhor_dia = df_filtrado.groupby('Data_Apenas')['Valor'].sum().idxmax()
        faturamento_melhor_dia = df_filtrado.groupby('Data_Apenas')['Valor'].sum().max()
        
        st.markdown(f"""
        <div class="insight-box">
        <strong>🕐 Horário de Pico:</strong> {horario_pico}h ({vendas_pico} vendas)<br>
        <strong>💳 Método Preferido:</strong> {metodo_top} ({metodo_percent:.1f}%)<br>
        <strong>📅 Melhor Dia:</strong> {melhor_dia} (R$ {faturamento_melhor_dia:.2f})<br>
        <strong>🎯 Ticket Médio:</strong> R$ {df_filtrado['Valor'].mean():.2f}
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Análise por faixas
        faixas_stats = df_filtrado.groupby('Faixa_Valor').agg({
            'Valor': ['count', 'sum']
        }).round(2)
        faixas_stats.columns = ['Quantidade', 'Faturamento']
        faixas_stats['Participacao'] = (faixas_stats['Faturamento'] / faixas_stats['Faturamento'].sum() * 100).round(1)
        faixas_stats = faixas_stats.reset_index()
        
        st.markdown("#### 💰 Análise por Faixas de Valor")
        st.dataframe(faixas_stats, use_container_width=True)

def main():
    """Função principal do dashboard"""
    
    # Header
    st.markdown('<h1 class="main-header">🥟 Dashboard Pastelaria Vinny Navegantes</h1>', unsafe_allow_html=True)
    st.markdown(f"**Análise em Tempo Real** • Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    # Carregar dados
    df = carregar_dados()
    
    if len(df) == 0:
        st.error("Nenhum dado disponível")
        return
    
    # Sidebar com filtros
    st.sidebar.header("🔧 Filtros")
    
    # Filtro por método de pagamento
    metodos_disponiveis = ['Todos'] + list(df['Metodo_Pagamento'].unique())
    metodo_selecionado = st.sidebar.selectbox("Método de Pagamento", metodos_disponiveis)
    
    # Filtro por período
    data_min = df['DateTime'].min().date()
    data_max = df['DateTime'].max().date()
    
    periodo_inicio = st.sidebar.date_input("Data Início", value=data_min, min_value=data_min, max_value=data_max)
    periodo_fim = st.sidebar.date_input("Data Fim", value=data_max, min_value=data_min, max_value=data_max)
    
    # Filtro por faixa de valor
    valor_min = float(df['Valor'].min())
    valor_max = float(df['Valor'].max())
    faixa_valor = st.sidebar.slider(
        "Faixa de Valor (R$)",
        min_value=valor_min,
        max_value=valor_max,
        value=(valor_min, valor_max),
        step=1.0
    )
    
    # Aplicar filtros
    df_filtrado = df.copy()
    
    if metodo_selecionado != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Metodo_Pagamento'] == metodo_selecionado]
    
    df_filtrado = df_filtrado[
        (df_filtrado['Data_Apenas'] >= periodo_inicio) &
        (df_filtrado['Data_Apenas'] <= periodo_fim) &
        (df_filtrado['Valor'] >= faixa_valor[0]) &
        (df_filtrado['Valor'] <= faixa_valor[1])
    ]
    
    # Mostrar informações dos filtros
    st.sidebar.markdown("---")
    st.sidebar.markdown(f"**Registros filtrados:** {len(df_filtrado):,}")
    st.sidebar.markdown(f"**Total original:** {len(df):,}")
    
    # Dashboard principal
    if len(df_filtrado) > 0:
        # KPIs
        criar_metricas_kpi(df_filtrado)
        
        st.markdown("---")
        
        # Gráficos principais
        criar_graficos_principais(df_filtrado)
        
        st.markdown("---")
        
        # Análise temporal
        criar_analise_temporal(df_filtrado)
        
        st.markdown("---")
        
        # Análise avançada
        criar_analise_avancada(df_filtrado)
        
        st.markdown("---")
        
        # Insights estratégicos
        criar_insights_estrategicos(df_filtrado)
        
        # Tabela de dados brutos (opcional)
        if st.sidebar.checkbox("Mostrar dados brutos"):
            st.subheader("📋 Dados Detalhados")
            st.dataframe(
                df_filtrado[['DateTime', 'Valor', 'Metodo_Pagamento', 'Hora_Int']].sort_values('DateTime', ascending=False),
                use_container_width=True
            )
    
    else:
        st.warning("Nenhum registro encontrado com os filtros aplicados")
    
    # Footer
    st.markdown("---")
    st.markdown("**Dashboard criado com ❤️ usando Streamlit**")

if __name__ == "__main__":
    main()