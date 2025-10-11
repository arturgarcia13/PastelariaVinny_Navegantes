"""
Script para instalar e configurar Tesseract OCR no Windows
"""
import os
import sys
import subprocess
from pathlib import Path
import urllib.request
import zipfile


def check_tesseract_installed():
    """Verifica se o Tesseract já está instalado"""
    possible_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        r'C:\Users\AppData\Local\Programs\Tesseract-OCR\tesseract.exe',
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            print(f"✅ Tesseract encontrado em: {path}")
            return path
    
    # Testa se está no PATH
    try:
        result = subprocess.run(['tesseract', '--version'], 
                              capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            print("✅ Tesseract encontrado no PATH do sistema")
            return 'tesseract'
    except Exception:
        pass
    
    return None


def download_tesseract_installer():
    """Baixa o instalador do Tesseract"""
    print("📥 Baixando instalador do Tesseract...")
    
    # URL do instalador mais recente (64-bit)
    url = "https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.3.3.20231005.exe"
    installer_path = "tesseract_installer.exe"
    
    try:
        urllib.request.urlretrieve(url, installer_path)
        print(f"✅ Instalador baixado: {installer_path}")
        return installer_path
    except Exception as e:
        print(f"❌ Erro ao baixar: {str(e)}")
        return None


def install_tesseract_manual():
    """Guia para instalação manual do Tesseract"""
    print("\n📖 GUIA DE INSTALAÇÃO MANUAL DO TESSERACT:")
    print("=" * 50)
    print("1. Acesse: https://github.com/UB-Mannheim/tesseract/wiki")
    print("2. Baixe o instalador para Windows (64-bit)")
    print("3. Execute o instalador como Administrador")
    print("4. Durante a instalação, certifique-se de instalar:")
    print("   - Tesseract OCR Engine")
    print("   - Portuguese language data (por.traineddata)")
    print("5. Anote o caminho de instalação (geralmente C:\\Program Files\\Tesseract-OCR)")
    print("\nApós a instalação, execute novamente este script.")


def configure_python_tesseract(tesseract_path):
    """Configura o pytesseract com o caminho correto"""
    config_lines = [
        "# Configuração automática do Tesseract",
        "import pytesseract",
        f"pytesseract.pytesseract.tesseract_cmd = r'{tesseract_path}'",
        ""
    ]
    
    config_file = Path("tesseract_config.py")
    
    with open(config_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(config_lines))
    
    print(f"✅ Arquivo de configuração criado: {config_file}")
    print("   Importe este arquivo no seu código Python")


def test_tesseract_installation():
    """Testa a instalação do Tesseract"""
    try:
        import pytesseract
        from PIL import Image
        import numpy as np
        
        # Cria imagem de teste
        test_img = np.ones((50, 200, 3), dtype=np.uint8) * 255
        test_pil = Image.fromarray(test_img)
        
        # Testa OCR
        result = pytesseract.image_to_string(test_pil)
        print("✅ Tesseract funcionando corretamente!")
        return True
        
    except Exception as e:
        print(f"❌ Erro no teste: {str(e)}")
        return False


def main():
    print("🔧 Configurador Automático do Tesseract OCR")
    print("=" * 45)
    
    # Verifica se já está instalado
    tesseract_path = check_tesseract_installed()
    
    if tesseract_path:
        print("\n✅ Tesseract já está instalado!")
        
        # Configura o Python
        if tesseract_path != 'tesseract':
            configure_python_tesseract(tesseract_path)
        
        # Testa instalação
        if test_tesseract_installation():
            print("\n🎉 Tudo configurado corretamente!")
        else:
            print("\n⚠️  Instalação encontrada mas há problemas na configuração")
            
    else:
        print("\n❌ Tesseract não encontrado no sistema")
        
        choice = input("""
Escolha uma opção:
1 - Tentar baixar e instalar automaticamente
2 - Guia para instalação manual
3 - Configurar caminho manualmente

Digite sua opção (1-3): """)
        
        if choice == "1":
            installer = download_tesseract_installer()
            if installer:
                print(f"\n📋 Execute o arquivo {installer} como Administrador")
                print("   Após a instalação, execute novamente este script")
            else:
                install_tesseract_manual()
                
        elif choice == "2":
            install_tesseract_manual()
            
        elif choice == "3":
            manual_path = input("Digite o caminho completo para tesseract.exe: ").strip()
            if os.path.exists(manual_path):
                configure_python_tesseract(manual_path)
                print("✅ Configuração salva!")
            else:
                print("❌ Caminho não encontrado!")
        
        else:
            print("❌ Opção inválida!")


if __name__ == "__main__":
    main()