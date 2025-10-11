#!/usr/bin/env python3
"""
Inicializador do Dashboard Streamlit
Pastelaria Vinny Navegantes
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    print("🥟" + "="*50)
    print("    DASHBOARD STREAMLIT - PASTELARIA VINNY")
    print("🥟" + "="*50)
    print()
    print("📊 Funcionalidades do Dashboard:")
    print("   • Análise completa de vendas em tempo real")
    print("   • Filtros interativos por método, período e valor")
    print("   • KPIs e métricas estratégicas")
    print("   • Visualizações dinâmicas com Plotly")
    print("   • Insights automatizados")
    print("   • Interface responsiva e intuitiva")
    print()
    print("🚀 Iniciando Streamlit...")
    print("🌐 O dashboard abrirá automaticamente no navegador")
    print("📍 URL: http://localhost:8501")
    print("⚠️  Para parar: Ctrl+C no terminal")
    print()
    
    # Determinar o caminho do Python no ambiente virtual
    project_path = Path(__file__).parent
    venv_python = project_path / ".venv" / "Scripts" / "python.exe"
    
    if not venv_python.exists():
        print("❌ Ambiente virtual não encontrado!")
        print("💡 Execute primeiro: poetry install")
        return
    
    # Executar Streamlit
    try:
        dashboard_path = project_path / "dashboard_streamlit.py"
        
        if not dashboard_path.exists():
            print("❌ Arquivo dashboard_streamlit.py não encontrado!")
            return
        
        cmd = [
            str(venv_python),
            "-m", "streamlit", "run", 
            str(dashboard_path),
            "--server.headless", "true",
            "--server.port", "8501"
        ]
        
        subprocess.run(cmd, check=True)
        
    except KeyboardInterrupt:
        print("\n👋 Dashboard encerrado pelo usuário.")
    except FileNotFoundError:
        print("❌ Streamlit não instalado!")
        print("💡 Execute: poetry add streamlit")
    except subprocess.CalledProcessError as e:
        print(f"❌ Erro ao executar dashboard: {e}")
        print("💡 Verifique se os arquivos de dados estão em:")
        print("   outputs/reports/transacoes_*.csv")
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")

if __name__ == "__main__":
    main()