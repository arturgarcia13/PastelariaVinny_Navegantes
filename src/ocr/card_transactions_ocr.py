import cv2
import numpy as np
from PIL import Image
import pytesseract
from pathlib import Path
import csv
import re
import os
import shutil
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass


@dataclass
class CardTransaction:
    """Estrutura para uma transação de cartão"""
    date: str
    time: str
    amount: float
    transaction_type: str
    reference_file: str


class CardTransactionOCR:
    """Sistema de OCR para extrair transações de cartão (crédito/débito) de imagens longas"""
    
    def __init__(self, images_folder, output_folder=None):
        self.images_folder = Path(images_folder)
        self.output_folder = Path(output_folder) if output_folder else Path("outputs/reports")
        
        # Cria pasta de saída se não existir
        self.output_folder.mkdir(parents=True, exist_ok=True)
        
        # Configura Tesseract
        self._setup_tesseract()
        
        # Mapeamento de meses em português para números
        self.month_mapping = {
            'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04',
            'mai': '05', 'jun': '06', 'jul': '07', 'ago': '08',
            'set': '09', 'out': '10', 'nov': '11', 'dez': '12'
        }
        
        # Padrões regex para extração
        self.date_patterns = [
            r'\d{1,2}\s+\w{3,4}\.?\s+\d{4}',  # 29 set. 2025
            r'\d{1,2}[/-]\d{1,2}[/-]\d{4}',   # 29/09/2025
            r'\d{4}[/-]\d{1,2}[/-]\d{1,2}',   # 2025/09/29
            r'\d{1,2}\s+de\s+\w+\s+de\s+\d{4}',  # 29 de setembro de 2025
        ]
        
        self.time_pattern = r'\b([0-2]?[0-9]):([0-5][0-9])\b'
        
        self.value_patterns = [
            r'R\$\s*([0-9]+[.,]?[0-9]*)',     # R$ 13,00
            r'([0-9]+[.,][0-9]{2})\s*reais?', # 13,00 reais
            r'\$\s*([0-9]+[.,]?[0-9]*)',      # $ 13,00
        ]
    
    def _setup_tesseract(self):
        """
        Configura o caminho do Tesseract automaticamente
        """
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
        
        # Se não encontrou, mostra aviso
        print("⚠️  Tesseract não encontrado automaticamente.")
        print("   Você pode instalá-lo ou configurar manualmente.")
    
    def test_tesseract(self) -> bool:
        """
        Testa se o Tesseract está funcionando
        """
        try:
            # Cria uma imagem simples para teste
            test_img = Image.new('RGB', (100, 30), color='white')
            
            # Tenta fazer OCR
            pytesseract.image_to_string(test_img)
            return True
            
        except Exception as e:
            print(f"❌ Erro no teste do Tesseract: {str(e)}")
            return False
    
    def enhance_image_for_ocr(self, image_path: str) -> np.ndarray:
        """
        Aplica pré-processamento na imagem para melhorar OCR
        """
        # Carrega imagem
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Não foi possível carregar a imagem: {image_path}")
        
        # Converte para escala de cinza
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Redimensiona se muito grande (mantém proporção)
        height, width = gray.shape
        max_width = 2000
        if width > max_width:
            scale = max_width / width
            new_width = int(width * scale)
            new_height = int(height * scale)
            gray = cv2.resize(gray, (new_width, new_height), interpolation=cv2.INTER_LANCZOS4)
        
        # Aplica denoising
        denoised = cv2.fastNlMeansDenoising(gray)
        
        # Melhora contraste usando CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(denoised)
        
        # Binarização adaptativa para melhor contraste
        binary = cv2.adaptiveThreshold(
            enhanced, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY, 11, 2
        )
        
        return binary
    
    def extract_text_from_image(self, image_path: str) -> Tuple[str, float]:
        """
        Extrai texto completo da imagem usando OCR
        """
        try:
            # Verifica se Tesseract está funcionando
            if not self.test_tesseract():
                return "Erro: Tesseract não configurado", 0.0
            
            # Pré-processa imagem
            processed_img = self.enhance_image_for_ocr(image_path)
            
            # Converte para PIL Image
            pil_img = Image.fromarray(processed_img)
            
            # Configuração otimizada do Tesseract para português
            custom_config = r'--oem 3 --psm 6 -l por'
            
            # Extrai texto
            text = pytesseract.image_to_string(pil_img, config=custom_config)
            
            # Calcula confiança média (usando image_to_data)
            try:
                data = pytesseract.image_to_data(pil_img, config=custom_config, output_type=pytesseract.Output.DICT)
                confidences = [int(conf) for conf in data['conf'] if int(conf) > 0]
                avg_confidence = sum(confidences) / len(confidences) if confidences else 0
            except Exception:
                avg_confidence = 0.0
            
            return text.strip(), avg_confidence
            
        except Exception as e:
            print(f"❌ Erro no OCR de {image_path}: {str(e)}")
            return "", 0.0
    
    def identify_transaction_type(self, filename: str) -> str:
        """
        Identifica tipo de transação baseado no nome do arquivo
        """
        filename_lower = filename.lower()
        
        if 'credito' in filename_lower:
            return 'Crédito'
        elif 'debito' in filename_lower:
            return 'Débito'
        else:
            return 'Não identificado'
    
    def convert_date_format(self, date_string: str) -> str:
        """
        Converte data para formato DD/MM/YYYY
        """
        if not date_string:
            return "Não encontrado"
        
        # Remove pontos e normaliza espaços
        normalized = re.sub(r'\.', '', date_string.strip())
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Tenta padrão: dia mês ano (ex: "29 set 2025")
        match = re.match(r'(\d{1,2})\s+(\w{3,4})\s+(\d{4})', normalized)
        
        if match:
            day = match.group(1).zfill(2)
            month_abbr = match.group(2).lower()[:3]
            year = match.group(3)
            
            month_num = self.month_mapping.get(month_abbr, '01')
            return f"{day}/{month_num}/{year}"
        
        # Tenta outros padrões
        for pattern in self.date_patterns[1:]:  # Pula o primeiro que já testamos
            match = re.search(pattern, date_string)
            if match:
                return match.group(0)
        
        return "Não encontrado"
    
    def extract_date_from_text(self, text: str) -> str:
        """
        Extrai data do texto (geralmente no início)
        """
        # Pega as primeiras linhas do texto onde geralmente está a data
        first_lines = '\n'.join(text.split('\n')[:10])
        
        for pattern in self.date_patterns:
            matches = re.findall(pattern, first_lines, re.IGNORECASE)
            if matches:
                return self.convert_date_format(matches[0])
        
        return "Não encontrado"
    
    def extract_times_from_text(self, text: str) -> List[str]:
        """
        Extrai todos os horários encontrados no texto
        """
        matches = re.findall(self.time_pattern, text)
        times = []
        
        for hour, minute in matches:
            formatted_time = f"{hour.zfill(2)}:{minute}"
            times.append(formatted_time)
        
        return times
    
    def extract_values_from_text(self, text: str) -> List[float]:
        """
        Extrai todos os valores monetários do texto
        """
        values = []
        
        for pattern in self.value_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            
            for match in matches:
                try:
                    # Limpa e converte valor
                    cleaned_value = match.replace(',', '.')
                    value = float(cleaned_value)
                    
                    # Filtra valores muito pequenos ou muito grandes (prováveis erros)
                    if 0.01 <= value <= 999999:
                        values.append(value)
                        
                except (ValueError, TypeError):
                    continue
        
        return values
    
    def extract_transactions_from_text(self, text: str, date: str, transaction_type: str, filename: str) -> List[CardTransaction]:
        """
        Extrai múltiplas transações de um texto
        """
        transactions = []
        
        # Extrai horários e valores
        times = self.extract_times_from_text(text)
        values = self.extract_values_from_text(text)
        
        # Combina horários com valores (pega o menor número entre os dois)
        min_count = min(len(times), len(values))
        
        for i in range(min_count):
            transaction = CardTransaction(
                date=date,
                time=times[i],
                amount=values[i],
                transaction_type=transaction_type,
                reference_file=filename
            )
            transactions.append(transaction)
        
        # Se houver mais valores que horários, adiciona com "Não encontrado"
        if len(values) > len(times):
            for i in range(len(times), len(values)):
                transaction = CardTransaction(
                    date=date,
                    time="Não encontrado",
                    amount=values[i],
                    transaction_type=transaction_type,
                    reference_file=filename
                )
                transactions.append(transaction)
        
        # Se houver mais horários que valores, adiciona com valor "Não encontrado"
        elif len(times) > len(values):
            for i in range(len(values), len(times)):
                transaction = CardTransaction(
                    date=date,
                    time=times[i],
                    amount="Não encontrado",
                    transaction_type=transaction_type,
                    reference_file=filename
                )
                transactions.append(transaction)
        
        return transactions
    
    def process_single_image(self, image_path: Path) -> List[CardTransaction]:
        """
        Processa uma única imagem e extrai todas as transações
        """
        print(f"🔄 Processando: {image_path.name}")
        
        try:
            # Extrai texto da imagem
            text, confidence = self.extract_text_from_image(str(image_path))
            
            if not text:
                print("   ❌ Nenhum texto extraído")
                return []
            
            print(f"   📄 Texto extraído ({len(text)} chars) - Confiança: {confidence:.1f}%")
            
            # Identifica tipo de transação
            transaction_type = self.identify_transaction_type(image_path.name)
            
            # Extrai data
            date = self.extract_date_from_text(text)
            
            # Extrai transações
            transactions = self.extract_transactions_from_text(
                text, date, transaction_type, image_path.name
            )
            
            print(f"   ✅ {len(transactions)} transações extraídas - Tipo: {transaction_type} - Data: {date}")
            
            return transactions
            
        except Exception as e:
            print(f"   ❌ Erro: {str(e)}")
            return []
    
    def get_all_card_images(self) -> List[Path]:
        """
        Obtém todas as imagens de cartão (crédito e débito)
        """
        if not self.images_folder.exists():
            raise FileNotFoundError(f"Pasta não encontrada: {self.images_folder}")
        
        # Busca imagens de crédito e débito
        image_files = []
        
        # Adiciona imagens de crédito
        credito_files = list(self.images_folder.glob("credito (*).*"))
        image_files.extend(credito_files)
        
        # Adiciona imagens de débito  
        debito_files = list(self.images_folder.glob("debito (*).*"))
        image_files.extend(debito_files)
        
        # Ordena por tipo e número
        def sort_key(file_path):
            # Extrai tipo (credito/debito) e número
            if 'credito' in file_path.name:
                tipo = 0  # crédito primeiro
            else:
                tipo = 1  # débito depois
            
            # Extrai número
            match = re.search(r'\((\d+)\)', file_path.name)
            numero = int(match.group(1)) if match else 0
            
            return (tipo, numero)
        
        image_files.sort(key=sort_key)
        
        return image_files
    
    def process_all_images(self) -> List[CardTransaction]:
        """
        Processa todas as imagens e consolida transações
        """
        print("🚀 Iniciando extração de transações de cartão")
        print("=" * 60)
        
        image_files = self.get_all_card_images()
        
        if not image_files:
            print("❌ Nenhuma imagem de cartão encontrada!")
            return []
        
        print(f"📁 Encontradas {len(image_files)} imagens para processar")
        
        all_transactions = []
        
        for image_file in image_files:
            transactions = self.process_single_image(image_file)
            all_transactions.extend(transactions)
            print()  # Linha em branco
        
        print("=" * 60)
        print(f"📊 Total de transações extraídas: {len(all_transactions)}")
        
        return all_transactions
    
    def generate_csv(self, transactions: List[CardTransaction], filename: str = "transacoes_cartao.csv") -> Path:
        """
        Gera arquivo CSV com as transações
        """
        if not transactions:
            print("❌ Nenhuma transação para exportar!")
            return None
        
        output_file = self.output_folder / filename
        
        # Cabeçalhos do CSV
        fieldnames = ['Data', 'Hora', 'Valor', 'Tipo de Venda', 'Referência']
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
                
                # Escreve cabeçalho
                writer.writeheader()
                
                # Escreve transações
                for transaction in transactions:
                    writer.writerow({
                        'Data': transaction.date,
                        'Hora': transaction.time,
                        'Valor': transaction.amount,
                        'Tipo de Venda': transaction.transaction_type,
                        'Referência': transaction.reference_file
                    })
            
            print(f"✅ CSV gerado com sucesso: {output_file}")
            print(f"📊 Total de linhas: {len(transactions) + 1} (incluindo cabeçalho)")
            
            return output_file
            
        except Exception as e:
            print(f"❌ Erro ao gerar CSV: {str(e)}")
            return None
    
    def generate_statistics_report(self, transactions: List[CardTransaction]) -> None:
        """
        Gera relatório estatístico das transações
        """
        if not transactions:
            return
        
        # Estatísticas por tipo
        credito_transactions = [t for t in transactions if t.transaction_type == 'Crédito']
        debito_transactions = [t for t in transactions if t.transaction_type == 'Débito']
        
        # Valores válidos
        credito_values = [t.amount for t in credito_transactions if isinstance(t.amount, (int, float))]
        debito_values = [t.amount for t in debito_transactions if isinstance(t.amount, (int, float))]
        all_values = credito_values + debito_values
        
        # Relatório
        report_file = self.output_folder / "relatorio_cartao_estatisticas.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("RELATÓRIO ESTATÍSTICO - TRANSAÇÕES DE CARTÃO\n")
            f.write("=" * 50 + "\n")
            f.write(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
            
            f.write("📊 RESUMO GERAL:\n")
            f.write(f"   Total de transações: {len(transactions)}\n")
            f.write(f"   Transações de Crédito: {len(credito_transactions)}\n")
            f.write(f"   Transações de Débito: {len(debito_transactions)}\n\n")
            
            if all_values:
                f.write("💰 VALORES:\n")
                f.write(f"   Total geral: R$ {sum(all_values):.2f}\n")
                f.write(f"   Valor médio: R$ {sum(all_values)/len(all_values):.2f}\n")
                
                if credito_values:
                    f.write(f"   Total Crédito: R$ {sum(credito_values):.2f}\n")
                if debito_values:
                    f.write(f"   Total Débito: R$ {sum(debito_values):.2f}\n")
        
        print(f"📈 Relatório estatístico salvo: {report_file}")
    
    def extract_and_generate_csv(self, output_filename: str = "transacoes_cartao.csv") -> Optional[Path]:
        """
        Método principal para extração completa e geração de CSV
        """
        # Processa todas as imagens
        transactions = self.process_all_images()
        
        if not transactions:
            return None
        
        # Gera CSV
        csv_file = self.generate_csv(transactions, output_filename)
        
        # Gera relatório estatístico
        self.generate_statistics_report(transactions)
        
        return csv_file


# Funções de conveniência
def extract_card_transactions_quick(images_folder, output_folder=None, filename="transacoes_cartao.csv"):
    """Função rápida para extração de transações de cartão"""
    extractor = CardTransactionOCR(images_folder, output_folder)
    return extractor.extract_and_generate_csv(filename)


def preview_card_images(images_folder, max_images=3):
    """Visualiza informações das primeiras imagens"""
    extractor = CardTransactionOCR(images_folder)
    image_files = extractor.get_all_card_images()
    
    print("🔍 PREVIEW DAS IMAGENS:")
    print("=" * 40)
    
    for i, image_file in enumerate(image_files[:max_images]):
        print(f"\n📄 {image_file.name}:")
        
        # Identifica tipo
        transaction_type = extractor.identify_transaction_type(image_file.name)
        print(f"   Tipo: {transaction_type}")
        
        # Extrai amostra de texto (apenas primeiras linhas)
        try:
            text, confidence = extractor.extract_text_from_image(str(image_file))
            first_lines = '\n'.join(text.split('\n')[:5])
            print(f"   Confiança OCR: {confidence:.1f}%")
            print(f"   Primeiras linhas: {first_lines[:100]}...")
        except Exception as e:
            print(f"   Erro: {str(e)}")


if __name__ == "__main__":
    # Configurações padrão
    IMAGES_FOLDER = r"data\raw\Imagens\unprocessed"
    OUTPUT_FOLDER = r"outputs\reports"
    
    print("💳 Sistema de Extração de Transações de Cartão")
    print("=" * 50)
    
    choice = input("""
Escolha uma opção:
1 - Extrair todas as transações e gerar CSV
2 - Preview das imagens (sem processamento)
3 - Testar configuração do Tesseract
4 - Configuração personalizada
5 - Extrair com nome personalizado

Digite sua opção (1-5): """)
    
    try:
        if choice == "1":
            csv_file = extract_card_transactions_quick(IMAGES_FOLDER, OUTPUT_FOLDER)
            if csv_file:
                print(f"\n🎉 Extração concluída! Arquivo: {csv_file}")
        
        elif choice == "2":
            preview_card_images(IMAGES_FOLDER)
        
        elif choice == "3":
            print("🔍 Testando configuração do Tesseract...")
            extractor = CardTransactionOCR(IMAGES_FOLDER)
            if extractor.test_tesseract():
                print("✅ Tesseract está funcionando corretamente!")
            else:
                print("❌ Tesseract não está funcionando. Verifique a instalação.")
        
        elif choice == "4":
            images_path = input(f"Pasta das imagens ({IMAGES_FOLDER}): ") or IMAGES_FOLDER
            output_path = input(f"Pasta de saída ({OUTPUT_FOLDER}): ") or OUTPUT_FOLDER
            filename = input("Nome do arquivo CSV (transacoes_cartao.csv): ") or "transacoes_cartao.csv"
            
            csv_file = extract_card_transactions_quick(images_path, output_path, filename)
            if csv_file:
                print(f"\n🎉 Extração concluída! Arquivo: {csv_file}")
        
        elif choice == "5":
            filename = input("Nome do arquivo CSV: ")
            if filename and not filename.endswith('.csv'):
                filename += '.csv'
            
            csv_file = extract_card_transactions_quick(IMAGES_FOLDER, OUTPUT_FOLDER, filename)
            if csv_file:
                print(f"\n🎉 Extração concluída! Arquivo: {csv_file}")
        
        else:
            print("❌ Opção inválida!")
    
    except Exception as e:
        print(f"❌ Erro durante a extração: {str(e)}")