import cv2
from pathlib import Path
import shutil

class ImageCropper:
    def __init__(self, crop_top=450):
        self.crop_top = crop_top
    
    def crop_single_image(self, input_path, output_path=None):
        """Recorta uma única imagem removendo os primeiros pixels do topo"""
        try:
            # Carrega a imagem
            img = cv2.imread(input_path)
            if img is None:
                raise ValueError(f"Não foi possível carregar a imagem: {input_path}")
            
            height, width = img.shape[:2]
            
            # Verifica se a imagem tem altura suficiente
            if height <= self.crop_top:
                print(f"⚠️  Aviso: Imagem {input_path} tem altura {height}px, menor que {self.crop_top}px")
                return False
            
            # Recorta a imagem (remove os primeiros crop_top pixels)
            cropped_img = img[self.crop_top:height, 0:width]
            
            # Define o caminho de saída
            if output_path is None:
                # Adiciona sufixo "_cropped" ao nome original
                path_obj = Path(input_path)
                output_path = path_obj.parent / f"{path_obj.stem}_cropped{path_obj.suffix}"
            
            # Salva a imagem recortada
            cv2.imwrite(str(output_path), cropped_img)
            
            print(f"✅ Recortada: {input_path}")
            print(f"   Original: {width}x{height} → Recortada: {width}x{height-self.crop_top}")
            print(f"   Salva em: {output_path}")
            
            return True
            
        except Exception as e:
            print(f"❌ Erro ao processar {input_path}: {str(e)}")
            return False
    
    def crop_folder_images(self, folder_path, output_folder=None, extensions=None):
        """Recorta todas as imagens de uma pasta"""
        if extensions is None:
            extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
        
        folder_path = Path(folder_path)
        
        if not folder_path.exists():
            raise FileNotFoundError(f"Pasta não encontrada: {folder_path}")
        
        # Define pasta de saída
        if output_folder is None:
            output_folder = folder_path / "cropped_images"
        else:
            output_folder = Path(output_folder)
        
        # Cria pasta de saída se não existir
        output_folder.mkdir(exist_ok=True)
        
        # Encontra todas as imagens
        image_files = []
        for ext in extensions:
            image_files.extend(folder_path.glob(f"*{ext}"))
            image_files.extend(folder_path.glob(f"*{ext.upper()}"))
        
        if not image_files:
            print(f"❌ Nenhuma imagem encontrada em: {folder_path}")
            return
        
        print(f"📁 Encontradas {len(image_files)} imagens para processar")
        print(f"📁 Pasta de saída: {output_folder}")
        print(f"✂️  Recortando {self.crop_top}px do topo de cada imagem...\n")
        
        success_count = 0
        
        for img_file in image_files:
            output_path = output_folder / img_file.name
            if self.crop_single_image(str(img_file), str(output_path)):
                success_count += 1
            print()  # Linha em branco para separar
        
        print(f"🎉 Processamento concluído!")
        print(f"✅ {success_count} imagens processadas com sucesso")
        print(f"❌ {len(image_files) - success_count} imagens falharam")
    
    def crop_and_replace(self, folder_path, backup=True, extensions=None):
        """Recorta e substitui as imagens originais (com backup opcional)"""
        if extensions is None:
            extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
        
        folder_path = Path(folder_path)
        
        if backup:
            backup_folder = folder_path / "backup_original"
            backup_folder.mkdir(exist_ok=True)
            print(f"📋 Backup será salvo em: {backup_folder}")
        
        # Encontra todas as imagens
        image_files = []
        for ext in extensions:
            image_files.extend(folder_path.glob(f"*{ext}"))
            image_files.extend(folder_path.glob(f"*{ext.upper()}"))
        
        print(f"📁 Encontradas {len(image_files)} imagens para processar")
        print(f"✂️  Recortando {self.crop_top}px do topo e substituindo originais...\n")
        
        success_count = 0
        
        for img_file in image_files:
            try:
                # Faz backup se solicitado
                if backup:
                    backup_path = backup_folder / img_file.name
                    shutil.copy2(str(img_file), str(backup_path))
                
                # Recorta e substitui
                if self.crop_single_image(str(img_file), str(img_file)):
                    success_count += 1
                
            except Exception as e:
                print(f"❌ Erro ao processar {img_file}: {str(e)}")
            
            print()
        
        print("🎉 Processamento concluído!")
        print(f"✅ {success_count} imagens processadas com sucesso")
        if backup:
            print(f"📋 Originais salvos em: {backup_folder}")


class ImageQuadrantDivider:
    def __init__(self, quadrant_width=1080, quadrant_height=250, first_quadrant_height=120):
        self.quadrant_width = quadrant_width
        self.quadrant_height = quadrant_height
        self.first_quadrant_height = first_quadrant_height
    
    def divide_single_image(self, input_path, output_folder=None):
        """Divide uma única imagem em quadrantes com dimensões específicas"""
        try:
            # Carrega a imagem
            img = cv2.imread(input_path)
            if img is None:
                raise ValueError(f"Não foi possível carregar a imagem: {input_path}")
            
            height, width = img.shape[:2]
            path_obj = Path(input_path)
            
            # Define pasta de saída
            if output_folder is None:
                output_folder = path_obj.parent / "quadrantes" / path_obj.stem
            else:
                output_folder = Path(output_folder) / path_obj.stem
            
            output_folder.mkdir(parents=True, exist_ok=True)
            
            print(f"🔄 Processando: {path_obj.name}")
            print(f"   Dimensões originais: {width}x{height}")
            print(f"   Pasta de saída: {output_folder}")
            
            quadrants_created = 0
            current_y = 0
            quadrant_num = 1
            
            while current_y < height:
                # Define altura do quadrante atual
                if quadrant_num == 1:
                    # Primeiro quadrante sempre tem altura especial
                    current_height = self.first_quadrant_height
                else:
                    # Demais quadrantes têm altura padrão
                    current_height = self.quadrant_height
                
                # Verifica se ainda há pixels suficientes
                remaining_height = height - current_y
                if remaining_height < current_height:
                    if remaining_height < 50:  # Se sobrar muito pouco, ignora
                        print(f"   ⚠️  Ignorando últimos {remaining_height}px (muito pequeno)")
                        break
                    else:
                        # Usa o que sobrou
                        current_height = remaining_height
                
                # Define coordenadas do quadrante
                y_start = current_y
                y_end = min(current_y + current_height, height)
                x_start = 0
                x_end = min(self.quadrant_width, width)
                
                # Extrai o quadrante
                quadrant = img[y_start:y_end, x_start:x_end]
                
                # Define nome do arquivo
                quadrant_filename = f"{path_obj.stem}_quadrante_{quadrant_num:02d}{path_obj.suffix}"
                quadrant_path = output_folder / quadrant_filename
                
                # Salva o quadrante
                cv2.imwrite(str(quadrant_path), quadrant)
                
                print(f"   📦 Quadrante {quadrant_num}: {x_end}x{y_end-y_start} → {quadrant_filename}")
                
                quadrants_created += 1
                current_y += current_height
                quadrant_num += 1
            
            print(f"   ✅ {quadrants_created} quadrantes criados\n")
            return quadrants_created
            
        except Exception as e:
            print(f"❌ Erro ao processar {input_path}: {str(e)}")
            return 0
    
    def divide_folder_images(self, folder_path, output_folder=None, extensions=None):
        """Divide todas as imagens de uma pasta em quadrantes"""
        if extensions is None:
            extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.webp']
        
        folder_path = Path(folder_path)
        
        if not folder_path.exists():
            raise FileNotFoundError(f"Pasta não encontrada: {folder_path}")
        
        # Define pasta de saída principal
        if output_folder is None:
            output_folder = folder_path / "quadrantes"
        else:
            output_folder = Path(output_folder)
        
        # Encontra todas as imagens
        image_files = []
        for ext in extensions:
            image_files.extend(folder_path.glob(f"*{ext}"))
            image_files.extend(folder_path.glob(f"*{ext.upper()}"))
        
        if not image_files:
            print(f"❌ Nenhuma imagem encontrada em: {folder_path}")
            return
        
        print(f"📁 Encontradas {len(image_files)} imagens para processar")
        print(f"📁 Pasta de saída principal: {output_folder}")
        print(f"🔧 Configuração dos quadrantes:")
        print(f"   - Primeiro quadrante: {self.quadrant_width}x{self.first_quadrant_height}")
        print(f"   - Demais quadrantes: {self.quadrant_width}x{self.quadrant_height}")
        print("=" * 50)
        
        success_count = 0
        total_quadrants = 0
        
        for img_file in image_files:
            quadrants = self.divide_single_image(str(img_file), str(output_folder))
            if quadrants > 0:
                success_count += 1
                total_quadrants += quadrants
        
        print("=" * 50)
        print("🎉 Processamento concluído!")
        print(f"✅ {success_count} imagens processadas com sucesso")
        print(f"📦 {total_quadrants} quadrantes criados no total")
        print(f"❌ {len(image_files) - success_count} imagens falharam")
    
    def get_quadrant_info(self, image_path):
        """Retorna informações sobre como a imagem seria dividida"""
        try:
            img = cv2.imread(image_path)
            if img is None:
                return None
            
            height, width = img.shape[:2]
            
            info = {
                'original_size': (width, height),
                'quadrants': [],
                'total_quadrants': 0
            }
            
            current_y = 0
            quadrant_num = 1
            
            while current_y < height:
                if quadrant_num == 1:
                    current_height = self.first_quadrant_height
                else:
                    current_height = self.quadrant_height
                
                remaining_height = height - current_y
                if remaining_height < current_height:
                    if remaining_height < 50:
                        break
                    else:
                        current_height = remaining_height
                
                y_end = min(current_y + current_height, height)
                x_end = min(self.quadrant_width, width)
                
                info['quadrants'].append({
                    'number': quadrant_num,
                    'coordinates': (0, current_y, x_end, y_end),
                    'size': (x_end, y_end - current_y)
                })
                
                current_y += current_height
                quadrant_num += 1
            
            info['total_quadrants'] = len(info['quadrants'])
            return info
            
        except Exception as e:
            print(f"Erro ao analisar {image_path}: {str(e)}")
            return None


# Função de conveniência
def crop_images_quick(folder_path, crop_pixels=450, replace_original=False):
    """Função rápida para recortar imagens"""
    cropper = ImageCropper(crop_top=crop_pixels)
    
    if replace_original:
        cropper.crop_and_replace(folder_path, backup=True)
    else:
        cropper.crop_folder_images(folder_path)


def divide_images_quick(folder_path, quadrant_width=1080, quadrant_height=250, first_height=125):
    """Função rápida para dividir imagens em quadrantes"""
    divider = ImageQuadrantDivider(
        quadrant_width=quadrant_width,
        quadrant_height=quadrant_height, 
        first_quadrant_height=first_height
    )
    divider.divide_folder_images(folder_path)


def preview_quadrant_division(image_path, quadrant_width=1080, quadrant_height=250, first_height=120):
    """Visualiza como uma imagem seria dividida sem processar"""
    divider = ImageQuadrantDivider(
        quadrant_width=quadrant_width,
        quadrant_height=quadrant_height,
        first_quadrant_height=first_height
    )
    
    info = divider.get_quadrant_info(image_path)
    
    if info is None:
        print(f"❌ Erro ao analisar a imagem: {image_path}")
        return
    
    print(f"📊 Análise da imagem: {Path(image_path).name}")
    print(f"   Tamanho original: {info['original_size'][0]}x{info['original_size'][1]}")
    print(f"   Total de quadrantes: {info['total_quadrants']}")
    print("\n📦 Quadrantes que serão criados:")
    
    for quad in info['quadrants']:
        size_str = f"{quad['size'][0]}x{quad['size'][1]}"
        coords = quad['coordinates']
        print(f"   {quad['number']:2d}. {size_str:>8s} - Coordenadas: ({coords[0]},{coords[1]}) → ({coords[2]},{coords[3]})")


def crop_and_divide_workflow(folder_path, crop_pixels=450, quadrant_width=1080, quadrant_height=250, first_height=120):
    """Fluxo completo: recorta e depois divide em quadrantes"""
    print("🔄 Iniciando fluxo completo: Recorte + Divisão em Quadrantes")
    print("=" * 60)
    
    # Etapa 1: Recortar imagens
    print("📍 ETAPA 1: Recortando imagens...")
    cropper = ImageCropper(crop_top=crop_pixels)
    cropper.crop_folder_images(folder_path)
    
    # Etapa 2: Dividir imagens recortadas em quadrantes
    print("\n📍 ETAPA 2: Dividindo imagens em quadrantes...")
    cropped_folder = Path(folder_path) / "cropped_images"
    
    if cropped_folder.exists():
        divide_images_quick(str(cropped_folder), quadrant_width, quadrant_height, first_height)
    else:
        print("❌ Pasta de imagens recortadas não encontrada!")
    
    print("\n🎉 Fluxo completo finalizado!")

if __name__ == "__main__":
    # Configure aqui o caminho para suas imagens
    PASTA_IMAGENS = r"data\raw\Imagens\cropped_images"
    
    print("🖼️  Sistema de Processamento de Imagens")
    print("=" * 50)
    
    opcao = input("""
Escolha uma opção:

📂 RECORTE (remove 450px do topo):
1 - Criar imagens recortadas (mantém originais)
2 - Substituir imagens originais (com backup)
3 - Recortar uma única imagem

📦 DIVISÃO EM QUADRANTES:
4 - Dividir imagens em quadrantes (1080x250, primeiro 1080x120)
5 - Visualizar como uma imagem seria dividida
6 - Configurar dimensões personalizadas dos quadrantes

🔄 FLUXO COMPLETO:
7 - Recortar E dividir em quadrantes (processo completo)

Digite sua opção (1-7): """)
    
    if opcao == "1":
        cropper = ImageCropper(crop_top=450)
        cropper.crop_folder_images(PASTA_IMAGENS)
    
    elif opcao == "2":
        confirm = input("⚠️  Isso vai substituir as imagens originais. Confirma? (s/n): ")
        if confirm.lower() == 's':
            cropper = ImageCropper(crop_top=450)
            cropper.crop_and_replace(PASTA_IMAGENS, backup=True)
    
    elif opcao == "3":
        img_path = input("Digite o caminho da imagem: ")
        cropper = ImageCropper(crop_top=450)
        cropper.crop_single_image(img_path)
    
    elif opcao == "4":
        divide_images_quick(PASTA_IMAGENS)
    
    elif opcao == "5":
        img_path = input("Digite o caminho da imagem para análise: ")
        preview_quadrant_division(img_path)
    
    elif opcao == "6":
        print("\n🔧 Configuração personalizada de quadrantes:")
        try:
            width = int(input("Largura dos quadrantes (padrão 1080): ") or "1080")
            height = int(input("Altura dos quadrantes normais (padrão 250): ") or "250")
            first_height = int(input("Altura do primeiro quadrante (padrão 120): ") or "120")
            
            print(f"\n📋 Configuração escolhida:")
            print(f"   - Largura: {width}px")
            print(f"   - Altura normal: {height}px")
            print(f"   - Altura do primeiro: {first_height}px")
            
            confirm = input("\nConfirma essa configuração? (s/n): ")
            if confirm.lower() == 's':
                divide_images_quick(PASTA_IMAGENS, width, height, first_height)
        except ValueError:
            print("❌ Valores inválidos inseridos!")
    
    elif opcao == "7":
        confirm = input("🔄 Isso vai executar o fluxo completo (recorte + quadrantes). Confirma? (s/n): ")
        if confirm.lower() == 's':
            crop_and_divide_workflow(PASTA_IMAGENS)
    
    else:
        print("❌ Opção inválida!")