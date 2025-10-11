import re
import csv
import os

def extract_transactions_from_ocr(file_path, tipo_venda="Crédito"):
    """Extrai transações do arquivo de OCR processado"""
    
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    # Extrair informações do cabeçalho
    arquivo_ref = re.search(r'=== (.+?) ===', content)
    arquivo_ref = arquivo_ref.group(1) if arquivo_ref else "N/A"
    
    # Extrair data (formato: dd mmm yyyy)
    data_match = re.search(r'(\d{1,2}\s+[a-z]{3}\.?\s+\d{4})', content, re.IGNORECASE)
    data_base = data_match.group(1) if data_match else "30 set. 2025"
    
    # Converter data para formato padrão
    meses = {
        'jan': '01', 'fev': '02', 'mar': '03', 'abr': '04', 
        'mai': '05', 'jun': '06', 'jul': '07', 'ago': '08',
        'set': '09', 'out': '10', 'nov': '11', 'dez': '12'
    }
    
    # Parse da data
    data_parts = data_base.replace('.', '').split()
    if len(data_parts) == 3:
        dia, mes_abr, ano = data_parts
        mes_num = meses.get(mes_abr.lower(), '01')
        data_formatada = f"{dia.zfill(2)}/{mes_num}/{ano}"
    else:
        data_formatada = "Não encontrado"
    
    # Extrair seção do texto principal
    # Procurar pela seção entre os marcadores
    inicio_marcador = "TEXTO EXTRAÍDO (MELHOR RESULTADO):"
    fim_marcador = "RESULTADOS DE TODAS AS CONFIGURAÇÕES:"
    
    inicio_pos = content.find(inicio_marcador)
    if inicio_pos == -1:
        # Tentar padrão mais flexível
        texto_secao = re.search(r'TEXTO EXTRAÍDO.*?:(.*?)(?:RESULTADOS|=+)', content, re.DOTALL | re.IGNORECASE)
        if texto_secao:
            texto_principal = texto_secao.group(1).strip()
        else:
            return []
    else:
        inicio_pos += len(inicio_marcador)
        fim_pos = content.find(fim_marcador, inicio_pos)
        if fim_pos == -1:
            # Se não encontrar o fim, pegar até o final
            texto_principal = content[inicio_pos:].strip()
        else:
            texto_principal = content[inicio_pos:fim_pos].strip()
    
    # Remove linhas de marcadores (==== etc)
    linhas = texto_principal.split('\n')
    linhas_filtradas = []
    for linha in linhas:
        if not re.match(r'^=+$', linha.strip()) and linha.strip():
            linhas_filtradas.append(linha)
    
    texto_principal = '\n'.join(linhas_filtradas)
    
    # Nova estratégia: extrair campos de forma independente e permitir campos vazios
    transacoes = []
    
    # Dividir o texto em linhas e processar
    linhas = texto_principal.split('\n')
    
    # Primeira passagem: identificar todas as ocorrências de valores e horários
    valores_encontrados = []
    horarios_encontrados = []
    horarios_processados = set()  # Para evitar duplicatas
    
    for i, linha in enumerate(linhas):
        linha = linha.strip()
        if not linha:
            continue
        
        # Procurar valores (incluindo os sem horários associados)
        valor_match = re.search(r'R\$\s*([\d,\.]+)', linha)
        if valor_match and not re.search(r'-R\$', linha):
            valor_str = valor_match.group(1)
            try:
                valor_float = float(valor_str.replace(',', '.'))
                # Só adicionar se maior que 2 reais
                if valor_float > 2.0:
                    valores_encontrados.append({
                        'linha': i,
                        'valor': valor_str,
                        'valor_float': valor_float
                    })
            except ValueError:
                continue
        
        # Procurar horários (incluindo os sem valores associados)
        # Definir horários válidos: 14:00 às 23:59
        horarios_validos = [14, 15, 16, 17, 18, 19, 20, 21, 22, 23]
        
        # Horário formato HH:MM
        horario_match = re.search(r'(\d{1,2}):(\d{2})', linha)
        if horario_match:
            hora = horario_match.group(1).zfill(2)
            minuto = horario_match.group(2)
            hora_int = int(hora)
            minuto_int = int(minuto)
            
            # Filtrar horários válidos na faixa permitida
            if hora_int in horarios_validos and minuto_int <= 59:
                hora_formatada = f"{hora}:{minuto}"
                # Evitar duplicatas baseado no horário e linha
                chave_horario = f"{hora_formatada}_{i}"
                if chave_horario not in horarios_processados:
                    horarios_processados.add(chave_horario)
                    horarios_encontrados.append({
                        'linha': i,
                        'hora': hora_formatada
                    })
        
        # Hora simples seguida de « ou .
        elif re.search(r'(\d{1,2})\s*[«.]', linha):
            hora_match = re.search(r'(\d{1,2})\s*[«.]', linha)
            if hora_match:
                hora = hora_match.group(1).zfill(2)
                hora_int = int(hora)
                # Filtrar apenas horas válidas na faixa permitida
                if hora_int in horarios_validos:
                    hora_formatada = f"{hora}:00"
                    # Evitar duplicatas baseado no horário e linha
                    chave_horario = f"{hora_formatada}_{i}"
                    if chave_horario not in horarios_processados:
                        horarios_processados.add(chave_horario)
                        horarios_encontrados.append({
                            'linha': i,
                            'hora': hora_formatada
                        })
    
    # Segunda passagem: associar valores com horários próximos
    horarios_usados_no_arquivo = set()  # Para evitar horários duplicados no mesmo arquivo
    horarios_validos = [14, 15, 16, 17, 18, 19, 20, 21, 22, 23]
    
    for valor_info in valores_encontrados:
        valor_linha = valor_info['linha']
        valor_str = valor_info['valor']
        
        # Procurar horário mais próximo (dentro de 3 linhas de distância)
        hora_encontrada = "não encontrado"
        melhor_distancia = float('inf')
        melhor_horario_info = None
        
        for horario_info in horarios_encontrados:
            horario_linha = horario_info['linha']
            distancia = abs(horario_linha - valor_linha)  # Distância absoluta
            hora = horario_info['hora']
            
            # Verificar se é um horário válido e não foi usado ainda neste arquivo
            hora_int = int(hora.split(':')[0])
            if hora_int in horarios_validos and hora not in horarios_usados_no_arquivo:
                # Horário deve estar a no máximo 3 linhas de distância
                if distancia <= 3 and distancia < melhor_distancia:
                    hora_encontrada = hora
                    melhor_distancia = distancia
                    melhor_horario_info = horario_info
        
        # Se encontrou um horário válido, marcar como usado
        if melhor_horario_info:
            horarios_usados_no_arquivo.add(hora_encontrada)
        
        # Sempre adicionar a transação, mesmo se horário for "não encontrado"
        transacao = {
            'Data': data_formatada,
            'Hora': hora_encontrada,
            'Valor': f"R$ {valor_str}",
            'Tipo de Venda': tipo_venda,
            'Arquivo de Referência': arquivo_ref
        }
        
        transacoes.append(transacao)
    
    # Terceira passagem: adicionar horários órfãos (sem valores associados) apenas se na faixa válida
    horarios_usados = set()
    horarios_validos = [14, 15, 16, 17, 18, 19, 20, 21, 22, 23]
    
    for transacao in transacoes:
        if transacao['Hora'] != "não encontrado":
            horarios_usados.add(transacao['Hora'])
    
    # Usar set para evitar adicionar horários órfãos duplicados
    horarios_orfaos_adicionados = set()
    
    for horario_info in horarios_encontrados:
        hora = horario_info['hora']
        hora_int = int(hora.split(':')[0])
        
        # Só adicionar horários órfãos se na faixa válida e não foram usados
        if (hora_int in horarios_validos and 
            hora not in horarios_usados and 
            hora not in horarios_orfaos_adicionados):
            
            # Horário órfão - adicionar como transação com valor não encontrado
            transacao = {
                'Data': data_formatada,
                'Hora': hora,
                'Valor': "não encontrado",
                'Tipo de Venda': tipo_venda,
                'Arquivo de Referência': arquivo_ref
            }
            
            transacoes.append(transacao)
            horarios_orfaos_adicionados.add(hora)
    
    # Ordenar transações por horário (colocar "não encontrado" no final)
    def sort_key(t):
        if t['Hora'] == "não encontrado":
            return "99:99"  # Colocar no final
        elif t['Valor'] == "não encontrado":
            return f"{t['Hora']}_orphan"  # Horários órfãos depois dos valores
        return t['Hora']
    
    transacoes.sort(key=sort_key)
    
    return transacoes

def save_to_csv(transacoes, output_file):
    """Salva as transações em arquivo CSV"""
    
    if not transacoes:
        print("Nenhuma transação encontrada.")
        return
    
    fieldnames = ['Data', 'Hora', 'Valor', 'Tipo de Venda', 'Arquivo de Referência']
    
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=';')
        writer.writeheader()
        writer.writerows(transacoes)
    
    print(f"Arquivo CSV criado: {output_file}")
    print(f"Total de transações: {len(transacoes)}")

def process_all_card_files(tipo_cartao="credito"):
    """Processa todos os arquivos de cartão (crédito ou débito) na pasta"""
    import glob
    
    # Definir configurações baseadas no tipo de cartão
    if tipo_cartao.lower() == "credito":
        input_subdir = "credit"
        file_pattern = "credito*_raw.txt"
        output_filename = "transacoes_credito.csv"
        tipo_venda = "Crédito"
    elif tipo_cartao.lower() == "debito":
        input_subdir = "debit"
        file_pattern = "debito*_raw.txt"
        output_filename = "transacoes_debito.csv"
        tipo_venda = "Débito"
    else:
        print("❌ Tipo de cartão inválido. Use 'credito' ou 'debito'")
        return
    
    base_dir = r"e:\MYAREA\AREA_DEV\PROJECTS\PastelariaVinny_Navegantes\outputs\ocr_results\cards"
    input_dir = os.path.join(base_dir, input_subdir)
    output_dir = r"e:\MYAREA\AREA_DEV\PROJECTS\PastelariaVinny_Navegantes\outputs\reports"
    
    # Verificar se o diretório existe
    if not os.path.exists(input_dir):
        print(f"❌ Diretório não encontrado: {input_dir}")
        return
    
    # Buscar todos os arquivos do tipo especificado
    card_files = glob.glob(os.path.join(input_dir, file_pattern))
    
    if not card_files:
        print(f"❌ Nenhum arquivo {file_pattern} encontrado em {input_dir}")
        return
    
    print(f"🔍 Processando arquivos de {tipo_cartao.upper()}...")
    print(f"📁 Diretório: {input_dir}")
    print(f"📄 Arquivos encontrados: {len(card_files)}")
    print("-" * 50)
    
    all_transactions = []
    processed_files = 0
    
    for file_path in card_files:
        try:
            print(f"Processando: {os.path.basename(file_path)}")
            transactions = extract_transactions_from_ocr(file_path, tipo_venda)
            all_transactions.extend(transactions)
            processed_files += 1
            print(f"  -> {len(transactions)} transações encontradas (valores > R$ 2,00)")
        except Exception as e:
            print(f"  -> Erro ao processar {file_path}: {e}")
    
    # Salvar todas as transações em um único CSV
    if all_transactions:
        output_file = os.path.join(output_dir, output_filename)
        save_to_csv(all_transactions, output_file)
        print("\n✅ Processamento concluído!")
        print(f"💳 Tipo de cartão: {tipo_cartao.upper()}")
        print(f"📁 Arquivos processados: {processed_files}")
        print(f"� Total de transações válidas: {len(all_transactions)} (valores > R$ 2,00)")
        print(f"📄 Arquivo gerado: {output_file}")
    else:
        print("❌ Nenhuma transação encontrada em todos os arquivos.")

def main():
    """Processa arquivos de cartão baseado nos argumentos fornecidos"""
    import sys
    
    # Verificar argumentos da linha de comando
    if len(sys.argv) < 2:
        print("🔧 Uso do script:")
        print("  python txt_to_csv.py --credito    # Processar apenas cartões de crédito")
        print("  python txt_to_csv.py --debito     # Processar apenas cartões de débito")
        print("  python txt_to_csv.py --all        # Processar crédito E débito")
        print("\n❌ Nenhum argumento fornecido. Processando crédito por padrão...")
        process_all_card_files("credito")
        return
    
    arg = sys.argv[1].lower()
    
    if arg == "--credito":
        print("🎯 Modo: Processando apenas CRÉDITO")
        process_all_card_files("credito")
    elif arg == "--debito":
        print("🎯 Modo: Processando apenas DÉBITO")
        process_all_card_files("debito")
    elif arg == "--all":
        print("🎯 Modo: Processando CRÉDITO e DÉBITO")
        print("\n" + "="*60)
        print("🔵 INICIANDO PROCESSAMENTO DE CRÉDITO")
        print("="*60)
        process_all_card_files("credito")
        
        print("\n" + "="*60)
        print("🟡 INICIANDO PROCESSAMENTO DE DÉBITO")
        print("="*60)
        process_all_card_files("debito")
        
        print("\n" + "="*60)
        print("✅ PROCESSAMENTO COMPLETO FINALIZADO!")
        print("="*60)
    else:
        print(f"❌ Argumento inválido: {arg}")
        print("✅ Argumentos válidos: --credito, --debito, --all")
    
if __name__ == "__main__":
    main()