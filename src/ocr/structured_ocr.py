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
        """Extrai texto com informações de confiança usando múltiplas estratégias e regiões"""
        try:
            processed_img = self.enhance_image_for_ocr(image_path)
            
            all_texts = []
            
            # Estratégia 1: Imagem completa
            pil_img = Image.fromarray(processed_img)
            texts_full = self._extract_with_multiple_configs(pil_img)
            all_texts.extend(texts_full)
            
            # Estratégia 2: Divide em regiões (topo, meio, fundo) para capturar texto perdido
            height, width = processed_img.shape
            regions = [
                (0, 0, width, height // 3),           # Região superior
                (0, height // 3, width, 2 * height // 3),  # Região central  
                (0, 2 * height // 3, width, height), # Região inferior
                (0, 0, width // 2, height),          # Lado esquerdo
                (width // 2, 0, width, height),      # Lado direito
            ]
            
            for x, y, x2, y2 in regions:
                region_img = processed_img[y:y2, x:x2]
                if region_img.size > 0:
                    region_pil = Image.fromarray(region_img)
                    region_texts = self._extract_with_multiple_configs(region_pil)
                    all_texts.extend(region_texts)
            
            # Estratégia 3: Tenta diferentes escalas
            for scale in [0.8, 1.2, 1.5]:
                try:
                    scaled_height = int(height * scale)
                    scaled_width = int(width * scale)
                    scaled_img = cv2.resize(processed_img, (scaled_width, scaled_height), 
                                          interpolation=cv2.INTER_CUBIC)
                    scaled_pil = Image.fromarray(scaled_img)
                    scaled_texts = self._extract_with_multiple_configs(scaled_pil)
                    all_texts.extend(scaled_texts)
                except Exception:
                    continue
            
            # Remove duplicatas e vazio
            unique_texts = []
            for text in all_texts:
                cleaned = text.strip()
                if cleaned and cleaned not in unique_texts:
                    unique_texts.append(cleaned)
            
            if unique_texts:
                # Combina todos os textos únicos
                combined_text = "\n".join(unique_texts)
                # Estima confiança baseada no número de fontes que encontraram texto
                estimated_confidence = min(90, 30 + (len(unique_texts) * 10))
                return combined_text, estimated_confidence
            
            return "", 0.0
            
        except Exception as e:
            print(f"Erro crítico no OCR de {image_path}: {str(e)}")
            return f"ERRO CRÍTICO: {str(e)}", 0.0
    
    def _extract_with_multiple_configs(self, pil_img):
        """Extrai texto usando múltiplas configurações do Tesseract"""
        configs = [
            r'--oem 3 --psm 6',      # Bloco uniforme de texto
            r'--oem 3 --psm 6 -l por',  # Com idioma português
            r'--oem 3 --psm 3',      # Página completamente automática
            r'--oem 3 --psm 4',      # Coluna de texto variável
            r'--oem 3 --psm 7',      # Linha de texto
            r'--oem 3 --psm 8',      # Uma palavra por vez
            r'--oem 3 --psm 13',     # Linha de texto crua
            r'--oem 1 --psm 6'       # OCR engine diferente
        ]
        
        texts = []
        
        for config in configs:
            try:
                text = pytesseract.image_to_string(pil_img, config=config)
                if text.strip():
                    texts.append(text.strip())
            except Exception:
                continue
        
        return texts


class StructuredTransactionOCR:
    """Sistema principal de OCR estruturado para transações organizadas por dia"""
    
    def __init__(self, base_folder_path, output_folder=None):
        self.base_folder = Path(base_folder_path)
        base_output_folder = Path(output_folder) if output_folder else self.base_folder.parent / "processed"
        self.ocr_engine = AdvancedOCR()
        
        # Extrai informações do caminho da pasta para nomenclatura dos arquivos
        self.path_info = self._extract_path_info()
        
        # Cria pasta de saída com subpasta do mês e tipo de transação
        self.output_folder = base_output_folder / self.path_info['month'] / self.path_info['transaction_type']
        self.output_folder.mkdir(parents=True, exist_ok=True)
        
        # Padrões regex para extrair informações
        self.date_patterns = [
            # Padrões específicos para meses abreviados em português
            r'\d{1,2}\.?\s*(?:jan|fev|mar|abr|mai|jun|jul|ago|set|out|nov|dez)\.?\s*\d{4}',  # 01. ago. 2025
            r'\d{1,2}\s+(?:janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro)\.?\s+\d{4}',
            r'\d{1,2}\s+\w{3,4}\.?\s+\d{4}',  # 29 set. 2025 ou 29 set 2025 (padrão geral)
            r'\d{1,2}[/-]\d{1,2}[/-]\d{4}',   # 01/08/2025
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',   # 2025/08/01
            r'\d{1,2}\s+de\s+\w+\s+de\s+\d{4}',  # 1 de agosto de 2025
        ]
        
        # Padrões aprimorados para valores monetários
        self.amount_patterns = [
            # Padrões com R$
            r'R\$\s*\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})',  # R$ 1.234,56 ou R$ 1,234.56
            r'R\$\s*\d+[.,]\d{2}',                         # R$ 22,00 ou R$ 22.00
            r'R\$\s*\d+',                                  # R$ 22
            r'R\$[\d.,]+',                                 # R$22,00 (sem espaço)
            
            # Padrões sem R$ mas com contexto
            r'\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})(?=\s*(?:reais?|BRL))', # 1.234,56 reais
            r'\d+[.,]\d{2}(?=\s*(?:reais?|BRL))',                       # 22,00 reais
            
            # Padrões específicos encontrados nos dados
            r'Pix\s+R\$\s*[\d.,]+',                       # "Pix R$ 22,00"
            r'(?:Pix|Dix)\s+R\$\s*[\d.,]+',              # "Pix R$ 22,00" ou "Dix R$ 22,00"
            
            # Padrões para capturar valores isolados no início de linha
            r'^R\$\s*[\d.,]+',                            # R$ no início da linha
            r'^\d+[.,]\d{2}$',                            # Apenas o valor numérico
            
            # Padrões mais flexíveis
            r'R\$\.?\s*\d+[.,]?\d*',                      # R$.5,00 ou R$. 5,00
            r'[\d.,]+\s*reais?',                          # Números seguidos de "reais"
            r'\$\s*[\d.,]+',                              # $ 22,00
        ]
    
    def _extract_path_info(self):
        """Extrai informações do caminho para nomenclatura dos arquivos"""
        path_parts = self.base_folder.parts
        
        # Procura por informações relevantes no caminho
        month = None
        transaction_type = None
        
        for part in path_parts:
            part_lower = part.lower()
            
            # Identifica mês
            meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho',
                    'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']
            meses_abrev = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun',
                          'jul', 'ago', 'set', 'out', 'nov', 'dez']
            
            if part_lower in meses or part_lower in meses_abrev:
                month = part_lower
            
            # Identifica tipo de transação
            tipos = ['debito', 'credito', 'pix', 'debit', 'credit']
            if part_lower in tipos:
                transaction_type = part_lower
        
        return {
            'month': month or 'mes',
            'transaction_type': transaction_type or 'transacao'
        }
    
    def _generate_file_prefix(self, index=None):
        """Gera prefixo para nomes de arquivos baseado na estrutura de pastas"""
        month = self.path_info['month']
        trans_type = self.path_info['transaction_type']
        
        if index is not None:
            return f"{month}_{trans_type}_{index:03d}"
        else:
            return f"{month}_{trans_type}"
    
    def extract_day_folders(self):
        """Extrai todas as pastas de dias (Screenshot_YYYYMMDD_HHMMSS_Ton ou pix (x))"""
        if not self.base_folder.exists():
            raise FileNotFoundError(f"Pasta base não encontrada: {self.base_folder}")
        
        # Procura por pastas
        day_folders = []
        for folder in self.base_folder.iterdir():
            if folder.is_dir():
                day_folders.append(folder)
        
        # Ordena numericamente por números entre parênteses, senão alfabeticamente
        def sort_key(folder):
            name = folder.name
            
            # Procura por números entre parênteses em qualquer posição do nome
            match = re.search(r'\((\d+)\)', name)
            if match:
                return (0, int(match.group(1)))  # Ordena numericamente pelo número
            else:
                return (1, name.lower())  # Ordena alfabeticamente se não tem número
        
        day_folders.sort(key=sort_key)
        return day_folders
    
    def get_quadrant_images(self, day_folder):
        """Obtém todas as imagens de quadrantes de um dia, ordenadas"""
        images = []
        
        # Procura por diferentes tipos de arquivo de imagem
        image_extensions = ["*.jpg", "*.jpeg", "*.png", "*.bmp", "*.tiff"]
        
        for extension in image_extensions:
            for img_file in day_folder.glob(extension):
                # Para pastas Screenshot, pega todas as imagens
                if day_folder.name.startswith('Screenshot_'):
                    # Usa timestamp do arquivo como "número do quadrante"
                    creation_time = img_file.stat().st_mtime
                    images.append((creation_time, img_file))
                
                # Para pastas pix, procura por quadrantes específicos
                elif "quadrante" in img_file.name:
                    match = re.search(r'quadrante_(\d+)', img_file.name)
                    if match:
                        quadrant_num = int(match.group(1))
                        images.append((quadrant_num, img_file))
                
                # Se não encontrar padrão específico, usa ordem alfabética
                else:
                    # Atribui um número baseado no nome do arquivo
                    file_order = hash(img_file.name) % 10000
                    images.append((file_order, img_file))
        
        # Ordena por número/timestamp do quadrante
        images.sort(key=lambda x: x[0])
        
        # Para pastas Screenshot, converte timestamp para números sequenciais
        if images and day_folder.name.startswith('Screenshot_'):
            sequential_images = []
            for i, (_, img_file) in enumerate(images):
                sequential_images.append((i + 1, img_file))
            return sequential_images
        
        return images
    
    def extract_date_info(self, text):
        """Extrai informações de data do texto"""
        if not text:
            return None
            
        for pattern in self.date_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0]
        
        return None
    
    def extract_amounts(self, text):
        """Extrai valores monetários do texto com padrões aprimorados"""
        if not text:
            return []
        
        amounts = []
        
        # Aplica cada padrão ao texto
        for pattern in self.amount_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
            amounts.extend(matches)
        
        # Remove duplicatas e normaliza valores
        normalized_amounts = []
        for amount in amounts:
            normalized = self._normalize_amount(amount)
            if normalized and normalized not in normalized_amounts:
                normalized_amounts.append(normalized)
        
        return normalized_amounts
    
    def _normalize_amount(self, amount_text):
        """Normaliza valores monetários para formato padrão"""
        if not amount_text:
            return None
        
        # Remove espaços extras e caracteres estranhos
        cleaned = re.sub(r'[^\d.,R\$]', '', amount_text)
        
        # Corrige padrões comuns de erro
        cleaned = cleaned.replace('R$.', 'R$ ')  # R$.5,00 -> R$ 5,00
        cleaned = re.sub(r'R\$(\d)', r'R$ \1', cleaned)  # R$22,00 -> R$ 22,00
        
        # Garante que tem pelo menos R$ e números
        if 'R$' in cleaned or re.search(r'\d+[.,]\d{2}', cleaned):
            # Adiciona R$ se não tiver
            if not cleaned.startswith('R$'):
                cleaned = 'R$ ' + cleaned
            
            # Normaliza espaçamento
            cleaned = re.sub(r'R\$\s*', 'R$ ', cleaned)
            
            return cleaned.strip()
        
        return None
    
    def extract_amount_smart(self, raw_text, processed_text):
        """Extração inteligente de valores considerando contexto"""
        # Tenta extrair de ambos os textos
        amounts_raw = self.extract_amounts(raw_text)
        amounts_processed = self.extract_amounts(processed_text)
        
        # Combina resultados
        all_amounts = amounts_raw + amounts_processed
        
        # Se não encontrou nada, tenta padrões mais agressivos
        if not all_amounts:
            # Combina todos os textos para busca mais ampla
            combined_text = f"{raw_text}\n{processed_text}"
            
            # Padrões específicos mais agressivos
            aggressive_patterns = [
                r'R\$\s*\d+[.,]\d{2}',           # R$ 22,00 ou R$ 22.00
                r'R\$\s*\d+',                    # R$ 22
                r'RS\s*\d+[.,]\d{2}',           # RS 22,00 (erro comum OCR)
                r'R\$\.?\s*\d+[.,]?\d*',        # R$.22,00 ou R$. 22
                r'Pix.*?R\$\s*[\d.,]+',         # Pix ... R$ 22,00
                r'(?:Pix|Dix).*?(\d+[.,]\d{2})', # Pix/Dix ... 22,00
                r'(\d+[.,]\d{2}).*?(?:Pix|Dix)', # 22,00 ... Pix/Dix
                r'(\d{1,3}[.,]\d{2})\s*(?=\s|$|Processando)', # Valor antes de "Processando"
                # Busca valores isolados que possam ter sido separados
                r'(?<!\d)(\d{1,3}[.,]\d{2})(?!\d)',  # Valores isolados
                r'(?<!\d)(\d{1,2},\d{2})(?!\d)',     # 16,00 isolado
                r'(?<!\d)(\d{1,2}\.\d{2})(?!\d)',    # 16.00 isolado
            ]
            
            for pattern in aggressive_patterns:
                matches = re.findall(pattern, combined_text, re.IGNORECASE | re.MULTILINE)
                for match in matches:
                    if isinstance(match, tuple):
                        match = match[0]
                    
                    # Tenta normalizar o valor encontrado
                    normalized = self._normalize_amount('R$ ' + str(match).strip())
                    if normalized and normalized not in all_amounts:
                        all_amounts.append(normalized)
            
            # Se ainda não encontrou, procura padrões extremamente flexíveis
            if not all_amounts:
                # Busca sequências numéricas que possam ser valores
                number_patterns = [
                    r'(\d{1,3}[,\.]\d{2})',  # Qualquer número com 2 decimais
                    r'(\d{1,2}[,\.]\d{2})',  # Números menores com 2 decimais
                ]
                
                for pattern in number_patterns:
                    matches = re.findall(pattern, combined_text)
                    for match in matches:
                        # Verifica se o número faz sentido como valor monetário
                        clean_match = match.replace(',', '.').replace('.', ',')  # Normaliza para formato BR
                        try:
                            # Converte para float para validar
                            float_val = float(clean_match.replace(',', '.'))
                            # Se está em uma faixa razoável para transações (R$ 0,01 a R$ 9999,99)
                            if 0.01 <= float_val <= 9999.99:
                                normalized = self._normalize_amount(f'R$ {clean_match}')
                                if normalized and normalized not in all_amounts:
                                    all_amounts.append(normalized)
                        except (ValueError, AttributeError):
                            continue
        
        # Retorna o primeiro valor válido encontrado
        return all_amounts[0] if all_amounts else None
    
    def clean_and_process_text(self, raw_text):
        """Limpa e processa o texto extraído preservando valores monetários"""
        if not raw_text:
            return ""
        
        # Preserva padrões monetários antes da limpeza
        # Protege R$ e valores monetários
        protected_text = raw_text
        
        # Normaliza caracteres problemáticos comuns no OCR
        protected_text = protected_text.replace('RS', 'R$')  # RS -> R$
        protected_text = protected_text.replace('R8', 'R$')  # R8 -> R$
        protected_text = protected_text.replace('R§', 'R$')  # R§ -> R$
        protected_text = re.sub(r'R\s*\$', 'R$', protected_text)  # R $ -> R$
        
        # Remove caracteres estranhos mas preserva monetários
        # Mantém: letras, números, espaços, pontuação monetária, acentos
        cleaned = re.sub(r'[^\w\s\.,\-\+\$R\(\)\/:\°áàâãéèêíìîóòôõúùûüçÁÀÂÃÉÈÊÍÌÎÓÒÔÕÚÙÛÜÇ]', ' ', protected_text)
        
        # Normaliza múltiplos espaços
        cleaned = re.sub(r'\s+', ' ', cleaned)
        
        # Remove espaços extras
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
            
            # Pula quadrantes vazios (0 caracteres)
            if len(processed_text.strip()) == 0:
                print("       ⏭️ Pulado - 0 caracteres detectados")
                return None
            
            # Extrai informações estruturadas
            date_info = self.extract_date_info(processed_text)
            
            # Usa extração inteligente de valores
            amount_found = self.extract_amount_smart(raw_text, processed_text)
            
            # Cria objeto de transação
            transaction = TransactionData(
                quadrant_number=quadrant_num,
                raw_text=raw_text,
                processed_text=processed_text,
                confidence=confidence,
                timestamp=date_info,
                amount=amount_found,
                description=processed_text[:200] + "..." if len(processed_text) > 200 else processed_text
            )
            
            # Debug: mostra se encontrou valor
            if amount_found:
                print(f"       Confiança: {confidence:.1f}% | Chars: {len(processed_text)} | ✅ Valor: {amount_found}")
            else:
                print(f"       Confiança: {confidence:.1f}% | Chars: {len(processed_text)} | ❌ Valor não encontrado")
                # Debug adicional para casos sem valor
                print(f"       📝 Texto bruto: '{raw_text[:100]}{'...' if len(raw_text) > 100 else ''}'")
                print(f"       🔧 Texto processado: '{processed_text[:100]}{'...' if len(processed_text) > 100 else ''}'")
                
                # Tenta buscar qualquer sequência que pareça um valor
                potential_values = re.findall(r'\d{1,3}[.,]\d{2}', raw_text + ' ' + processed_text)
                if potential_values:
                    print(f"       🔍 Possíveis valores detectados: {potential_values}")
            
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
        date_info = self.extract_date_info(header_processed)
        
        if date_info:
            print(f"      ✅ Data identificada: {date_info}")
        else:
            date_info = "Data não identificada"
            print(f"      ❌ Data não identificada no texto: '{header_processed}'")
        
        print(f"      Confiança: {header_confidence:.1f}%")
        
        # Processa demais quadrantes (transações)
        transactions = []
        
        for quadrant_num, image_path in quadrant_images[1:]:  # Pula o primeiro
            transaction = self.process_single_quadrant(quadrant_num, image_path)
            # Apenas adiciona transações válidas (pula None - quadrantes vazios)
            if transaction is not None:
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
        
        # Calcula quantos foram pulados
        total_processed = len(quadrant_images) - 1  # -1 porque o primeiro é cabeçalho
        quadrants_skipped = total_processed - len(transactions)
        
        if quadrants_skipped > 0:
            print(f"   ✅ Dia processado: {len(transactions)} transações | {quadrants_skipped} quadrantes pulados (vazios)")
        else:
            print(f"   ✅ Dia processado: {len(transactions)} transações")
        
        return day_data
    
    def save_day_data(self, day_data, format='json', index=None):
        """Salva dados de um dia em arquivo"""
        # Gera nome do arquivo baseado na estrutura de pastas
        if index is not None:
            file_prefix = self._generate_file_prefix(index)
        else:
            file_prefix = f"{self._generate_file_prefix()}_{day_data.day_folder}"
        
        if format == 'json':
            output_file = self.output_folder / f"{file_prefix}_data.json"
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(asdict(day_data), f, ensure_ascii=False, indent=2)
            
            print(f"   💾 Dados salvos em: {output_file}")
        
        elif format == 'txt':
            output_file = self.output_folder / f"{file_prefix}_data.txt"
            
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
        
        # Mostra padrão de nomenclatura
        example_prefix = self._generate_file_prefix(1)
        print(f"📝 Padrão de nomenclatura: {example_prefix}_data.json/txt")
        print(f"   Baseado no caminho: {self.base_folder}")
        print(f"   Mês: {self.path_info['month']}")
        print(f"   Tipo: {self.path_info['transaction_type']}")
        print(f"   Pasta de saída: {self.output_folder}")
        
        # Obtém todas as pastas de dias
        day_folders = self.extract_day_folders()
        
        if not day_folders:
            print("❌ Nenhuma pasta de dia encontrada!")
            return []
        
        print(f"📁 Encontradas {len(day_folders)} pastas de dias para processar")
        
        all_days_data = []
        successful_days = 0
        
        for index, day_folder in enumerate(day_folders, 1):
            try:
                day_data = self.process_single_day(day_folder)
                
                if day_data:
                    all_days_data.append(day_data)
                    successful_days += 1
                    
                    # Salva dados do dia com índice sequencial
                    if save_format in ['json', 'both']:
                        self.save_day_data(day_data, 'json', index)
                    
                    if save_format in ['txt', 'both']:
                        self.save_day_data(day_data, 'txt', index)
                
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
        summary_prefix = self._generate_file_prefix()
        summary_file = self.output_folder / f"{summary_prefix}_resumo_geral.txt"
        
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
        print(f"   📦 {len(quadrants)} imagens encontradas")
        
        for i, (num, img_path) in enumerate(quadrants[:5]):  # Mostra apenas os 5 primeiros
            if i == 0:
                print(f"   🏷️  Imagem {num}: {img_path.name} (CABEÇALHO)")
            else:
                print(f"   📋 Imagem {num}: {img_path.name}")
        
        if len(quadrants) > 5:
            print(f"   ... e mais {len(quadrants) - 5} imagens")


def process_screenshot_folders(base_folder, output_folder=None):
    """Função específica para processar pastas Screenshot_YYYYMMDD_HHMMSS_Ton"""
    print("🎯 Processamento específico para pastas Screenshot")
    print("=" * 50)
    
    processor = StructuredTransactionOCR(base_folder, output_folder)
    
    # Mostra informações de nomenclatura
    print("📝 Padrão de nomenclatura dos arquivos:")
    print(f"   Baseado no caminho: {base_folder}")
    print(f"   Mês: {processor.path_info['month']}")
    print(f"   Tipo: {processor.path_info['transaction_type']}")
    print(f"   Exemplo: {processor._generate_file_prefix(1)}_data.json")
    
    # Mostra estrutura primeiro
    day_folders = processor.extract_day_folders()
    print(f"\n📁 Encontradas {len(day_folders)} pastas para processar:")
    
    for folder in day_folders:
        images = processor.get_quadrant_images(folder)
        print(f"   📂 {folder.name}: {len(images)} imagens")
    
    # Confirma antes de processar
    print(f"\n📋 Os arquivos serão salvos em: {processor.output_folder}")
    confirmacao = input("\nDeseja continuar com o processamento? (s/n): ")
    
    if confirmacao.lower() == 's':
        # Processa todas
        return processor.process_all_days('both')
    else:
        print("❌ Processamento cancelado pelo usuário")
        return []


def test_nomenclature_system(base_folder):
    """Testa o sistema de nomenclatura sem processar imagens"""
    print("🧪 Teste do Sistema de Nomenclatura")
    print("=" * 40)
    
    processor = StructuredTransactionOCR(base_folder)
    
    print(f"📂 Pasta base: {base_folder}")
    print(f"📅 Mês extraído: {processor.path_info['month']}")
    print(f"💳 Tipo extraído: {processor.path_info['transaction_type']}")
    print(f"📁 Pasta de saída: {processor.output_folder}")
    
    print("\n🏷️ Exemplos de nomes de arquivos que serão gerados:")
    for i in range(1, 6):
        json_name = f"{processor._generate_file_prefix(i)}_data.json"
        txt_name = f"{processor._generate_file_prefix(i)}_data.txt"
        print(f"   {i:2d}. {json_name}")
        print(f"       {txt_name}")
    
    resumo_name = f"{processor._generate_file_prefix()}_resumo_geral.txt"
    print(f"\n📊 Arquivo de resumo: {resumo_name}")
    
    return processor



if __name__ == "__main__":
    # Configuração padrão - atualizada para a pasta quadrantes
    BASE_FOLDER = r"data\images\Agosto\pix\cropped_images\quadrantes"
    OUTPUT_FOLDER = r"data\raw\ocr_results"
    
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
5 - Processar pastas Screenshot específicas
6 - Testar sistema de nomenclatura
7 - Configuração personalizada

Digite sua opção (1-7): """)
    
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
            process_screenshot_folders(BASE_FOLDER, OUTPUT_FOLDER)
        
        elif choice == "6":
            test_nomenclature_system(BASE_FOLDER)
        
        elif choice == "7":
            base_path = input(f"Pasta base ({BASE_FOLDER}): ") or BASE_FOLDER
            output_path = input(f"Pasta saída ({OUTPUT_FOLDER}): ") or OUTPUT_FOLDER
            format_choice = input("Formato (json/txt/both): ") or 'both'
            
            process_transactions_quick(base_path, output_path, format_choice)
        
        else:
            print("❌ Opção inválida!")
    
    except Exception as e:
        print(f"❌ Erro: {str(e)}")