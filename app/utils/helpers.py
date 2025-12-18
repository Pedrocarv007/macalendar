"""
Utilitários e funções auxiliares
"""
import os
import random
import re
import uuid
from datetime import datetime, date
from PIL import Image

def generate_unique_filename(original_filename, prefix="file"):
    """Gerar nome único para arquivo"""
    timestamp = int(datetime.now().timestamp())
    unique_id = str(uuid.uuid4())[:8]
    
    if '.' in original_filename:
        name, ext = original_filename.rsplit('.', 1)
        return f"{prefix}_{timestamp}_{unique_id}.{ext.lower()}"
    else:
        return f"{prefix}_{timestamp}_{unique_id}"

def format_file_size(size_bytes):
    """Formatar tamanho do arquivo em formato legível"""
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"

def resize_image(image_path, max_width=800, max_height=600, quality=85):
    """Redimensionar imagem mantendo proporção"""
    try:
        with Image.open(image_path) as img:
            # Converter para RGB se necessário
            if img.mode in ('RGBA', 'LA', 'P'):
                img = img.convert('RGB')
            
            # Calcular novo tamanho mantendo proporção
            img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
            
            # Salvar imagem otimizada
            img.save(image_path, 'JPEG', optimize=True, quality=quality)
            
        return True
    except Exception as e:
        print(f"Erro ao redimensionar imagem: {e}")
        return False

def validate_date_format(date_string, format='%Y-%m-%d'):
    """Validar formato de data"""
    try:
        datetime.strptime(date_string, format)
        return True
    except ValueError:
        return False

def calculate_age(birth_date):
    """Calcular idade baseada na data de nascimento"""
    if isinstance(birth_date, str):
        birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
    
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))

def format_brazilian_phone(phone):
    """Formatar telefone no padrão brasileiro"""
    if not phone:
        return ""
    
    # Remover caracteres não numéricos
    clean_phone = re.sub(r'[^\d]', '', phone)
    
    # Formatar baseado no tamanho
    if len(clean_phone) == 11:
        return f"({clean_phone[:2]}) {clean_phone[2:7]}-{clean_phone[7:]}"
    elif len(clean_phone) == 10:
        return f"({clean_phone[:2]}) {clean_phone[2:6]}-{clean_phone[6:]}"
    else:
        return phone

def sanitize_string(text, max_length=None):
    """Sanitizar string removendo caracteres especiais"""
    if not text:
        return ""
    
    # Remover caracteres especiais mantendo acentos
    sanitized = re.sub(r'[<>"\'/\\]', '', text)
    
    # Limitar tamanho se especificado
    if max_length and len(sanitized) > max_length:
        sanitized = sanitized[:max_length]
    
    return sanitized.strip()

def get_next_birthday(birth_date):
    """Calcular próximo aniversário"""
    if isinstance(birth_date, str):
        birth_date = datetime.strptime(birth_date, '%Y-%m-%d').date()
    
    today = date.today()
    birthday_this_year = birth_date.replace(year=today.year)
    
    if birthday_this_year < today:
        return birth_date.replace(year=today.year + 1)
    return birthday_this_year

def days_until_birthday(birth_date):
    """Calcular dias até o próximo aniversário"""
    next_birthday = get_next_birthday(birth_date)
    return (next_birthday - date.today()).days

def format_datetime_br(dt, include_time=True):
    """Formatar datetime para padrão brasileiro"""
    if isinstance(dt, str):
        dt = datetime.fromisoformat(dt.replace('Z', '+00:00'))
    
    if include_time:
        return dt.strftime('%d/%m/%Y %H:%M')
    else:
        return dt.strftime('%d/%m/%Y')

def create_directory_if_not_exists(path):
    """Criar diretório se não existir"""
    try:
        os.makedirs(path, exist_ok=True)
        return True
    except Exception as e:
        print(f"Erro ao criar diretório {path}: {e}")
        return False

def get_file_extension(filename):
    """Obter extensão do arquivo"""
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()
    return ""

def is_image_file(filename):
    """Verificar se arquivo é uma imagem"""
    image_extensions = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp'}
    return get_file_extension(filename) in image_extensions

def generate_random_color():
    """Gerar cor hexadecimal aleatória"""
    return f"#{random.randint(0, 0xFFFFFF):06x}"

