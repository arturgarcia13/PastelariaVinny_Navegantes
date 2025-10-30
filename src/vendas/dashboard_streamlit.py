"""
Dashboard Executivo Multi-Mensal - Pastelaria Vinny Navegantes
Análise completa e comparativa de vendas com visualizações interativas

Recursos:
- Análise multi-mensal (Agosto, Setembro, e expansível)
- Comparações temporais avançadas
- Filtros por período do dia, horário, método de pagamento
- KPIs executivos consolidados
- Insights estratégicos para tomada de decisão
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
    """Carrega e processa os dados de vendas multi-mensal"""
    try:
        # Configuração de meses disponíveis - Sistema modular
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        meses_disponiveis = {
            'setembro': os.path.join(base_path, 'outputs', 'reports', 'setembro'),
            'agosto': os.path.join(base_path, 'outputs', 'reports', 'agosto'),
        }
        
        def limpar_valor(valor_str):
            """Converte string de valor monetário para float"""
            if pd.isna(valor_str):
                return 0.0
            try:
                valor_limpo = str(valor_str).replace('R$', '').replace(' ', '').replace(',', '.')
                return float(valor_limpo)
            except:
                return 0.0
        
        def classificar_periodo(hora):
            """Classifica hora em período do dia"""
            if 6 <= hora < 12:
                return 'Manhã'
            elif 12 <= hora < 18:
                return 'Tarde'
            elif 18 <= hora < 24:
                return 'Noite'
            else:
                return 'Madrugada'
        
        def carregar_dados_mes(mes, caminho_base):
            """Carrega dados de um mês específico"""
            dados_mes = {'pix': pd.DataFrame(), 'credito': pd.DataFrame(), 'debito': pd.DataFrame()}
            
            # Mapeamento de arquivos por método
            if mes == 'setembro':
                arquivos = {
                    'pix': 'transacoes_pix.csv',
                    'credito': 'transacoes_credito.csv', 
                    'debito': 'transacoes_debito.csv'
                }
            else:  # Para agosto e outros meses
                arquivos = {
                    'pix': 'pix/transacoes_consolidadas.csv',
                    'credito': 'credito/transacoes_consolidadas.csv', 
                    'debito': 'debito/transacoes_consolidadas.csv'
                }
            
            for metodo, arquivo in arquivos.items():
                caminho_arquivo = os.path.join(caminho_base, arquivo)
                if os.path.exists(caminho_arquivo):
                    try:
                        df = pd.read_csv(caminho_arquivo, sep=';')
                        dados_mes[metodo] = df
                    except Exception as e:
                        st.warning(f"Erro ao carregar {metodo} do {mes}: {e}")
            
            return dados_mes
        
        def padronizar_dados(df, tipo_pagamento, mes):
            """Padroniza DataFrame com enriquecimento temporal"""
            if df.empty:
                return pd.DataFrame()
            
            df_clean = df.copy()
            df_clean['Metodo_Pagamento'] = tipo_pagamento
            df_clean['Mes_Nome'] = mes.capitalize()
            
            # Limpeza de valores
            if 'Valor' in df_clean.columns:
                df_clean['Valor'] = df_clean['Valor'].apply(limpar_valor)
            else:
                df_clean['Valor'] = 0.0
            
            # Processamento temporal
            if 'Data' in df_clean.columns and 'Hora' in df_clean.columns:
                try:
                    df_clean['DateTime'] = pd.to_datetime(
                        df_clean['Data'] + ' ' + df_clean['Hora'].astype(str), 
                        format='%d/%m/%Y %H:%M', errors='coerce'
                    )
                    
                    df_clean['Data_Apenas'] = df_clean['DateTime'].dt.date
                    df_clean['Hora_Int'] = df_clean['DateTime'].dt.hour
                    df_clean['Minuto'] = df_clean['DateTime'].dt.minute
                    df_clean['Dia_Semana'] = df_clean['DateTime'].dt.day_name()
                    df_clean['Dia_Mes'] = df_clean['DateTime'].dt.day
                    df_clean['Mes'] = df_clean['DateTime'].dt.month
                    df_clean['Ano'] = df_clean['DateTime'].dt.year
                    df_clean['Periodo_Dia'] = df_clean['Hora_Int'].apply(classificar_periodo)
                    
                except Exception as e:
                    st.warning(f"Erro no processamento temporal para {tipo_pagamento}: {e}")
            
            # Filtrar valores válidos
            df_clean = df_clean[(df_clean['Valor'] > 0) & (df_clean['Valor'] < 1000)]
            
            return df_clean
        
        # Carregar e processar todos os meses
        todos_dados = []
        
        for mes, caminho in meses_disponiveis.items():
            if os.path.exists(caminho):
                dados_mes = carregar_dados_mes(mes, caminho)
                
                # Padronizar cada método de pagamento
                pix_clean = padronizar_dados(dados_mes['pix'], 'PIX', mes)
                credito_clean = padronizar_dados(dados_mes['credito'], 'Crédito', mes)  
                debito_clean = padronizar_dados(dados_mes['debito'], 'Débito', mes)
                
                # Consolidar dados do mês
                if not (pix_clean.empty and credito_clean.empty and debito_clean.empty):
                    df_mes = pd.concat([pix_clean, credito_clean, debito_clean], ignore_index=True)
                    todos_dados.append(df_mes)
        
        # Consolidar todos os meses
        if todos_dados:
            df_completo = pd.concat(todos_dados, ignore_index=True)
            df_completo = df_completo.dropna(subset=['DateTime'])
            return df_completo
        else:
            st.error("Nenhum dado encontrado nos meses disponíveis")
            return pd.DataFrame()
        
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
        st.plotly_chart(fig_pie, config={'responsive': True})
    
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
        st.plotly_chart(fig_bar, config={'responsive': True})

def criar_analise_comparativa_mensal(df_filtrado):
    """Cria análise comparativa entre meses"""
    
    if 'Mes_Nome' not in df_filtrado.columns or df_filtrado['Mes_Nome'].nunique() < 2:
        return
    
    st.subheader("📊 Análise Comparativa Mensal")
    
    # Estatísticas por mês
    stats_mensal = df_filtrado.groupby('Mes_Nome').agg({
        'Valor': ['count', 'sum', 'mean']
    }).round(2)
    stats_mensal.columns = ['Transações', 'Faturamento', 'Ticket_Médio']
    stats_mensal = stats_mensal.reset_index()
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Faturamento por mês
        fig_fat_mes = px.bar(
            stats_mensal,
            x='Mes_Nome',
            y='Faturamento',
            title="💰 Faturamento por Mês",
            color='Faturamento',
            color_continuous_scale='viridis',
            text='Faturamento'
        )
        fig_fat_mes.update_traces(texttemplate='R$ %{text:,.0f}', textposition='outside')
        st.plotly_chart(fig_fat_mes, config={'responsive': True})
    
    with col2:
        # Transações por mês
        fig_trans_mes = px.bar(
            stats_mensal,
            x='Mes_Nome',
            y='Transações',
            title="🏪 Transações por Mês",
            color='Transações',
            color_continuous_scale='plasma',
            text='Transações'
        )
        fig_trans_mes.update_traces(texttemplate='%{text}', textposition='outside')
        st.plotly_chart(fig_trans_mes, config={'responsive': True})
    
    # Métricas comparativas
    if len(stats_mensal) >= 2:
        col1, col2, col3 = st.columns(3)
        
        # Calcular crescimento (assumindo ordem cronológica)
        primeiro_mes = stats_mensal.iloc[0]
        ultimo_mes = stats_mensal.iloc[-1]
        
        crescimento_faturamento = ((ultimo_mes['Faturamento'] - primeiro_mes['Faturamento']) / primeiro_mes['Faturamento'] * 100)
        crescimento_transacoes = ((ultimo_mes['Transações'] - primeiro_mes['Transações']) / primeiro_mes['Transações'] * 100)
        
        with col1:
            st.metric(
                "📈 Crescimento Faturamento",
                f"{crescimento_faturamento:+.1f}%",
                f"R$ {ultimo_mes['Faturamento'] - primeiro_mes['Faturamento']:+.2f}"
            )
        
        with col2:
            st.metric(
                "📊 Crescimento Transações",
                f"{crescimento_transacoes:+.1f}%",
                f"{ultimo_mes['Transações'] - primeiro_mes['Transações']:+.0f} vendas"
            )
        
        with col3:
            melhor_mes = stats_mensal.loc[stats_mensal['Faturamento'].idxmax(), 'Mes_Nome']
            st.metric(
                "🏆 Melhor Mês",
                melhor_mes,
                f"R$ {stats_mensal['Faturamento'].max():,.2f}"
            )

def criar_analise_temporal(df_filtrado):
    """Cria análise temporal das vendas"""
    
    st.subheader("📈 Análise Temporal Detalhada")
    
    # Vendas por dia
    vendas_diarias = df_filtrado.groupby('Data_Apenas').agg({
        'Valor': ['count', 'sum', 'mean']
    }).round(2)
    vendas_diarias.columns = ['Quantidade', 'Faturamento', 'Ticket_Medio']
    vendas_diarias = vendas_diarias.reset_index()
    
    # Análise por horário (quantidade e faturamento)
    vendas_hora = df_filtrado.groupby('Hora_Int').agg({
        'Valor': ['count', 'sum']
    }).round(2)
    vendas_hora.columns = ['Quantidade', 'Faturamento_Hora']
    vendas_hora = vendas_hora.reset_index()
    
    # Primeira linha - Faturamento diário e por horário (quantidade)
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
        st.plotly_chart(fig_linha, config={'responsive': True})
    
    with col2:
        # Quantidade de vendas por horário
        fig_hora_qtd = px.bar(
            vendas_hora,
            x='Hora_Int',
            y='Quantidade',
            title="Quantidade de Transações por Horário",
            color='Quantidade',
            color_continuous_scale='viridis'
        )
        st.plotly_chart(fig_hora_qtd, config={'responsive': True})
    
    # Segunda linha - Faturamento por horário
    st.subheader("💰 Faturamento por Horário do Dia")
    
    fig_hora_valor = px.bar(
        vendas_hora,
        x='Hora_Int',
        y='Faturamento_Hora',
        title="Valor Total Vendido por Horário",
        color='Faturamento_Hora',
        color_continuous_scale='plasma',
        text='Faturamento_Hora'
    )
    
    # Personalizar o gráfico
    fig_hora_valor.update_traces(
        texttemplate='R$ %{text:.0f}',
        textposition='outside'
    )
    
    fig_hora_valor.update_layout(
        xaxis_title="Horário",
        yaxis_title="Faturamento (R$)",
        showlegend=False,
        height=500
    )
    
    st.plotly_chart(fig_hora_valor, config={'responsive': True})
    
    # Estatísticas do horário de maior faturamento
    if len(vendas_hora) > 0:
        melhor_horario = vendas_hora.loc[vendas_hora['Faturamento_Hora'].idxmax()]
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "🕐 Horário de Maior Faturamento",
                f"{int(melhor_horario['Hora_Int'])}h",
                f"R$ {melhor_horario['Faturamento_Hora']:.2f}"
            )
        
        with col2:
            horario_mais_movimentado = vendas_hora.loc[vendas_hora['Quantidade'].idxmax()]
            st.metric(
                "📊 Horário Mais Movimentado",
                f"{int(horario_mais_movimentado['Hora_Int'])}h",
                f"{int(horario_mais_movimentado['Quantidade'])} vendas"
            )
        
        with col3:
            ticket_medio_horario = melhor_horario['Faturamento_Hora'] / melhor_horario['Quantidade']
            st.metric(
                "💎 Maior Ticket Médio/Hora",
                f"R$ {ticket_medio_horario:.2f}",
                f"às {int(melhor_horario['Hora_Int'])}h"
            )

def criar_analise_periodos(df_filtrado):
    """Cria análise por períodos do dia"""
    
    if 'Periodo_Dia' not in df_filtrado.columns:
        return
    
    st.subheader("🌅 Análise por Período do Dia")
    
    # Estatísticas por período
    periodos_stats = df_filtrado.groupby('Periodo_Dia').agg({
        'Valor': ['count', 'sum', 'mean']
    }).round(2)
    periodos_stats.columns = ['Transações', 'Faturamento', 'Ticket_Médio']
    periodos_stats = periodos_stats.reset_index()
    
    # Ordenar pelos períodos do dia
    ordem_periodos = ['Madrugada', 'Manhã', 'Tarde', 'Noite']
    periodos_stats['Periodo_Dia'] = pd.Categorical(periodos_stats['Periodo_Dia'], categories=ordem_periodos, ordered=True)
    periodos_stats = periodos_stats.sort_values('Periodo_Dia')
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Faturamento por período
        fig_periodo_fat = px.bar(
            periodos_stats,
            x='Periodo_Dia',
            y='Faturamento',
            title="💰 Faturamento por Período",
            color='Periodo_Dia',
            color_discrete_sequence=['#2c3e50', '#f39c12', '#e74c3c', '#8e44ad']
        )
        st.plotly_chart(fig_periodo_fat, config={'responsive': True})
    
    with col2:
        # Ticket médio por período
        fig_ticket_periodo = px.line(
            periodos_stats,
            x='Periodo_Dia',
            y='Ticket_Médio',
            title="🎯 Ticket Médio por Período",
            markers=True,
            line_shape='spline'
        )
        fig_ticket_periodo.update_traces(line_color='#3498db', line_width=4, marker_size=10)
        st.plotly_chart(fig_ticket_periodo, config={'responsive': True})

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
        st.plotly_chart(fig_hist, config={'responsive': True})
    
    with col2:
        # Boxplot por método
        fig_box = px.box(
            df_filtrado,
            x='Metodo_Pagamento',
            y='Valor',
            title="Distribuição de Valores por Método",
            color='Metodo_Pagamento'
        )
        st.plotly_chart(fig_box, config={'responsive': True})
    
    # Análise por dia da semana se houver dados suficientes
    if 'Dia_Semana' in df_filtrado.columns and len(df_filtrado) > 7:
        st.subheader("📅 Performance por Dia da Semana")
        
        # Traduzir dias da semana para português
        traducao_dias = {
            'Monday': 'Segunda', 'Tuesday': 'Terça', 'Wednesday': 'Quarta',
            'Thursday': 'Quinta', 'Friday': 'Sexta', 'Saturday': 'Sábado', 'Sunday': 'Domingo'
        }
        
        df_dias = df_filtrado.copy()
        df_dias['Dia_Semana_PT'] = df_dias['Dia_Semana'].map(traducao_dias)
        
        vendas_semana = df_dias.groupby('Dia_Semana_PT').agg({
            'Valor': ['count', 'sum', 'mean']
        }).round(2)
        vendas_semana.columns = ['Transações', 'Faturamento', 'Ticket_Médio']
        vendas_semana = vendas_semana.reset_index()
        
        fig_semana = px.bar(
            vendas_semana,
            x='Dia_Semana_PT',
            y='Faturamento',
            title="📊 Faturamento por Dia da Semana",
            color='Faturamento',
            color_continuous_scale='viridis'
        )
        st.plotly_chart(fig_semana, config={'responsive': True})

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
        
        # Melhor período do dia se disponível
        melhor_periodo = ""
        if 'Periodo_Dia' in df_filtrado.columns:
            periodo_top = df_filtrado.groupby('Periodo_Dia')['Valor'].sum().idxmax()
            melhor_periodo = f"<br><strong>🌅 Melhor Período:</strong> {periodo_top}"
        
        # Melhor mês se houver múltiplos
        melhor_mes_info = ""
        if 'Mes_Nome' in df_filtrado.columns and df_filtrado['Mes_Nome'].nunique() > 1:
            mes_top = df_filtrado.groupby('Mes_Nome')['Valor'].sum().idxmax()
            faturamento_mes_top = df_filtrado.groupby('Mes_Nome')['Valor'].sum().max()
            melhor_mes_info = f"<br><strong>📆 Melhor Mês:</strong> {mes_top} (R$ {faturamento_mes_top:,.2f})"
        
        st.markdown(f"""
        <div class="insight-box">
        <strong>🕐 Horário de Pico:</strong> {horario_pico}h ({vendas_pico} vendas)<br>
        <strong>💳 Método Preferido:</strong> {metodo_top} ({metodo_percent:.1f}%)<br>
        <strong>📅 Melhor Dia:</strong> {melhor_dia} (R$ {faturamento_melhor_dia:.2f})<br>
        <strong>🎯 Ticket Médio:</strong> R$ {df_filtrado['Valor'].mean():.2f}{melhor_periodo}{melhor_mes_info}
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
    
    # Header inicial
    st.markdown('<h1 class="main-header">🥟 Dashboard Executivo - Pastelaria Vinny Navegantes</h1>', unsafe_allow_html=True)
    
    # Carregar dados
    df = carregar_dados()
    
    # Informações sobre os dados carregados
    if len(df) > 0 and 'Mes_Nome' in df.columns:
        meses_info = sorted(df['Mes_Nome'].unique())
        periodo_info = f"**Período:** {', '.join(meses_info)} • **Total:** {len(df):,} transações • **Faturamento:** R$ {df['Valor'].sum():,.2f}"
    else:
        periodo_info = "**Análise Multi-Mensal de Vendas**"
    
    st.markdown(f"{periodo_info}")
    st.markdown(f"**Última atualização:** {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    
    if len(df) == 0:
        st.error("Nenhum dado disponível")
        return
    
    # Sidebar com filtros
    st.sidebar.header("🔧 Filtros de Análise")
    
    # Informações gerais dos dados
    st.sidebar.markdown("### 📊 Resumo dos Dados")
    meses_disponiveis_filtro = sorted(df['Mes_Nome'].unique()) if 'Mes_Nome' in df.columns else []
    total_transacoes = len(df)
    faturamento_total = df['Valor'].sum()
    
    st.sidebar.markdown(f"**Meses:** {', '.join(meses_disponiveis_filtro)}")
    st.sidebar.markdown(f"**Transações:** {total_transacoes:,}")
    st.sidebar.markdown(f"**Faturamento:** R$ {faturamento_total:,.2f}")
    
    st.sidebar.markdown("---")
    
    # Filtro por mês
    if 'Mes_Nome' in df.columns and len(meses_disponiveis_filtro) > 1:
        meses_opcoes = ['Todos'] + meses_disponiveis_filtro
        mes_selecionado = st.sidebar.selectbox("📅 Mês", meses_opcoes)
    else:
        mes_selecionado = 'Todos'
    
    # Filtro por método de pagamento
    metodos_disponiveis = ['Todos'] + list(df['Metodo_Pagamento'].unique())
    metodo_selecionado = st.sidebar.selectbox("💳 Método de Pagamento", metodos_disponiveis)
    
    # Filtro por período do dia
    if 'Periodo_Dia' in df.columns:
        periodos_disponiveis = ['Todos'] + list(df['Periodo_Dia'].unique())
        periodo_dia_selecionado = st.sidebar.selectbox("🌅 Período do Dia", periodos_disponiveis)
    else:
        periodo_dia_selecionado = 'Todos'
    
    # Filtro por faixa de horário
    hora_min = int(df['Hora_Int'].min()) if 'Hora_Int' in df.columns else 0
    hora_max = int(df['Hora_Int'].max()) if 'Hora_Int' in df.columns else 23
    faixa_horario = st.sidebar.slider(
        "🕐 Faixa de Horário",
        min_value=hora_min,
        max_value=hora_max,
        value=(hora_min, hora_max),
        step=1
    )
    
    # Filtro por período
    data_min = df['DateTime'].min().date()
    data_max = df['DateTime'].max().date()
    
    periodo_inicio = st.sidebar.date_input("📅 Data Início", value=data_min, min_value=data_min, max_value=data_max)
    periodo_fim = st.sidebar.date_input("📅 Data Fim", value=data_max, min_value=data_min, max_value=data_max)
    
    # Filtro por faixa de valor
    valor_min = float(df['Valor'].min())
    valor_max = float(df['Valor'].max())
    faixa_valor = st.sidebar.slider(
        "💰 Faixa de Valor (R$)",
        min_value=valor_min,
        max_value=valor_max,
        value=(valor_min, valor_max),
        step=1.0
    )
    
    # Aplicar filtros
    df_filtrado = df.copy()
    
    # Filtro por mês
    if mes_selecionado != 'Todos' and 'Mes_Nome' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['Mes_Nome'] == mes_selecionado]
    
    # Filtro por método de pagamento
    if metodo_selecionado != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Metodo_Pagamento'] == metodo_selecionado]
    
    # Filtro por período do dia
    if periodo_dia_selecionado != 'Todos' and 'Periodo_Dia' in df_filtrado.columns:
        df_filtrado = df_filtrado[df_filtrado['Periodo_Dia'] == periodo_dia_selecionado]
    
    # Filtros de data, horário e valor
    if 'Hora_Int' in df_filtrado.columns:
        df_filtrado = df_filtrado[
            (df_filtrado['Data_Apenas'] >= periodo_inicio) &
            (df_filtrado['Data_Apenas'] <= periodo_fim) &
            (df_filtrado['Hora_Int'] >= faixa_horario[0]) &
            (df_filtrado['Hora_Int'] <= faixa_horario[1]) &
            (df_filtrado['Valor'] >= faixa_valor[0]) &
            (df_filtrado['Valor'] <= faixa_valor[1])
        ]
    else:
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
        
        # Análise comparativa mensal (se houver múltiplos meses)
        criar_analise_comparativa_mensal(df_filtrado)
        
        st.markdown("---")
        
        # Gráficos principais
        criar_graficos_principais(df_filtrado)
        
        st.markdown("---")
        
        # Análise temporal
        criar_analise_temporal(df_filtrado)
        
        st.markdown("---")
        
        # Análise por períodos do dia
        criar_analise_periodos(df_filtrado)
        
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
                width='stretch'
            )
    
    else:
        st.warning("Nenhum registro encontrado com os filtros aplicados")
    
    # Footer
    st.markdown("---")
    
    # Informações técnicas
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**📊 Dashboard Executivo Multi-Mensal**")
        st.markdown("*Sistema de análise completa para tomada de decisão estratégica*")
    
    with col2:
        if len(df) > 0:
            st.markdown(f"**🔄 Dados processados:** {len(df):,} registros")
            if 'Mes_Nome' in df.columns:
                st.markdown(f"**📅 Meses analisados:** {df['Mes_Nome'].nunique()}")
    
    st.markdown("**Dashboard criado com ❤️ usando Streamlit • Sistema modular para crescimento**")

if __name__ == "__main__":
    main()