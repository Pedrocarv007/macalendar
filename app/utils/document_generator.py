"""
Módulo para gerar documentos automaticamente usando PIL/Canva
Gera cartões de boas-vindas e aniversário
"""
from PIL import Image, ImageDraw, ImageFont
import os
from datetime import datetime
from pathlib import Path

class DocumentGenerator:
    """Gerador de documentos com templates"""
    
    def __init__(self):
        # Diretórios
        self.base_dir = Path(__file__).parent.parent.parent
        self.uploads_dir = self.base_dir / 'uploads' / 'generated'
        
        # Criar diretório se não existir
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_font(self, size=40):
        """Carregar fonte TTF ou retornar padrão"""
        font_paths = [
            '/Windows/Fonts/arial.ttf',
            'C:\\Windows\\Fonts\\arial.ttf',
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
            '/System/Library/Fonts/Arial.ttf'
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    return ImageFont.truetype(font_path, size)
                except:
                    continue
        
        # Fallback para fonte padrão PIL
        return ImageFont.load_default()
    
    def _get_template_image(self, template_name):
        """Obter imagem de template"""
        templates = {
            'bem_vindo': 'bem_vindo.png',
            'aniversario': 'aniversario.png',
            'welcome': 'bem_vindo.png',
            'birthday': 'aniversario.png'
        }
        
        filename = templates.get(template_name.lower(), 'bem_vindo.png')
        template_path = self.base_dir / filename
        
        if not os.path.exists(template_path):
            # Se não existir template, criar imagem em branco
            return Image.new('RGBA', (1920, 1280), color=(240, 240, 240, 255))
        
        return Image.open(template_path).convert('RGBA')
    
    def _apply_rounded_corners(self, image, radius=50):
        """Aplicar bordas arredondadas em imagem"""
        image = image.convert('RGBA')
        mask = Image.new('L', image.size, 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle([(0, 0), image.size], radius=radius, fill=255)
        image.putalpha(mask)
        return image
    
    def _get_or_create_placeholder(self, size=(400, 400)):
        """Obter ou criar imagem placeholder se não houver foto"""
        placeholder_path = self.base_dir / 'app' / 'static' / 'images' / 'placeholder-user.jpg'
        
        if os.path.exists(placeholder_path):
            try:
                return Image.open(placeholder_path).resize(size).convert('RGBA')
            except:
                pass
        
        # Criar placeholder em memória se não existir arquivo
        placeholder = Image.new('RGBA', size, color=(200, 200, 200, 255))
        draw = ImageDraw.Draw(placeholder)
        
        # Desenhar ícone de usuário simples
        # Círculo para cabeça
        draw.ellipse([80, 50, 320, 290], fill=(150, 150, 150, 255))
        # Retângulo para corpo
        draw.rectangle([100, 290, 300, 400], fill=(150, 150, 150, 255))
        
        return placeholder
    
    def generate_welcome_card(self, employee_name, employee_photo_path=None, restaurant_name=None):
        """Gerar cartão de boas-vindas - APENAS com foto, nome e data"""
        try:
            # Carregar template
            fundo = self._get_template_image('bem_vindo')
            largura, altura = fundo.size
            
            centro_x = largura // 2
            centro_y = altura // 2
            
            # Adicionar foto com tamanho exato (621x834)
            if employee_photo_path and os.path.exists(employee_photo_path):
                try:
                    foto = Image.open(employee_photo_path).resize((621, 834)).convert('RGBA')
                    foto_arredondada = self._apply_rounded_corners(foto, radius=50)
                    fundo.paste(foto_arredondada, (centro_x - 621 // 2, centro_y - 800 // 2 - 50), mask=foto_arredondada)
                except Exception as e:
                    print(f"Aviso ao carregar foto: {str(e)}")
            else:
                # Usar placeholder se não houver foto
                placeholder = self._get_or_create_placeholder((621, 834))
                placeholder_arredondado = self._apply_rounded_corners(placeholder, radius=50)
                fundo.paste(placeholder_arredondado, (centro_x - 621 // 2, centro_y - 800 // 2 - 50), mask=placeholder_arredondado)
            
            # Desenhar textos - APENAS nome
            draw = ImageDraw.Draw(fundo)
            
            try:
                fonte_nome = self._load_font(size=60)
                xmin, ymin, xmax, ymax = fonte_nome.getbbox(employee_name)
                largura_nome = xmax - xmin
                # Posição: centro_y + 400 (exatamente como no canva.py)
                draw.text((centro_x - largura_nome // 2, centro_y + 400), 
                         employee_name, font=fonte_nome, fill=(255, 255, 255, 255))
            except Exception as e:
                print(f"Aviso ao desenhar nome: {str(e)}")
            try:
                data = datetime.now().strftime('%d/%m/%Y')
                fonte_data = self._load_font(size=55)
                xmin, ymin, xmax, ymax = fonte_data.getbbox(data)
                largura_data = xmax - xmin
                # Posição: centro_y + 505 (exatamente como no canva.py para bem_vindo)
                draw.text((centro_x - largura_data // 2, centro_y + 505), 
                         data, font=fonte_data, fill=(255, 255, 255, 255))
            except Exception as e:
                print(f"Aviso ao desenhar data: {str(e)}")
            
            # Salvar
            filename = f"cartao_bemvindo_{int(datetime.now().timestamp())}.png"
            filepath = self.uploads_dir / filename
            fundo.save(str(filepath), 'PNG')
            
            return str(filepath), filename
            
        except Exception as e:
            print(f"Erro ao gerar cartão de boas-vindas: {str(e)}")
            raise
    
    def generate_birthday_card(self, employee_name, birth_date, employee_photo_path=None):
        """Gerar cartão de aniversário - APENAS com foto, nome e data"""
        try:
            # Carregar template
            fundo = self._get_template_image('aniversario')
            largura, altura = fundo.size
            
            centro_x = largura // 2
            centro_y = altura // 2
            
            # Adicionar foto com tamanho exato (621x834)
            if employee_photo_path and os.path.exists(employee_photo_path):
                try:
                    foto = Image.open(employee_photo_path).resize((621, 834)).convert('RGBA')
                    foto_arredondada = self._apply_rounded_corners(foto, radius=50)
                    fundo.paste(foto_arredondada, (centro_x - 621 // 2, centro_y - 800 // 2 - 50), mask=foto_arredondada)
                except Exception as e:
                    print(f"Aviso ao carregar foto: {str(e)}")
            else:
                # Usar placeholder se não houver foto
                placeholder = self._get_or_create_placeholder((621, 834))
                placeholder_arredondado = self._apply_rounded_corners(placeholder, radius=50)
                fundo.paste(placeholder_arredondado, (centro_x - 621 // 2, centro_y - 800 // 2 - 50), mask=placeholder_arredondado)
            
            # Desenhar textos - APENAS nome e data
            draw = ImageDraw.Draw(fundo)
            
            # Nome
            try:
                fonte_nome = self._load_font(size=60)
                xmin, ymin, xmax, ymax = fonte_nome.getbbox(employee_name)
                largura_nome = xmax - xmin
                # Posição: centro_y + 400 (exatamente como no canva.py)
                draw.text((centro_x - largura_nome // 2, centro_y + 400), 
                         employee_name, font=fonte_nome, fill=(255, 255, 255, 255))
            except Exception as e:
                print(f"Aviso ao desenhar nome: {str(e)}")
            
            # Data
            try:
                if isinstance(birth_date, str):
                    # Se vier como string (YYYY-MM-DD)
                    data_obj = datetime.strptime(birth_date, '%Y-%m-%d')
                else:
                    data_obj = birth_date
                
                data_str = data_obj.strftime('%d/%m/%Y')
                
                fonte_data = self._load_font(size=55)
                xmin, ymin, xmax, ymax = fonte_data.getbbox(data_str)
                largura_data = xmax - xmin
                # Posição: centro_y + 530 (exatamente como no canva.py para aniversario)
                draw.text((centro_x - largura_data // 2, centro_y + 530), 
                         data_str, font=fonte_data, fill=(255, 255, 255, 255))
            except Exception as e:
                print(f"Aviso ao desenhar data: {str(e)}")
            
            # Salvar
            filename = f"cartao_aniversario_{int(datetime.now().timestamp())}.png"
            filepath = self.uploads_dir / filename
            fundo.save(str(filepath), 'PNG')
            
            return str(filepath), filename
            
        except Exception as e:
            print(f"Erro ao gerar cartão de aniversário: {str(e)}")
            raise
    
    def generate_custom_card(self, title, employee_name, template='bem_vindo', 
                           additional_text=None, employee_photo_path=None):
        """Gerar cartão customizado - APENAS com foto, nome e data"""
        try:
            fundo = self._get_template_image(template)
            largura, altura = fundo.size
            
            centro_x = largura // 2
            centro_y = altura // 2
            
            # Adicionar foto com tamanho exato (621x834)
            if employee_photo_path and os.path.exists(employee_photo_path):
                try:
                    foto = Image.open(employee_photo_path).resize((621, 834)).convert('RGBA')
                    foto_arredondada = self._apply_rounded_corners(foto, radius=50)
                    fundo.paste(foto_arredondada, (centro_x - 621 // 2, centro_y - 800 // 2 - 50), mask=foto_arredondada)
                except Exception as e:
                    print(f"Aviso ao carregar foto: {str(e)}")
            else:
                # Usar placeholder se não houver foto
                placeholder = self._get_or_create_placeholder((621, 834))
                placeholder_arredondado = self._apply_rounded_corners(placeholder, radius=50)
                fundo.paste(placeholder_arredondado, (centro_x - 621 // 2, centro_y - 800 // 2 - 50), mask=placeholder_arredondado)
            
            draw = ImageDraw.Draw(fundo)
            
            # Nome
            try:
                fonte_nome = self._load_font(size=60)
                xmin, ymin, xmax, ymax = fonte_nome.getbbox(employee_name)
                largura_nome = xmax - xmin
                # Posição: centro_y + 400 (como no canva.py)
                draw.text((centro_x - largura_nome // 2, centro_y + 400), 
                         employee_name, font=fonte_nome, fill=(255, 255, 255, 255))
            except Exception as e:
                print(f"Aviso ao desenhar nome: {str(e)}")
            
            # Data (título é usado como data)
            try:
                fonte_data = self._load_font(size=55)
                xmin, ymin, xmax, ymax = fonte_data.getbbox(title)
                largura_data = xmax - xmin
                # Posição: centro_y + 530 (como no canva.py)
                draw.text((centro_x - largura_data // 2, centro_y + 530), 
                         title, font=fonte_data, fill=(255, 255, 255, 255))
            except Exception as e:
                print(f"Aviso ao desenhar data: {str(e)}")
            
            # Salvar
            filename = f"cartao_custom_{int(datetime.now().timestamp())}.png"
            filepath = self.uploads_dir / filename
            fundo.save(str(filepath), 'PNG')
            
            return str(filepath), filename
            
        except Exception as e:
            print(f"Erro ao gerar cartão customizado: {str(e)}")
            raise
