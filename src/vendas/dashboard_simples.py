"""
Dashboard Simplificado - Pastelaria Vinny Navegantes
Versão otimizada para visualização rápida dos dados
"""

import dash
from dash import dcc, html, Input, Output
import plotly.graph_objects as go
import pandas as pd
import numpy as np

def carregar_dados():
    """Carrega os dados de vendas"""
    try:
        # Carregar dados
        pix_df = pd.read_csv('outputs/reports/transacoes_pix.csv', delimiter=';')
        credito_df = pd.read_csv('outputs/reports/transacoes_credito.csv', delimiter=';')
        debito_df = pd.read_csv('outputs/reports/transacoes_debito.csv', delimiter=';')
        
        # Processar PIX
        pix_df['Metodo'] = 'PIX'
        pix_df['Valor_Limpo'] = pix_df['Valor']
        
        # Processar Crédito
        credito_df['Metodo'] = 'Crédito'
        credito_df['Valor_Limpo'] = credito_df['Valor'].str.replace('R$ ', '').str.replace(',', '.').astype(float)
        
        # Processar Débito
        debito_df['Metodo'] = 'Débito'
        debito_df['Valor_Limpo'] = debito_df['Valor'].str.replace('R$ ', '').str.replace(',', '.').astype(float)
        
        # Combinar
        df_completo = pd.concat([pix_df[['Data', 'Hora', 'Valor_Limpo', 'Metodo']], 
                               credito_df[['Data', 'Hora', 'Valor_Limpo', 'Metodo']], 
                               debito_df[['Data', 'Hora', 'Valor_Limpo', 'Metodo']]], 
                              ignore_index=True)
        
        # Criar datetime
        df_completo['DateTime'] = pd.to_datetime(df_completo['Data'] + ' ' + df_completo['Hora'], 
                                                format='%d/%m/%Y %H:%M', errors='coerce')
        df_completo = df_completo.dropna(subset=['DateTime'])
        
        return df_completo
        
    except Exception as e:
        print(f"Erro ao carregar dados: {e}")
        # Criar dados de exemplo se falhar
        dates = pd.date_range(start='2025-09-01', end='2025-09-30', freq='H')[:100]
        return pd.DataFrame({
            'DateTime': dates,
            'Valor_Limpo': np.random.uniform(5, 50, 100),
            'Metodo': np.random.choice(['PIX', 'Crédito', 'Débito'], 100)
        })

# Inicializar app
app = dash.Dash(__name__)
app.title = "Dashboard Vendas - Pastelaria Vinny"

# Carregar dados
df = carregar_dados()

# Layout
app.layout = html.Div([
    html.H1("🥟 Dashboard Pastelaria Vinny Navegantes", 
            style={'textAlign': 'center', 'color': '#2c3e50', 'marginBottom': '30px'}),
    
    # KPIs
    html.Div([
        html.Div([
            html.H2(f"{len(df):,}", style={'color': '#3498db', 'margin': '0', 'fontSize': '2.5em'}),
            html.P("Transações", style={'margin': '0', 'fontSize': '1.2em'})
        ], style={'textAlign': 'center', 'backgroundColor': 'white', 'padding': '30px', 
                 'borderRadius': '15px', 'boxShadow': '0 4px 8px rgba(0,0,0,0.1)', 'flex': '1'}),
        
        html.Div([
            html.H2(f"R$ {df['Valor_Limpo'].sum():,.0f}", style={'color': '#27ae60', 'margin': '0', 'fontSize': '2.5em'}),
            html.P("Faturamento", style={'margin': '0', 'fontSize': '1.2em'})
        ], style={'textAlign': 'center', 'backgroundColor': 'white', 'padding': '30px', 
                 'borderRadius': '15px', 'boxShadow': '0 4px 8px rgba(0,0,0,0.1)', 'flex': '1'}),
        
        html.Div([
            html.H2(f"R$ {df['Valor_Limpo'].mean():.0f}", style={'color': '#e74c3c', 'margin': '0', 'fontSize': '2.5em'}),
            html.P("Ticket Médio", style={'margin': '0', 'fontSize': '1.2em'})
        ], style={'textAlign': 'center', 'backgroundColor': 'white', 'padding': '30px', 
                 'borderRadius': '15px', 'boxShadow': '0 4px 8px rgba(0,0,0,0.1)', 'flex': '1'})
        
    ], style={'display': 'flex', 'gap': '20px', 'marginBottom': '40px'}),
    
    # Gráficos
    html.Div([
        dcc.Graph(id='grafico-metodos', style={'flex': '1'}),
        dcc.Graph(id='grafico-temporal', style={'flex': '1'})
    ], style={'display': 'flex', 'gap': '20px', 'marginBottom': '20px'}),
    
    html.Div([
        dcc.Graph(id='grafico-horarios', style={'flex': '1'}),
        dcc.Graph(id='grafico-valores', style={'flex': '1'})
    ], style={'display': 'flex', 'gap': '20px'})
    
], style={'padding': '30px', 'backgroundColor': '#f8f9fa', 'minHeight': '100vh'})

# Callback para gráficos
@app.callback(
    [Output('grafico-metodos', 'figure'),
     Output('grafico-temporal', 'figure'),
     Output('grafico-horarios', 'figure'),
     Output('grafico-valores', 'figure')],
    [Input('grafico-metodos', 'id')]  # Trigger simples
)
def atualizar_graficos(_):
    # 1. Vendas por método
    metodos_data = df.groupby('Metodo')['Valor_Limpo'].agg(['count', 'sum']).reset_index()
    fig_metodos = go.Figure(data=[
        go.Pie(labels=metodos_data['Metodo'], values=metodos_data['sum'], hole=0.4)
    ])
    fig_metodos.update_layout(title='💳 Faturamento por Método', height=400)
    
    # 2. Evolução temporal
    df['Data'] = df['DateTime'].dt.date
    temporal_data = df.groupby('Data')['Valor_Limpo'].sum().reset_index()
    fig_temporal = go.Figure()
    fig_temporal.add_trace(go.Scatter(
        x=temporal_data['Data'], y=temporal_data['Valor_Limpo'],
        mode='lines+markers', line=dict(color='#3498db', width=3)
    ))
    fig_temporal.update_layout(title='📈 Faturamento Diário', height=400)
    
    # 3. Vendas por hora
    df['Hora'] = df['DateTime'].dt.hour
    hora_data = df.groupby('Hora').size().reset_index(name='Count')
    fig_horarios = go.Figure()
    fig_horarios.add_trace(go.Bar(x=hora_data['Hora'], y=hora_data['Count'], marker_color='#2ecc71'))
    fig_horarios.update_layout(title='🕐 Transações por Horário', height=400)
    
    # 4. Distribuição de valores
    fig_valores = go.Figure()
    fig_valores.add_trace(go.Histogram(x=df['Valor_Limpo'], nbinsx=20, marker_color='#e74c3c'))
    fig_valores.update_layout(title='💰 Distribuição de Valores', height=400)
    
    return fig_metodos, fig_temporal, fig_horarios, fig_valores

if __name__ == '__main__':
    print("🚀 Iniciando Dashboard Simplificado...")
    print("📊 Acesse: http://localhost:8050")
    print("⚠️  Para parar: Ctrl+C")
    app.run(debug=True, host='0.0.0.0', port=8050)