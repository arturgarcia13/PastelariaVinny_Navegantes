import cv2
import numpy as np
from PIL import Image
import pytesseract
from pathlib import Path
import os
import shutil
from datetime import datetime


class RawTextExtractor:
    """Extrator simples de texto bruto das imagens sem processamento adicional"""
    
    def __init__(self, images_folder, output_folder=None):
        self.images_folder = Path(images_folder)
        self.output_folder = Path(output_folder) if output_folder else Path("outputs/raw_text")
        
        # Cria pasta de saída
        self.output_folder.mkdir(parents=True, exist_ok=True)
        
        # Configura Tesseract
        self._setup_tesseract()
    
    def _setup_tesseract(self):
        """Configura o caminho do Tesseract automaticamente"""
        # Caminhos comuns do Tesseract no Windows
        possible_paths = [
            r'C:\Program Files\Tesseract-OCR\tesseract.exe',
            r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
            r'C:\Users\{}\AppData\Local\Tesseract-OCR\tesseract.exe'.format(os.getenv('USERNAME', '')),
            r'C:\tesseract\tesseract.exe',
        ]
        
        # Tenta encontrar Tesseract no PATH
        tesseract_path = shutil.which('tesseract')
        if tesseract_path:
            pytesseract.pytesseract.tesseract_cmd = tesseract_path
            print(f"✅ Tesseract encontrado no PATH: {tesseract_path}")
            return
        
        # Tenta caminhos comuns
        for path in possible_paths:
            if Path(path).exists():
                pytesseract.pytesseract.tesseract_cmd = path
                print(f"✅ Tesseract encontrado em: {path}")
                return
        
        print("⚠️  Tesseract não encontrado automaticamente.")
    
    def test_tesseract(self) -> bool:
        """Testa se o Tesseract está funcionando"""
        try:
            test_img = Image.new('RGB', (100, 30), color='white')
            pytesseract.image_to_string(test_img)
            return True
        except Exception as e:
            print(f"❌ Erro no teste do Tesseract: {str(e)}")
            return False
    
    def enhance_image_basic(self, image_path: str) -> np.ndarray:
        """Pré-processamento básico da imagem"""
        # Carrega imagem
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Não foi possível carregar a imagem: {image_path}")
        
        # Converte para escala de cinza
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Redimensiona se muito grande
        height, width = gray.shape
        max_width = 2000
        if width > max_width:
            scale = max_width / width
            new_width = int(width * scale)
            new_height = int(height * scale)
            gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
        
        # Melhoria básica de contraste
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        
        return enhanced
    
    def extract_raw_text(self, image_path: str) -> tuple[str, float, dict]:
        """Extrai texto bruto da imagem com informações de confiança"""
        try:
            # Pré-processamento básico
            processed_img = self.enhance_image_basic(image_path)
            pil_img = Image.fromarray(processed_img)
            
            # Configurações diferentes do Tesseract para testar
            configs = {
                'config1': r'--oem 3 --psm 6 -l por',  # Padrão
                # 'config2': r'--oem 3 --psm 3 -l por',  # Processamento de página completa
                # 'config3': r'--oem 3 --psm 4 -l por',  # Coluna de texto
                # 'config4': r'--oem 1 --psm 6 -l por',  # Engine diferente
            }
            
            results = {}
            best_text = ""
            best_confidence = 0.0
            
            for config_name, config in configs.items():
                try:
                    # Extrai texto
                    text = pytesseract.image_to_string(pil_img, config=config)
                    
                    # Calcula confiança
                    try:
                        data = pytesseract.image_to_data(pil_img, config=config, output_type=pytesseract.Output.DICT)
                        confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                        avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                    except Exception:
                        avg_confidence = 0.0
                    
                    results[config_name] = {
                        'text': text.strip(),
                        'confidence': avg_confidence,
                        'char_count': len(text.strip())
                    }
                    
                    # Guarda o melhor resultado
                    if avg_confidence > best_confidence:
                        best_confidence = avg_confidence
                        best_text = text.strip()
                
                except Exception as e:
                    results[config_name] = {
                        'text': f"ERRO: {str(e)}",
                        'confidence': 0.0,
                        'char_count': 0
                    }
            
            return best_text, best_confidence, results
            
        except Exception as e:
            error_msg = f"ERRO GERAL: {str(e)}"
            return error_msg, 0.0, {'error': {'text': error_msg, 'confidence': 0.0, 'char_count': 0}}
    
    def get_image_info(self, image_path: Path) -> dict:
        """Obtém informações básicas da imagem"""
        try:
            img = cv2.imread(str(image_path))
            if img is not None:
                height, width = img.shape[:2]
                file_size = image_path.stat().st_size / 1024  # KB
                return {
                    'width': width,
                    'height': height,
                    'file_size_kb': round(file_size, 2)
                }
        except Exception:
            pass
        
        return {'width': 0, 'height': 0, 'file_size_kb': 0}
    
    def process_single_image(self, image_path: Path) -> dict:
        """Processa uma única imagem e salva texto bruto"""
        print(f"🔄 Processando: {image_path.name}")
        
        # Informações da imagem
        img_info = self.get_image_info(image_path)
        
        # Extrai texto
        text, confidence, all_results = self.extract_raw_text(str(image_path))
        
        # Identifica tipo (crédito/débito)
        image_type = "credito" if "credito" in image_path.name.lower() else "debito"
        
        # Informações do processamento
        result_info = {
            'filename': image_path.name,
            'type': image_type,
            'image_info': img_info,
            'best_confidence': confidence,
            'text_length': len(text),
            'processing_time': datetime.now().isoformat(),
            'all_configs': all_results
        }
        
        # Nome do arquivo de saída
        output_name = image_path.stem + "_raw.txt"
        output_path = self.output_folder / output_name
        
        # Salva texto bruto
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(f"=== {image_path.name} ===\n")
            f.write(f"Tipo: {image_type.title()}\n")
            f.write(f"Dimensões: {img_info['width']}x{img_info['height']}\n")
            f.write(f"Tamanho: {img_info['file_size_kb']} KB\n")
            f.write(f"Processado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"Melhor confiança: {confidence:.1f}%\n")
            f.write(f"Caracteres extraídos: {len(text)}\n")
            f.write("\n" + "="*50 + "\n")
            f.write("TEXTO EXTRAÍDO (MELHOR RESULTADO):\n")
            f.write("="*50 + "\n\n")
            f.write(text)
            f.write("\n\n" + "="*50 + "\n")
            f.write("RESULTADOS DE TODAS AS CONFIGURAÇÕES:\n")
            f.write("="*50 + "\n\n")
            
            for config_name, result in all_results.items():
                f.write(f"--- {config_name.upper()} ---\n")
                f.write(f"Confiança: {result['confidence']:.1f}%\n")
                f.write(f"Caracteres: {result['char_count']}\n")
                f.write(f"Texto:\n{result['text']}\n\n")
        
        print(f"   ✅ Confiança: {confidence:.1f}% | Chars: {len(text)} | Salvo: {output_name}")
        
        return result_info
    
    def get_all_images(self) -> list[Path]:
        """Obtém todas as imagens de crédito e débito"""
        if not self.images_folder.exists():
            raise FileNotFoundError(f"Pasta não encontrada: {self.images_folder}")
        
        image_files = []
        
        # Busca imagens de crédito e débito
        for pattern in ["credito (*).jpg", "debito (*).jpg", "credito (*).png", "debito (*).png"]:
            image_files.extend(self.images_folder.glob(pattern))
        
        # Ordena por tipo e número
        def sort_key(file_path):
            if 'credito' in file_path.name:
                tipo = 0
            else:
                tipo = 1
            
            # Extrai número
            import re
            match = re.search(r'\((\d+)\)', file_path.name)
            numero = int(match.group(1)) if match else 0
            
            return (tipo, numero)
        
        image_files.sort(key=sort_key)
        return image_files
    
    def extract_all_images(self) -> list[dict]:
        """Extrai texto de todas as imagens"""
        print("📄 Iniciando extração de texto bruto das imagens")
        print("=" * 60)
        
        # Testa Tesseract
        if not self.test_tesseract():
            print("❌ Tesseract não está funcionando! Abortando...")
            return []
        
        # Obtém imagens
        image_files = self.get_all_images()
        
        if not image_files:
            print("❌ Nenhuma imagem encontrada!")
            return []
        
        print(f"📁 Encontradas {len(image_files)} imagens para processar")
        print(f"📁 Pasta de saída: {self.output_folder}")
        print()
        
        results = []
        
        for image_file in image_files:
            try:
                result = self.process_single_image(image_file)
                results.append(result)
            except Exception as e:
                print(f"   ❌ Erro: {str(e)}")
                results.append({
                    'filename': image_file.name,
                    'error': str(e),
                    'processing_time': datetime.now().isoformat()
                })
            
            print()  # Linha em branco
        
        # Gera relatório resumo
        self.generate_summary_report(results)
        
        print("=" * 60)
        print(f"📊 Processamento concluído!")
        print(f"✅ {len([r for r in results if 'error' not in r])} imagens processadas com sucesso")
        print(f"❌ {len([r for r in results if 'error' in r])} imagens falharam")
        print(f"📁 Textos salvos em: {self.output_folder}")
        
        return results
    
    def generate_summary_report(self, results: list[dict]):
        """Gera relatório resumo do processamento"""
        summary_file = self.output_folder / "relatorio_extracao.txt"
        
        successful_results = [r for r in results if 'error' not in r]
        failed_results = [r for r in results if 'error' in r]
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("RELATÓRIO DE EXTRAÇÃO DE TEXTO BRUTO\n")
            f.write("=" * 50 + "\n")
            f.write(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
            
            f.write("📊 RESUMO GERAL:\n")
            f.write(f"   Total de imagens: {len(results)}\n")
            f.write(f"   Sucessos: {len(successful_results)}\n")
            f.write(f"   Falhas: {len(failed_results)}\n\n")
            
            if successful_results:
                # Estatísticas por tipo
                credito_count = len([r for r in successful_results if r.get('type') == 'credito'])
                debito_count = len([r for r in successful_results if r.get('type') == 'debito'])
                
                f.write("📂 POR TIPO:\n")
                f.write(f"   Crédito: {credito_count} imagens\n")
                f.write(f"   Débito: {debito_count} imagens\n\n")
                
                # Estatísticas de confiança
                confidences = [r.get('best_confidence', 0) for r in successful_results]
                if confidences:
                    f.write("📈 CONFIANÇA OCR:\n")
                    f.write(f"   Média: {sum(confidences)/len(confidences):.1f}%\n")
                    f.write(f"   Máxima: {max(confidences):.1f}%\n")
                    f.write(f"   Mínima: {min(confidences):.1f}%\n\n")
                
                # Lista detalhada
                f.write("📋 DETALHES POR ARQUIVO:\n")
                for result in successful_results:
                    f.write(f"   {result['filename']}: ")
                    f.write(f"{result.get('best_confidence', 0):.1f}% - ")
                    f.write(f"{result.get('text_length', 0)} chars - ")
                    f.write(f"{result.get('type', 'N/A').title()}\n")
            
            if failed_results:
                f.write(f"\n❌ FALHAS ({len(failed_results)}):\n")
                for result in failed_results:
                    f.write(f"   {result['filename']}: {result.get('error', 'Erro desconhecido')}\n")
        
        print(f"📊 Relatório resumo salvo: {summary_file}")


def extract_raw_text_quick(images_folder, output_folder=None):
    """Função rápida para extração de texto bruto"""
    extractor = RawTextExtractor(images_folder, output_folder)
    return extractor.extract_all_images()


if __name__ == "__main__":
    # Configurações padrão
    IMAGES_FOLDER = r"data\raw\Imagens\unprocessed"
    OUTPUT_FOLDER = r"outputs\raw_text"
    
    print("📄 Extrator de Texto Bruto - Etapa 1")
    print("=" * 50)
    
    choice = input("""
Escolha uma opção:
1 - Extrair texto de todas as imagens
2 - Testar configuração do Tesseract
3 - Configuração personalizada

Digite sua opção (1-3): """)
    
    try:
        if choice == "1":
            results = extract_raw_text_quick(IMAGES_FOLDER, OUTPUT_FOLDER)
            print(f"\n🎉 Extração concluída! Arquivos salvos em: {OUTPUT_FOLDER}")
        
        elif choice == "2":
            print("🔍 Testando configuração do Tesseract...")
            extractor = RawTextExtractor(IMAGES_FOLDER)
            if extractor.test_tesseract():
                print("✅ Tesseract está funcionando corretamente!")
            else:
                print("❌ Tesseract não está funcionando.")
        
        elif choice == "3":
            images_path = input(f"Pasta das imagens ({IMAGES_FOLDER}): ") or IMAGES_FOLDER
            output_path = input(f"Pasta de saída ({OUTPUT_FOLDER}): ") or OUTPUT_FOLDER
            
            results = extract_raw_text_quick(images_path, output_path)
            print(f"\n🎉 Extração concluída! Arquivos salvos em: {output_path}")
        
        else:
            print("❌ Opção inválida!")
    
    except Exception as e:
        print(f"❌ Erro durante a extração: {str(e)}")