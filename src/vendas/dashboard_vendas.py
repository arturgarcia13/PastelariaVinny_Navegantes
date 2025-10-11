"""
Dashboard Interativo - Pastelaria Vinny Navegantes
Análise de vendas em tempo real com visualizações interativas
"""

import dash
from dash import dcc, html, Input, Output
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from datetime import datetime
import os

# Configurações
app = dash.Dash(__name__)
app.title = "Dashboard Vendas - Pastelaria Vinny"

# Função para carregar e processar dados
def carregar_dados():
    """Carrega e processa os dados de vendas"""
    try:
        # Caminhos dos arquivos
        base_path = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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
        print(f"Erro ao carregar dados: {e}")
        return pd.DataFrame()

# Carregar dados
df = carregar_dados()

# Filtrar setembro 2025 (período principal)
df_setembro = df[df['DateTime'].dt.month == 9].copy() if len(df) > 0 else pd.DataFrame()

# Layout do Dashboard
app.layout = html.Div([
    # Header
    html.Div([
        html.H1("🥟 Dashboard Vendas - Pastelaria Vinny Navegantes", 
                style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': '10px'}),
        html.P(f"Análise em tempo real • Período: Setembro 2025 • Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}", 
               style={'textAlign': 'center', 'color': '#7f8c8d'})
    ], style={'backgroundColor': '#ecf0f1', 'padding': '20px', 'marginBottom': '20px'}),
    
    # KPIs Principais
    html.Div([
        html.Div([
            html.H3(f"{len(df_setembro):,}", style={'color': '#3498db', 'margin': '0'}),
            html.P("Total Transações", style={'margin': '0'})
        ], className='kpi-box', style={'textAlign': 'center', 'backgroundColor': 'white', 
                                     'padding': '20px', 'borderRadius': '10px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}),
        
        html.Div([
            html.H3(f"R$ {df_setembro['Valor'].sum():,.2f}" if len(df_setembro) > 0 else "R$ 0,00", 
                    style={'color': '#27ae60', 'margin': '0'}),
            html.P("Faturamento Total", style={'margin': '0'})
        ], className='kpi-box', style={'textAlign': 'center', 'backgroundColor': 'white', 
                                     'padding': '20px', 'borderRadius': '10px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}),
        
        html.Div([
            html.H3(f"R$ {df_setembro['Valor'].mean():.2f}" if len(df_setembro) > 0 else "R$ 0,00", 
                    style={'color': '#e74c3c', 'margin': '0'}),
            html.P("Ticket Médio", style={'margin': '0'})
        ], className='kpi-box', style={'textAlign': 'center', 'backgroundColor': 'white', 
                                     'padding': '20px', 'borderRadius': '10px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}),
        
        html.Div([
            html.H3(f"{df_setembro['DateTime'].dt.date.nunique()}" if len(df_setembro) > 0 else "0", 
                    style={'color': '#9b59b6', 'margin': '0'}),
            html.P("Dias Operação", style={'margin': '0'})
        ], className='kpi-box', style={'textAlign': 'center', 'backgroundColor': 'white', 
                                     'padding': '20px', 'borderRadius': '10px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'})
        
    ], style={'display': 'flex', 'justifyContent': 'space-around', 'marginBottom': '30px', 'gap': '20px'}),
    
    # Filtros
    html.Div([
        html.Div([
            html.Label("Método de Pagamento:", style={'fontWeight': 'bold'}),
            dcc.Dropdown(
                id='filtro-metodo',
                options=[{'label': 'Todos', 'value': 'Todos'}] + 
                        [{'label': metodo, 'value': metodo} for metodo in df['Metodo_Pagamento'].unique()] if len(df) > 0 else [],
                value='Todos',
                style={'marginTop': '5px'}
            )
        ], style={'width': '30%'}),
        
        html.Div([
            html.Label("Período:", style={'fontWeight': 'bold'}),
            dcc.DatePickerRange(
                id='filtro-data',
                start_date=df_setembro['DateTime'].min().date() if len(df_setembro) > 0 else datetime.now().date(),
                end_date=df_setembro['DateTime'].max().date() if len(df_setembro) > 0 else datetime.now().date(),
                display_format='DD/MM/YYYY',
                style={'marginTop': '5px'}
            )
        ], style={'width': '30%'}),
        
        html.Div([
            html.Label("Faixa de Valor:", style={'fontWeight': 'bold'}),
            dcc.RangeSlider(
                id='filtro-valor',
                min=df_setembro['Valor'].min() if len(df_setembro) > 0 else 0,
                max=df_setembro['Valor'].max() if len(df_setembro) > 0 else 100,
                value=[df_setembro['Valor'].min() if len(df_setembro) > 0 else 0, 
                       df_setembro['Valor'].max() if len(df_setembro) > 0 else 100],
                marks={int(i): f'R${int(i)}' for i in np.linspace(
                    df_setembro['Valor'].min() if len(df_setembro) > 0 else 0,
                    df_setembro['Valor'].max() if len(df_setembro) > 0 else 100, 5)},
                tooltip={"placement": "bottom", "always_visible": True}
            )
        ], style={'width': '35%'})
        
    ], style={'display': 'flex', 'justifyContent': 'space-between', 'marginBottom': '30px', 
             'backgroundColor': 'white', 'padding': '20px', 'borderRadius': '10px',
             'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'}),
    
    # Gráficos Principais
    html.Div([
        # Primeira linha de gráficos
        html.Div([
            dcc.Graph(id='grafico-metodos'),
            dcc.Graph(id='grafico-temporal')
        ], style={'display': 'flex', 'gap': '20px'}),
        
        # Segunda linha de gráficos
        html.Div([
            dcc.Graph(id='grafico-horarios'),
            dcc.Graph(id='grafico-distribuicao')
        ], style={'display': 'flex', 'gap': '20px', 'marginTop': '20px'})
    ]),
    
    # Tabela de dados
    html.Div([
        html.H3("📊 Dados Detalhados", style={'color': '#2c3e50'}),
        html.Div(id='tabela-resumo')
    ], style={'marginTop': '30px', 'backgroundColor': 'white', 'padding': '20px', 
             'borderRadius': '10px', 'boxShadow': '0 2px 4px rgba(0,0,0,0.1)'})
    
], style={'padding': '20px', 'backgroundColor': '#f8f9fa', 'minHeight': '100vh'})

# Callbacks para interatividade
@app.callback(
    [Output('grafico-metodos', 'figure'),
     Output('grafico-temporal', 'figure'),
     Output('grafico-horarios', 'figure'),
     Output('grafico-distribuicao', 'figure'),
     Output('tabela-resumo', 'children')],
    [Input('filtro-metodo', 'value'),
     Input('filtro-data', 'start_date'),
     Input('filtro-data', 'end_date'),
     Input('filtro-valor', 'value')]
)
def atualizar_dashboard(metodo_selecionado, data_inicio, data_fim, faixa_valor):
    # Filtrar dados
    df_filtrado = df_setembro.copy() if len(df_setembro) > 0 else pd.DataFrame()
    
    if len(df_filtrado) == 0:
        # Retornar gráficos vazios se não há dados
        fig_vazia = go.Figure()
        fig_vazia.add_annotation(text="Nenhum dado disponível", xref="paper", yref="paper",
                               x=0.5, y=0.5, showarrow=False)
        return fig_vazia, fig_vazia, fig_vazia, fig_vazia, "Nenhum dado disponível"
    
    # Aplicar filtros
    if metodo_selecionado != 'Todos':
        df_filtrado = df_filtrado[df_filtrado['Metodo_Pagamento'] == metodo_selecionado]
    
    if data_inicio and data_fim:
        df_filtrado = df_filtrado[
            (df_filtrado['DateTime'].dt.date >= pd.to_datetime(data_inicio).date()) &
            (df_filtrado['DateTime'].dt.date <= pd.to_datetime(data_fim).date())
        ]
    
    if faixa_valor:
        df_filtrado = df_filtrado[
            (df_filtrado['Valor'] >= faixa_valor[0]) &
            (df_filtrado['Valor'] <= faixa_valor[1])
        ]
    
    # Gráfico 1: Distribuição por métodos de pagamento
    metodos_stats = df_filtrado.groupby('Metodo_Pagamento').agg({
        'Valor': ['count', 'sum']
    }).round(2)
    metodos_stats.columns = ['Quantidade', 'Faturamento']
    metodos_stats = metodos_stats.reset_index()
    
    fig_metodos = go.Figure(data=[
        go.Bar(name='Quantidade', x=metodos_stats['Metodo_Pagamento'], 
               y=metodos_stats['Quantidade'], yaxis='y', offsetgroup=1),
        go.Bar(name='Faturamento (R$)', x=metodos_stats['Metodo_Pagamento'], 
               y=metodos_stats['Faturamento'], yaxis='y2', offsetgroup=2)
    ])
    fig_metodos.update_layout(
        title='💳 Vendas por Método de Pagamento',
        xaxis=dict(title='Método'),
        yaxis=dict(title='Quantidade', side='left'),
        yaxis2=dict(title='Faturamento (R$)', side='right', overlaying='y'),
        barmode='group'
    )
    
    # Gráfico 2: Evolução temporal
    vendas_diarias = df_filtrado.groupby(df_filtrado['DateTime'].dt.date).agg({
        'Valor': ['count', 'sum']
    }).round(2)
    vendas_diarias.columns = ['Quantidade', 'Faturamento']
    vendas_diarias = vendas_diarias.reset_index()
    
    fig_temporal = go.Figure()
    fig_temporal.add_trace(go.Scatter(
        x=vendas_diarias['DateTime'], y=vendas_diarias['Faturamento'],
        mode='lines+markers', name='Faturamento Diário',
        line=dict(color='#3498db', width=3)
    ))
    fig_temporal.update_layout(
        title='📈 Evolução do Faturamento Diário',
        xaxis_title='Data',
        yaxis_title='Faturamento (R$)'
    )
    
    # Gráfico 3: Vendas por horário
    vendas_hora = df_filtrado.groupby('Hora_Int')['Valor'].agg(['count', 'sum']).round(2)
    vendas_hora.columns = ['Quantidade', 'Faturamento']
    vendas_hora = vendas_hora.reset_index()
    
    fig_horarios = go.Figure()
    fig_horarios.add_trace(go.Bar(
        x=vendas_hora['Hora_Int'], y=vendas_hora['Quantidade'],
        name='Quantidade', marker_color='#2ecc71'
    ))
    fig_horarios.update_layout(
        title='🕐 Distribuição de Vendas por Horário',
        xaxis_title='Hora do Dia',
        yaxis_title='Quantidade de Transações'
    )
    
    # Gráfico 4: Distribuição de valores
    fig_distribuicao = go.Figure()
    fig_distribuicao.add_trace(go.Histogram(
        x=df_filtrado['Valor'], nbinsx=20,
        marker_color='#e74c3c', opacity=0.7
    ))
    fig_distribuicao.update_layout(
        title='💰 Distribuição dos Valores de Transação',
        xaxis_title='Valor (R$)',
        yaxis_title='Frequência'
    )
    
    # Tabela resumo
    if len(df_filtrado) > 0:
        resumo_stats = {
            'Métrica': ['Transações', 'Faturamento Total', 'Ticket Médio', 'Maior Venda', 'Menor Venda'],
            'Valor': [
                f"{len(df_filtrado):,}",
                f"R$ {df_filtrado['Valor'].sum():,.2f}",
                f"R$ {df_filtrado['Valor'].mean():.2f}",
                f"R$ {df_filtrado['Valor'].max():.2f}",
                f"R$ {df_filtrado['Valor'].min():.2f}"
            ]
        }
        
        tabela = html.Table([
            html.Thead([html.Tr([html.Th(col) for col in resumo_stats.keys()])]),
            html.Tbody([html.Tr([html.Td(resumo_stats[col][i]) for col in resumo_stats.keys()]) 
                       for i in range(len(resumo_stats['Métrica']))])
        ], style={'width': '100%', 'textAlign': 'center'})
    else:
        tabela = html.P("Nenhum dado encontrado com os filtros aplicados.")
    
    return fig_metodos, fig_temporal, fig_horarios, fig_distribuicao, tabela

if __name__ == '__main__':
    print("🚀 Iniciando Dashboard da Pastelaria Vinny Navegantes...")
    print("📊 Acesse: http://localhost:8050")
    app.run(debug=True, port=8050)