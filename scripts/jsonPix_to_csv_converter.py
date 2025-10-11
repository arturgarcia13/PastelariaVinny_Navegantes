import json
import csv
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Tuple


class JSONToCSVConverter:
    """Conversor de arquivos JSON de transações para CSV estruturado"""
    
    def __init__(self, json_folder, output_folder=None):
        self.json_folder = Path(json_folder)
        self.output_folder = Path(output_folder) if output_folder else self.json_folder.parent / "reports"
        
        # Cria pasta de saída se não existir
        self.output_folder.mkdir(exist_ok=True)
        
        # Mapeamento de meses em português para números
        self.month_mapping = {
            'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04',
            'mai': '05', 'jun': '06', 'jul': '07', 'ago': '08',
            'set': '09', 'out': '10', 'nov': '11', 'dez': '12'
        }
        
        # Padrões regex para extração
        self.time_pattern = r'\b([0-2]?[0-9]):([0-5][0-9])\b'
        self.value_pattern = r'R\$\s*([0-9]+[.,]?[0-9]*)'
    
    def convert_date_format(self, date_string: str) -> str:
        """
        Converte data do formato '29 set. 2025' para '29/09/2025'
        """
        if not date_string or date_string == "Data não identificada":
            return "Não encontrado"
        
        # Remove pontos e normaliza espaços
        normalized = re.sub(r'\.', '', date_string.strip())
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Padrão: dia mês ano (ex: "29 set 2025")
        match = re.match(r'(\d{1,2})\s+(\w{3,4})\s+(\d{4})', normalized)
        
        if match:
            day = match.group(1).zfill(2)  # Adiciona zero à esquerda se necessário
            month_abbr = match.group(2).lower()[:3]  # Primeiras 3 letras em minúsculo
            year = match.group(3)
            
            # Converte mês abreviado para número
            month_num = self.month_mapping.get(month_abbr, '01')
            
            return f"{day}/{month_num}/{year}"
        
        return "Não encontrado"  # Retorna "Não encontrado" se não conseguir converter
    
    def extract_time_from_text(self, text: str) -> str:
        """
        Extrai horário do texto no formato HH:MM
        """
        if not text:
            return "Não encontrado"
        
        matches = re.findall(self.time_pattern, text)
        
        if matches:
            # Pega o primeiro horário encontrado
            hour, minute = matches[0]
            return f"{hour.zfill(2)}:{minute}"
        
        return "Não encontrado"
    
    def convert_value_to_float(self, value_string: str) -> Optional[float]:
        """
        Converte valor monetário para float
        Ex: 'R$ 13,00' → 13.00
        """
        if not value_string:
            return "Não encontrado"
        
        # Remove 'R$' e espaços
        cleaned = re.sub(r'R\$\s*', '', value_string)
        
        # Remove espaços extras
        cleaned = cleaned.strip()
        
        # Substitui vírgula por ponto
        cleaned = cleaned.replace(',', '.')
        
        try:
            return float(cleaned)
        except (ValueError, AttributeError):
            return "Não encontrado"
    
    def extract_reference_filename(self, day_folder: str, quadrant_number: int) -> str:
        """
        Gera nome do arquivo de referência
        Ex: 'pix (1)' + quadrante 2 → 'pix (1)_quadrante_02.jpg'
        """
        return f"{day_folder}_quadrante_{quadrant_number:02d}.jpg"
    
    def process_single_json(self, json_file_path: Path) -> List[Dict]:
        """
        Processa um único arquivo JSON e extrai transações
        """
        transactions_data = []
        
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extrai informações do dia
            day_folder = data.get('day_folder', '')
            date_info = data.get('date_info', '')
            
            # Converte data
            formatted_date = self.convert_date_format(date_info)
            
            # Processa cada transação
            transactions = data.get('transactions', [])
            
            for transaction in transactions:
                quadrant_num = transaction.get('quadrant_number', 0)
                raw_text = transaction.get('raw_text', '')
                processed_text = transaction.get('processed_text', '')
                amount_str = transaction.get('amount', '')
                
                # Extrai horário
                time_str = self.extract_time_from_text(processed_text or raw_text)
                
                # Converte valor
                value_float = self.convert_value_to_float(amount_str)
                
                # Gera nome do arquivo de referência
                reference_file = self.extract_reference_filename(day_folder, quadrant_num)
                
                # Adiciona todas as transações (mesmo sem valor válido)
                transaction_row = {
                    'Data': formatted_date,
                    'Hora': time_str,
                    'Valor': value_float,
                    'Tipo de Venda': 'Pix',
                    'arquivo_de_referencia': reference_file
                }
                
                transactions_data.append(transaction_row)
            
            print(f"✅ Processado: {json_file_path.name} - {len(transactions_data)} transações")
            
        except Exception as e:
            print(f"❌ Erro ao processar {json_file_path.name}: {str(e)}")
        
        return transactions_data
    
    def get_all_json_files(self) -> List[Path]:
        """
        Obtém todos os arquivos JSON da pasta
        """
        if not self.json_folder.exists():
            raise FileNotFoundError(f"Pasta não encontrada: {self.json_folder}")
        
        json_files = list(self.json_folder.glob("pix (*)*_data.json"))
        
        # Ordena por número do pix
        def extract_pix_number(file_path):
            match = re.search(r'pix \((\d+)\)', file_path.name)
            return int(match.group(1)) if match else 0
        
        json_files.sort(key=extract_pix_number)
        
        return json_files
    
    def process_all_json_files(self) -> List[Dict]:
        """
        Processa todos os arquivos JSON e consolida transações
        """
        print("🔄 Iniciando conversão JSON → CSV")
        print("=" * 50)
        
        json_files = self.get_all_json_files()
        
        if not json_files:
            print("❌ Nenhum arquivo JSON encontrado!")
            return []
        
        print(f"📁 Encontrados {len(json_files)} arquivos JSON")
        
        all_transactions = []
        
        for json_file in json_files:
            transactions = self.process_single_json(json_file)
            all_transactions.extend(transactions)
        
        print(f"\n📊 Total de transações válidas: {len(all_transactions)}")
        
        return all_transactions
    
    def generate_csv(self, transactions: List[Dict], filename: str = "transacoes_consolidadas.csv") -> Path:
        """
        Gera arquivo CSV com as transações
        """
        if not transactions:
            print("❌ Nenhuma transação para exportar!")
            return None
        
        output_file = self.output_folder / filename
        
        # Cabeçalhos do CSV
        fieldnames = ['Data', 'Hora', 'Valor', 'Tipo de Venda', 'arquivo_de_referencia']
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
                
                # Escreve cabeçalho
                writer.writeheader()
                
                # Escreve transações
                for transaction in transactions:
                    writer.writerow(transaction)
            
            print(f"✅ CSV gerado com sucesso: {output_file}")
            print(f"📊 Total de linhas: {len(transactions) + 1} (incluindo cabeçalho)")
            
            return output_file
            
        except Exception as e:
            print(f"❌ Erro ao gerar CSV: {str(e)}")
            return None
    
    def generate_statistics_report(self, transactions: List[Dict]) -> None:
        """
        Gera relatório estatístico das transações
        """
        if not transactions:
            return
        
        # Estatísticas básicas
        total_transactions = len(transactions)
        # Calcula total apenas para valores numéricos
        valid_values = [t['Valor'] for t in transactions if isinstance(t['Valor'], (int, float))]
        total_value = sum(valid_values)
        avg_value = total_value / len(valid_values) if valid_values else 0
        
        # Transações por dia
        days_count = {}
        for transaction in transactions:
            day = transaction['Data']
            days_count[day] = days_count.get(day, 0) + 1
        
        # Salva relatório
        report_file = self.output_folder / "relatorio_estatisticas.txt"
        
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write("RELATÓRIO ESTATÍSTICO - TRANSAÇÕES PIX\n")
            f.write("=" * 50 + "\n")
            f.write(f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n\n")
            
            f.write("📊 RESUMO GERAL:\n")
            f.write(f"   Total de transações: {total_transactions}\n")
            f.write(f"   Valor total: R$ {total_value:.2f}\n")
            f.write(f"   Valor médio: R$ {avg_value:.2f}\n")
            f.write(f"   Dias processados: {len(days_count)}\n\n")
            
            f.write("📅 TRANSAÇÕES POR DIA:\n")
            for day, count in sorted(days_count.items()):
                # Calcula total apenas para valores numéricos deste dia
                day_values = [t['Valor'] for t in transactions if t['Data'] == day and isinstance(t['Valor'], (int, float))]
                day_total = sum(day_values)
                f.write(f"   {day}: {count} transações - R$ {day_total:.2f}\n")
        
        print(f"📈 Relatório estatístico salvo: {report_file}")
    
    def convert_to_csv(self, output_filename: str = "transacoes_consolidadas.csv") -> Optional[Path]:
        """
        Método principal para conversão completa
        """
        # Processa todos os JSONs
        transactions = self.process_all_json_files()
        
        if not transactions:
            return None
        
        # Gera CSV
        csv_file = self.generate_csv(transactions, output_filename)
        
        # Gera relatório estatístico
        self.generate_statistics_report(transactions)
        
        return csv_file


# Funções de conveniência
def convert_json_to_csv_quick(json_folder, output_folder=None, filename="transacoes_consolidadas.csv"):
    """Função rápida para conversão JSON → CSV"""
    converter = JSONToCSVConverter(json_folder, output_folder)
    return converter.convert_to_csv(filename)


def preview_conversion_data(json_folder, max_files=3):
    """Visualiza como os dados serão convertidos"""
    converter = JSONToCSVConverter(json_folder)
    json_files = converter.get_all_json_files()
    
    print("🔍 PREVIEW DA CONVERSÃO:")
    print("=" * 40)
    
    for i, json_file in enumerate(json_files[:max_files]):
        print(f"\n📄 {json_file.name}:")
        transactions = converter.process_single_json(json_file)
        
        for j, transaction in enumerate(transactions[:3]):  # Mostra apenas 3 primeiras
            print(f"   {j+1}. {transaction['Data']} | {transaction['Hora']} | R$ {transaction['Valor']:.2f} | {transaction['arquivo_de_referencia']}")
        
        if len(transactions) > 3:
            print(f"   ... e mais {len(transactions) - 3} transações")


if __name__ == "__main__":
    # Configurações padrão
    JSON_FOLDER = r"outputs\ocr_results"
    OUTPUT_FOLDER = r"outputs\reports"
    
    print("💱 Conversor JSON → CSV para Transações PIX")
    print("=" * 50)
    
    choice = input("""
Escolha uma opção:
1 - Converter todos os JSONs para CSV
2 - Preview dos dados (sem conversão)
3 - Configuração personalizada
4 - Converter com nome personalizado

Digite sua opção (1-4): """)
    
    try:
        if choice == "1":
            csv_file = convert_json_to_csv_quick(JSON_FOLDER, OUTPUT_FOLDER)
            if csv_file:
                print(f"\n🎉 Conversão concluída! Arquivo: {csv_file}")
        
        elif choice == "2":
            preview_conversion_data(JSON_FOLDER)
        
        elif choice == "3":
            json_path = input(f"Pasta dos JSONs ({JSON_FOLDER}): ") or JSON_FOLDER
            output_path = input(f"Pasta de saída ({OUTPUT_FOLDER}): ") or OUTPUT_FOLDER
            filename = input("Nome do arquivo CSV (transacoes_consolidadas.csv): ") or "transacoes_consolidadas.csv"
            
            csv_file = convert_json_to_csv_quick(json_path, output_path, filename)
            if csv_file:
                print(f"\n🎉 Conversão concluída! Arquivo: {csv_file}")
        
        elif choice == "4":
            filename = input("Nome do arquivo CSV: ")
            if filename and not filename.endswith('.csv'):
                filename += '.csv'
            
            csv_file = convert_json_to_csv_quick(JSON_FOLDER, OUTPUT_FOLDER, filename)
            if csv_file:
                print(f"\n🎉 Conversão concluída! Arquivo: {csv_file}")
        
        else:
            print("❌ Opção inválida!")
    
    except Exception as e:
        print(f"❌ Erro durante a conversão: {str(e)}")