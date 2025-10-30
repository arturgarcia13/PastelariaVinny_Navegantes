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
        self.time_pattern = r'\b([0-9]?[0-9])[:°]([0-5][0-9])\b'
        self.value_pattern = r'R\$\s*([0-9]+[.,]?[0-9]*)'
    
    def convert_date_format(self, date_string: list) -> str:
        """
        Converte data do formato '29 set. 2025' para '29/09/2025'
        """
        # Tenta encontrar a primeira data válida na lista
        date_string_match = next((date for date in date_string if date and date != "Data não identificada"), None)
        
        # Retorna "Não encontrado" se nenhuma data válida for encontrada
        if not date_string_match:
            return "Não encontrado"
        
        # Remove pontos e normaliza espaços
        normalized = re.sub(r'\.', '', date_string_match.strip())
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
            
            # Verifica e ajusta se o primeiro número da hora é 7 ou 9
            if hour.startswith('7') or hour.startswith('9'):
                hour = '1' + hour[1:]
            
            hour, minute = hour.zfill(2), minute.zfill(2)
            
            # Verifica se o horário é válido
            if int(hour) < 24 and int(minute) < 60:
                return f"{hour}:{minute}"
            else:
                return f"{hour}:{minute} (ATENÇÃO)"
        
        return "Não encontrado"
    
    def convert_value_to_float(self, value_string: str) -> Optional[float]:
        """
        Converte valor monetário para float
        Ex: 'R$ 13,00' → 13.00 ou 'R$:7,73' → 7.73
        Procura especificamente por valores monetários, evitando conflito com horários
        """
        if not value_string:
            return "Não encontrado"
        
        # Estratégia 1: Busca valores com R$ explícito (mais seguro)
        r_dollar_patterns = [
            r'R\$\s*(\d{1,4})[.,](\d{2})',     # R$ 16,37 ou R$ 16.37
            r'R\$\.(\d{1,4})[.,](\d{2})',      # R$.16,37
            r'R\$(\d{1,4})[.,](\d{2})',        # R$16,37 (sem espaço)
            r'R\$\s*(\d{1,4})\s+(\d{2})',      # R$16 37 (espaço no lugar da vírgula)
        ]
        
        found_values = []
        
        for pattern in r_dollar_patterns:
            matches = re.findall(pattern, value_string, re.IGNORECASE)
            for match in matches:
                try:
                    if isinstance(match, tuple) and len(match) >= 2:
                        # Reconstrói o número (parte inteira, parte decimal)
                        value = float(f"{match[0]}.{match[1]}")
                        found_values.append(value)
                except (ValueError, IndexError):
                    continue
        
        # Estratégia 2: Busca padrões monetários sem R$ (mais restritiva para evitar horários)
        if not found_values:
            # Remove R$ e caracteres especiais, mas preserva contexto
            cleaned = re.sub(r'R\$[:\s\.]*', '', value_string)
            
            # Busca números com vírgula decimal (formato brasileiro) - menos provável de ser horário
            comma_decimal_matches = re.findall(r'\b(\d{1,4}),(\d{2})\b', cleaned)
            for match in comma_decimal_matches:
                try:
                    value = float(f"{match[0]}.{match[1]}")
                    # Filtros para evitar horários:
                    # - Valores de hora (00-23) com minutos (00-59) são suspeitos
                    if not (0 <= int(match[0]) <= 23 and 0 <= int(match[1]) <= 59):
                        found_values.append(value)
                    elif int(match[0]) > 23:  # Definitivamente não é hora
                        found_values.append(value)
                except (ValueError, IndexError):
                    continue
            
            # Busca números com ponto decimal (menos comum em horários brasileiros)
            if not found_values:
                dot_decimal_matches = re.findall(r'\b(\d{1,4})\.(\d{2})\b', cleaned)
                for match in dot_decimal_matches:
                    try:
                        value = float(f"{match[0]}.{match[1]}")
                        # Mesmo filtro para horários
                        if not (0 <= int(match[0]) <= 23 and 0 <= int(match[1]) <= 59):
                            found_values.append(value)
                        elif int(match[0]) > 23:
                            found_values.append(value)
                    except (ValueError, IndexError):
                        continue
        
        # Prioriza valores >= 1.0, depois pega o maior
        if found_values:
            # Remove duplicatas
            found_values = list(set(found_values))
            
            # Primeiro tenta encontrar valores >= 1.0
            valid_values = [v for v in found_values if v >= 1.0]
            if valid_values:
                return max(valid_values)  # Retorna o maior valor válido
            else:
                return max(found_values)  # Se só tem valores < 1, retorna o maior
        
        # Estratégia 3: Fallback mais conservador
        try:
            # Apenas se tem R$ explícito
            if 'R$' in value_string.upper():
                cleaned = re.sub(r'R\$[:\s]*', '', value_string, flags=re.IGNORECASE)
                cleaned = cleaned.strip().replace(',', '.')
                value = float(cleaned)
                return value
        except (ValueError, AttributeError):
            pass
        
        return "Não encontrado"
    
    def validate_minimum_value(self, value) -> Optional[float]:
        """
        Valida se o valor é maior que 1.00, caso contrário retorna "Não encontrado"
        """
        if isinstance(value, (int, float)):
            if value >= 1.0:
                return value
            else:
                # Valor menor que R$ 1,00 é considerado inválido
                return "Não encontrado"
        else:
            # Se não é numérico, mantém o valor original
            return value
    
    def extract_reference_filename(self, day_folder: str, quadrant_number: int) -> str:
        """
        Gera nome do arquivo de referência
        Ex: 'data/raw/ocr_results/agosto/debito/agosto_debito_001_data.json' + quadrante 2 → 'agosto_debito_001_data_quadrante_02'
        """
        day_folder_name = Path(day_folder).stem  # Obtém o nome do arquivo sem extensão
        return f"{day_folder_name}_quadrante_{quadrant_number:02d}"
    
    def process_single_json(self, json_file_path: Path) -> List[Dict]:
        """
        Processa um único arquivo JSON e extrai transações
        """
        transactions_data = []
        
        try:
            with open(json_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extrai informações do dia
            #day_folder = data.get('day_folder', '')
            date_info = [data.get('date_info', ''), data.get('header_text', '')]
            
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
                time_str = self.extract_time_from_text(raw_text)
                
                # Estratégia inteligente para conversão de valor
                # 1. Tenta primeiro o campo 'amount' do JSON
                value_float = None
                if amount_str:
                    value_float = self.convert_value_to_float(amount_str)
                    
                    # Se o valor do campo 'amount' for muito baixo, tenta o texto completo
                    if isinstance(value_float, (int, float)) and value_float < 1.0:
                        alternative_value = self.convert_value_to_float(processed_text)
                        if isinstance(alternative_value, (int, float)) and alternative_value > value_float:
                            value_float = alternative_value
                
                # 2. Se não havia 'amount' ou não conseguiu extrair, usa o texto completo
                if value_float is None or value_float == "Não encontrado":
                    value_float = self.convert_value_to_float(processed_text)
                
                # Aplica validação de valor mínimo
                value_float = self.validate_minimum_value(value_float)
                
                # Verifica se encontrou pelo menos alguns campos importantes
                # Pula transação se não tiver valor OU horário válidos
                has_valid_value = isinstance(value_float, (int, float)) and value_float >= 1.0
                has_valid_time = time_str != "Não encontrado"
                
                # Só adiciona se tiver pelo menos valor E horário, OU texto substancial
                if not (has_valid_value or has_valid_time):
                    continue  # Pula esta transação
                
                # Gera nome do arquivo de referência
                reference_file = self.extract_reference_filename(json_file_path, quadrant_num)
                
                # Adiciona transação válida
                transaction_row = {
                    'Data': formatted_date,
                    'Hora': time_str,
                    'Valor': value_float,
                    'Tipo de Venda': 'Débito',
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
        
        json_files = list(self.json_folder.glob("*_data.json"))
        
        # Ordena por índice no formato '001', '002', etc.
        def extract_index(file_path):
            match = re.search(r'(\d{3})', file_path.name)
            return int(match.group(1)) if match else 0
        
        json_files.sort(key=extract_index)
        
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
        
        # Extrai o mês e o tipo da pasta json_folder
        month = self.json_folder.parts[-2]  # Penúltima parte do caminho
        sale_type = self.json_folder.parts[-1]  # Última parte do caminho
        
        # Define o caminho de saída com subpastas
        output_file = self.output_folder / month / sale_type / filename
        
        # Cria as subpastas se não existirem
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
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
        
        # Extrai o mês e o tipo da pasta json_folder
        month = self.json_folder.parts[-2]  # Penúltima parte do caminho
        sale_type = self.json_folder.parts[-1]  # Última parte do caminho
        
        # Salva relatório
        report_file = self.output_folder / month / sale_type / "relatorio_estatisticas.txt"
        
        # Cria as subpastas se não existirem
        report_file.parent.mkdir(parents=True, exist_ok=True)
        
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
    JSON_FOLDER = r"data\raw\ocr_results\agosto\credito"
    OUTPUT_FOLDER = r"outputs\reports"
    
    print("💱 Conversor JSON → CSV para Transações")
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