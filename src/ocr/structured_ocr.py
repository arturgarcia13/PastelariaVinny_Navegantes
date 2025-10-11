import cv2
from PIL import Image
import pytesseract
from pathlib import Path
import json
import re
import os
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Optional

# Configuração automática do Tesseract para Windows
def setup_tesseract():
    """Configura o caminho do Tesseract automaticamente"""
    possible_paths = [
        r'C:\Program Files\Tesseract-OCR\tesseract.exe',
        r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe',
        r'C:\Users\AppData\Local\Programs\Tesseract-OCR\tesseract.exe',
        r'C:\tesseract\tesseract.exe',
        'tesseract'  # Se estiver no PATH
    ]
    
    for path in possible_paths:
        try:
            if path == 'tesseract':
                # Testa se está no PATH
                import subprocess
                result = subprocess.run(['tesseract', '--version'], 
                                      capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return True
            else:
                if os.path.exists(path):
                    pytesseract.pytesseract.tesseract_cmd = path
                    print(f"✅ Tesseract encontrado em: {path}")
                    return True
        except Exception:
            continue
    
    return False

# Tenta configurar o Tesseract automaticamente
if not setup_tesseract():
    print("⚠️  Tesseract não encontrado automaticamente!")
    print("Por favor, instale o Tesseract OCR ou configure manualmente:")
    print("1. Baixe em: https://github.com/UB-Mannheim/tesseract/wiki")
    print("2. Ou defina: pytesseract.pytesseract.tesseract_cmd = 'caminho/para/tesseract.exe'")
    
    # Permite configuração manual
    manual_path = input("Digite o caminho para tesseract.exe (ou Enter para tentar continuar): ").strip()
    if manual_path and os.path.exists(manual_path):
        pytesseract.pytesseract.tesseract_cmd = manual_path
        print(f"✅ Tesseract configurado para: {manual_path}")
    else:
        print("⚠️  Continuando sem configuração específica...")

def test_tesseract():
    """Testa se o Tesseract está funcionando corretamente"""
    try:
        # Cria uma imagem de teste simples
        import numpy as np
        from PIL import Image
        
        # Imagem de teste com texto simples
        test_img = np.ones((100, 300, 3), dtype=np.uint8) * 255
        test_pil = Image.fromarray(test_img)
        
        # Testa OCR básico
        _ = pytesseract.image_to_string(test_pil)
        print("✅ Tesseract está funcionando!")
        return True
        
    except pytesseract.TesseractNotFoundError:
        print("❌ Tesseract não foi encontrado no sistema!")
        print("   Instale o Tesseract OCR de: https://github.com/UB-Mannheim/tesseract/wiki")
        return False
    except Exception as e:
        print(f"❌ Erro ao testar Tesseract: {str(e)}")
        return False


@dataclass
class TransactionData:
    """Estrutura para dados de uma transação"""
    quadrant_number: int
    raw_text: str
    processed_text: str
    confidence: float = 0.0
    timestamp: Optional[str] = None
    amount: Optional[str] = None
    description: Optional[str] = None


@dataclass
class DayData:
    """Estrutura para dados de um dia completo"""
    day_folder: str
    date_info: str
    header_text: str
    transactions: List[TransactionData]
    total_quadrants: int
    processing_timestamp: str


class AdvancedOCR:
    """Sistema avançado de OCR com múltiplas estratégias"""
    
    def __init__(self, chunk_height=1200, overlap=100):
        self.chunk_height = chunk_height
        self.overlap = overlap
    
    def enhance_image_for_ocr(self, image_path):
        """Melhora a imagem para OCR"""
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Não foi possível carregar a imagem: {image_path}")
        
        # Converte para escala de cinza
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Redimensiona se muito grande (mantém proporção)
        height, width = gray.shape
        if width > 2000:
            scale = 2000 / width
            new_width = int(width * scale)
            new_height = int(height * scale)
            gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
        
        # Aplica denoising
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # Melhora contraste
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(denoised)
        
        # Binarização adaptativa
        binary = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        return binary
    
    def split_image_vertically(self, image, chunk_height=None):
        """Divide a imagem em pedaços verticais com sobreposição"""
        if chunk_height is None:
            chunk_height = self.chunk_height
            
        height, width = image.shape[:2]
        chunks = []
        y = 0
        
        while y < height:
            y_end = min(y + chunk_height, height)
            chunk = image[y:y_end, 0:width]
            chunks.append((chunk, y, y_end))
            
            y += chunk_height - self.overlap
            if y_end >= height:
                break
        
        return chunks
    
    def process_image_with_chunking(self, image_path, strategy='hybrid'):
        """Processa imagem usando estratégia de chunking"""
        # Pré-processamento
        processed_img = self.enhance_image_for_ocr(image_path)
        
        # Divide em chunks
        chunks = self.split_image_vertically(processed_img)
        full_text = ""
        
        for i, (chunk, y_start, y_end) in enumerate(chunks):
            # Converte para PIL Image
            chunk_pil = Image.fromarray(chunk)
            
            # Aplica OCR com configurações otimizadas
            custom_config = r'--oem 3 --psm 6 -l por'
            text = pytesseract.image_to_string(chunk_pil, config=custom_config)
            
            # Remove duplicatas na sobreposição (básico)
            if i > 0 and full_text:
                # Remove as primeiras linhas se muito similares ao final anterior
                text_lines = text.split('\n')
                if len(text_lines) > 3:
                    text = '\n'.join(text_lines[2:])
            
            full_text += text + "\n"
        
        return full_text.strip()
    
    def extract_text_with_confidence(self, image_path):
        """Extrai texto com informações de confiança"""
        try:
            processed_img = self.enhance_image_for_ocr(image_path)
            pil_img = Image.fromarray(processed_img)
            
            # Tenta diferentes configurações de OCR
            configs = [
                r'--oem 3 --psm 6',  # Sem especificar idioma primeiro
                r'--oem 3 --psm 6 -l por',
                r'--oem 3 --psm 3',
                r'--oem 1 --psm 6'
            ]
            
            for config in configs:
                try:
                    # OCR com dados de confiança
                    data = pytesseract.image_to_data(pil_img, config=config, 
                                                   output_type=pytesseract.Output.DICT)
                    
                    # Calcula confiança média
                    confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                    avg_confidence = sum(confidences) / len(confidences) if confidences else 0
                    
                    # Se obteve confiança razoável, extrai texto
                    if avg_confidence > 30 or config == configs[-1]:  # Usa última config como fallback
                        text = pytesseract.image_to_string(pil_img, config=config)
                        return text.strip(), avg_confidence
                        
                except pytesseract.TesseractError as te:
                    if config == configs[-1]:  # Se é a última tentativa
                        print(f"Erro do Tesseract: {str(te)}")
                        # Tenta sem configuração específica
                        try:
                            text = pytesseract.image_to_string(pil_img)
                            return text.strip(), 50.0  # Confiança estimada
                        except Exception:
                            return f"ERRO TESSERACT: {str(te)}", 0.0
                    continue
                except Exception as e:
                    if config == configs[-1]:
                        print(f"Erro geral no OCR: {str(e)}")
                        return f"ERRO: {str(e)}", 0.0
                    continue
            
            return "", 0.0
            
        except Exception as e:
            print(f"Erro crítico no OCR de {image_path}: {str(e)}")
            return f"ERRO CRÍTICO: {str(e)}", 0.0


class StructuredTransactionOCR:
    """Sistema principal de OCR estruturado para transações organizadas por dia"""
    
    def __init__(self, base_folder_path, output_folder=None):
        self.base_folder = Path(base_folder_path)
        self.output_folder = Path(output_folder) if output_folder else self.base_folder.parent / "processed"
        self.ocr_engine = AdvancedOCR()
        
        # Cria pasta de saída
        self.output_folder.mkdir(exist_ok=True)
        
        # Padrões regex para extrair informações
        self.date_patterns = [
            r'\d{1,2}\s+\w{3,4}\.?\s+\d{4}',  # 29 set. 2025 ou 29 set 2025
            r'\d{1,2}[/-]\d{1,2}[/-]\d{4}',
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',
            r'\d{1,2}\s+de\s+\w+\s+de\s+\d{4}',
        ]
        
        self.amount_patterns = [
            r'R\$\s*[\d.,]+',
            r'[\d.,]+\s*reais?',
            r'\$\s*[\d.,]+',
        ]
    
    def extract_day_folders(self):
        """Extrai todas as pastas de dias (pix (x))"""
        if not self.base_folder.exists():
            raise FileNotFoundError(f"Pasta base não encontrada: {self.base_folder}")
        
        # Procura por pastas com padrão "pix (numero)"
        day_folders = []
        for folder in self.base_folder.iterdir():
            if folder.is_dir() and folder.name.startswith('pix (') and folder.name.endswith(')'):
                day_folders.append(folder)
        
        # Ordena numericamente
        day_folders.sort(key=lambda x: int(re.search(r'\((\d+)\)', x.name).group(1)))
        
        return day_folders
    
    def get_quadrant_images(self, day_folder):
        """Obtém todas as imagens de quadrantes de um dia, ordenadas"""
        images = []
        
        for img_file in day_folder.glob("*.jpg"):
            if "quadrante" in img_file.name:
                # Extrai número do quadrante
                match = re.search(r'quadrante_(\d+)', img_file.name)
                if match:
                    quadrant_num = int(match.group(1))
                    images.append((quadrant_num, img_file))
        
        # Ordena por número do quadrante
        images.sort(key=lambda x: x[0])
        
        return images
    
    def extract_date_info(self, text):
        """Extrai informações de data do texto"""
        for pattern in self.date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0]
        return None
    
    def extract_amounts(self, text):
        """Extrai valores monetários do texto"""
        amounts = []
        for pattern in self.amount_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            amounts.extend(matches)
        return amounts
    
    def clean_and_process_text(self, raw_text):
        """Limpa e processa o texto extraído"""
        if not raw_text:
            return ""
        
        # Remove caracteres estranhos e normaliza espaços
        cleaned = re.sub(r'[^\w\s\.,\-\+\$R\(\)\/:]', ' ', raw_text)
        cleaned = re.sub(r'\s+', ' ', cleaned)
        cleaned = cleaned.strip()
        
        return cleaned
    
    def process_single_quadrant(self, quadrant_num, image_path):
        """Processa um único quadrante"""
        print(f"    📋 Processando quadrante {quadrant_num:02d}...")
        
        try:
            # Extrai texto com confiança
            raw_text, confidence = self.ocr_engine.extract_text_with_confidence(str(image_path))
            
            # Processa o texto
            processed_text = self.clean_and_process_text(raw_text)
            
            # Extrai informações estruturadas
            date_info = self.extract_date_info(processed_text)
            amounts = self.extract_amounts(processed_text)
            
            # Cria objeto de transação
            transaction = TransactionData(
                quadrant_number=quadrant_num,
                raw_text=raw_text,
                processed_text=processed_text,
                confidence=confidence,
                timestamp=date_info,
                amount=amounts[0] if amounts else None,
                description=processed_text[:200] + "..." if len(processed_text) > 200 else processed_text
            )
            
            print(f"       Confiança: {confidence:.1f}% | Chars: {len(processed_text)}")
            
            return transaction
            
        except Exception as e:
            print(f"       ❌ Erro: {str(e)}")
            return TransactionData(
                quadrant_number=quadrant_num,
                raw_text="",
                processed_text=f"ERRO: {str(e)}",
                confidence=0.0
            )
    
    def process_single_day(self, day_folder):
        """Processa todas as transações de um único dia"""
        print(f"\n📅 Processando dia: {day_folder.name}")
        
        # Obtém todas as imagens do dia
        quadrant_images = self.get_quadrant_images(day_folder)
        
        if not quadrant_images:
            print(f"   ❌ Nenhuma imagem encontrada em {day_folder}")
            return None
        
        print(f"   📦 Encontrados {len(quadrant_images)} quadrantes")
        
        # Processa primeira imagem (cabeçalho do dia)
        first_quadrant_num, first_image = quadrant_images[0]
        print(f"   🏷️  Processando cabeçalho (quadrante {first_quadrant_num})...")
        
        header_text, header_confidence = self.ocr_engine.extract_text_with_confidence(str(first_image))
        header_processed = self.clean_and_process_text(header_text)
        date_info = self.extract_date_info(header_processed) or "Data não identificada"
        
        print(f"      Data identificada: {date_info}")
        print(f"      Confiança: {header_confidence:.1f}%")
        
        # Processa demais quadrantes (transações)
        transactions = []
        
        for quadrant_num, image_path in quadrant_images[1:]:  # Pula o primeiro
            transaction = self.process_single_quadrant(quadrant_num, image_path)
            transactions.append(transaction)
        
        # Cria objeto do dia
        day_data = DayData(
            day_folder=day_folder.name,
            date_info=date_info,
            header_text=header_processed,
            transactions=transactions,
            total_quadrants=len(quadrant_images),
            processing_timestamp=datetime.now().isoformat()
        )
        
        print(f"   ✅ Dia processado: {len(transactions)} transações")
        
        return day_data
    
    def save_day_data(self, day_data, format='json'):
        """Salva dados de um dia em arquivo"""
        if format == 'json':
            output_file = self.output_folder / f"{day_data.day_folder}_data.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(day_data), f, ensure_ascii=False, indent=2)
            
            print(f"   💾 Dados salvos em: {output_file}")
        
        elif format == 'txt':
            output_file = self.output_folder / f"{day_data.day_folder}_data.txt"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(f"=== {day_data.day_folder.upper()} ===\n")
                f.write(f"Data: {day_data.date_info}\n")
                f.write(f"Processado em: {day_data.processing_timestamp}\n")
                f.write(f"Total de quadrantes: {day_data.total_quadrants}\n\n")
                
                f.write("CABEÇALHO DO DIA:\n")
                f.write("-" * 40 + "\n")
                f.write(f"{day_data.header_text}\n\n")
                
                f.write("TRANSAÇÕES:\n")
                f.write("-" * 40 + "\n")
                
                for i, transaction in enumerate(day_data.transactions, 1):
                    f.write(f"\nTransação {i} (Quadrante {transaction.quadrant_number}):\n")
                    f.write(f"Confiança: {transaction.confidence:.1f}%\n")
                    if transaction.amount:
                        f.write(f"Valor: {transaction.amount}\n")
                    if transaction.timestamp:
                        f.write(f"Timestamp: {transaction.timestamp}\n")
                    f.write(f"Texto:\n{transaction.processed_text}\n")
                    f.write("-" * 20 + "\n")
            
            print(f"   📄 Relatório salvo em: {output_file}")
        
        return output_file
    
    def process_all_days(self, save_format='both'):
        """Processa todos os dias disponíveis"""
        print("🚀 Iniciando processamento estruturado de OCR")
        print("=" * 60)
        
        # Obtém todas as pastas de dias
        day_folders = self.extract_day_folders()
        
        if not day_folders:
            print("❌ Nenhuma pasta de dia encontrada!")
            return []
        
        print(f"📁 Encontradas {len(day_folders)} pastas de dias para processar")
        
        all_days_data = []
        successful_days = 0
        
        for day_folder in day_folders:
            try:
                day_data = self.process_single_day(day_folder)
                
                if day_data:
                    all_days_data.append(day_data)
                    successful_days += 1
                    
                    # Salva dados do dia
                    if save_format in ['json', 'both']:
                        self.save_day_data(day_data, 'json')
                    
                    if save_format in ['txt', 'both']:
                        self.save_day_data(day_data, 'txt')
                
            except Exception as e:
                print(f"❌ Erro ao processar {day_folder.name}: {str(e)}")
        
        # Salva resumo geral
        self.save_summary_report(all_days_data)
        
        print("\n" + "=" * 60)
        print("🎉 Processamento concluído!")
        print(f"✅ {successful_days} dias processados com sucesso")
        print(f"❌ {len(day_folders) - successful_days} dias falharam")
        print(f"📁 Resultados salvos em: {self.output_folder}")
        
        return all_days_data
    
    def save_summary_report(self, all_days_data):
        """Salva relatório resumo de todos os dias"""
        summary_file = self.output_folder / "resumo_geral.txt"
        
        with open(summary_file, 'w', encoding='utf-8') as f:
            f.write("RELATÓRIO RESUMO - TRANSAÇÕES POR DIA\n")
            f.write("=" * 50 + "\n")
            f.write(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"Total de dias processados: {len(all_days_data)}\n\n")
            
            for day_data in all_days_data:
                f.write(f"📅 {day_data.day_folder} - {day_data.date_info}\n")
                f.write(f"   Transações: {len(day_data.transactions)}\n")
                f.write(f"   Quadrantes: {day_data.total_quadrants}\n")
                
                # Confiança média
                confidences = [t.confidence for t in day_data.transactions if t.confidence > 0]
                avg_conf = sum(confidences) / len(confidences) if confidences else 0
                f.write(f"   Confiança média: {avg_conf:.1f}%\n")
                
                # Valores encontrados
                amounts = [t.amount for t in day_data.transactions if t.amount]
                if amounts:
                    f.write(f"   Valores encontrados: {len(amounts)}\n")
                
                f.write("\n")
        
        print(f"📊 Resumo geral salvo em: {summary_file}")


# Funções de conveniência
def process_transactions_quick(base_folder, output_folder=None, save_format='both'):
    """Função rápida para processar transações"""
    processor = StructuredTransactionOCR(base_folder, output_folder)
    return processor.process_all_days(save_format)


def preview_day_structure(base_folder, day_name=None):
    """Visualiza a estrutura de um dia específico"""
    processor = StructuredTransactionOCR(base_folder)
    day_folders = processor.extract_day_folders()
    
    if day_name:
        # Procura dia específico
        target_folder = None
        for folder in day_folders:
            if folder.name == day_name:
                target_folder = folder
                break
        
        if not target_folder:
            print(f"❌ Dia '{day_name}' não encontrado!")
            return
        
        day_folders = [target_folder]
    
    print("📊 ESTRUTURA DOS DIAS:")
    print("=" * 40)
    
    for folder in day_folders[:3]:  # Mostra apenas os 3 primeiros
        quadrants = processor.get_quadrant_images(folder)
        print(f"\n📁 {folder.name}:")
        print(f"   📦 {len(quadrants)} quadrantes encontrados")
        
        for i, (num, img_path) in enumerate(quadrants[:5]):  # Mostra apenas os 5 primeiros
            if i == 0:
                print(f"   🏷️  Quadrante {num:02d}: {img_path.name} (CABEÇALHO)")
            else:
                print(f"   📋 Quadrante {num:02d}: {img_path.name}")
        
        if len(quadrants) > 5:
            print(f"   ... e mais {len(quadrants) - 5} quadrantes")


if __name__ == "__main__":
    # Configuração padrão
    BASE_FOLDER = r"data\raw\Imagens\cropped_images\quadrantes"
    OUTPUT_FOLDER = r"outputs\ocr_results"
    
    print("🔍 Sistema de OCR Estruturado para Transações")
    print("=" * 50)
    
    # Testa o Tesseract antes de continuar
    print("\n🔧 Testando configuração do Tesseract...")
    if not test_tesseract():
        print("\n❌ Tesseract não está configurado corretamente!")
        print("Para resolver:")
        print("1. Instale Tesseract: https://github.com/UB-Mannheim/tesseract/wiki")
        print("2. Ou configure o caminho manualmente no código")
        
        continuar = input("\nDeseja continuar mesmo assim? (s/n): ")
        if continuar.lower() != 's':
            exit(1)
    
    print("\n" + "=" * 50)
    
    choice = input("""
Escolha uma opção:
1 - Processar todos os dias (formato JSON + TXT)
2 - Processar todos os dias (apenas JSON)
3 - Processar todos os dias (apenas TXT)
4 - Visualizar estrutura dos dias
5 - Configuração personalizada

Digite sua opção (1-5): """)
    
    try:
        if choice == "1":
            process_transactions_quick(BASE_FOLDER, OUTPUT_FOLDER, 'both')
        
        elif choice == "2":
            process_transactions_quick(BASE_FOLDER, OUTPUT_FOLDER, 'json')
        
        elif choice == "3":
            process_transactions_quick(BASE_FOLDER, OUTPUT_FOLDER, 'txt')
        
        elif choice == "4":
            preview_day_structure(BASE_FOLDER)
        
        elif choice == "5":
            base_path = input(f"Pasta base ({BASE_FOLDER}): ") or BASE_FOLDER
            output_path = input(f"Pasta saída ({OUTPUT_FOLDER}): ") or OUTPUT_FOLDER
            format_choice = input("Formato (json/txt/both): ") or 'both'
            
            process_transactions_quick(base_path, output_path, format_choice)
        
        else:
            print("❌ Opção inválida!")
    
    except Exception as e:
        print(f"❌ Erro: {str(e)}")