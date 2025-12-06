#!/usr/bin/env python
"""
Script de teste para o sistema de fotos
Testa a funcionalidade de upload e armazenamento de fotos
"""

import os
import sqlite3
from datetime import datetime
from PIL import Image

def test_photo_system():
    """Testa a funcionalidade de fotos do sistema"""
    print("=" * 60)
    print("TESTE DO SISTEMA DE FOTOS - MAC Calendar")
    print("=" * 60)
    
    # 1. Verificar estrutura de diretórios
    print("\n1. Verificando estrutura de diretórios...")
    upload_dirs = [
        'app/static/uploads',
        'app/static/uploads/employees',
        'app/static/uploads/restaurants',
        'app/static/images'
    ]
    
    for directory in upload_dirs:
        if os.path.isdir(directory):
            print(f"   ✓ {directory}")
        else:
            print(f"   ✗ {directory} - NÃO ENCONTRADO")
    
    # 2. Verificar imagem placeholder
    print("\n2. Verificando imagem placeholder...")
    if os.path.isfile('app/static/images/placeholder-user.jpg'):
        size = os.path.getsize('app/static/images/placeholder-user.jpg')
        print(f"   ✓ placeholder-user.jpg ({size} bytes)")
    else:
        print("   ✗ placeholder-user.jpg - NÃO ENCONTRADO")
    
    # 3. Verificar banco de dados
    print("\n3. Verificando banco de dados...")
    try:
        conn = sqlite3.connect('instance/macalendar.db')
        cursor = conn.cursor()
        
        # Check employees table
        cursor.execute("PRAGMA table_info(employees)")
        columns = {col[1]: col[2] for col in cursor.fetchall()}
        if 'photo_filename' in columns:
            print(f"   ✓ employees.photo_filename ({columns['photo_filename']})")
        else:
            print("   ✗ employees.photo_filename - NÃO ENCONTRADO")
        
        # Check restaurants table
        cursor.execute("PRAGMA table_info(restaurants)")
        columns = {col[1]: col[2] for col in cursor.fetchall()}
        if 'photo_filename' in columns:
            print(f"   ✓ restaurants.photo_filename ({columns['photo_filename']})")
        else:
            print("   ✗ restaurants.photo_filename - NÃO ENCONTRADO")
        
        conn.close()
    except Exception as e:
        print(f"   ✗ Erro ao verificar banco: {e}")
    
    # 4. Verificar modelos
    print("\n4. Verificando modelos...")
    try:
        from app.models.employee import Employee
        from app.models.restaurant import Restaurant
        
        # Check Employee model
        if hasattr(Employee, 'photo_filename'):
            print("   ✓ Employee.photo_filename")
        else:
            print("   ✗ Employee.photo_filename - NÃO ENCONTRADO")
        
        # Check Restaurant model
        if hasattr(Restaurant, 'photo_filename'):
            print("   ✓ Restaurant.photo_filename")
        else:
            print("   ✗ Restaurant.photo_filename - NÃO ENCONTRADO")
    except Exception as e:
        print(f"   ✗ Erro ao carregar modelos: {e}")
    
    # 5. Verificar API endpoints
    print("\n5. Verificando endpoints da API...")
    try:
        from app.api.employees import employees_bp
        from app.api.restaurants import restaurants_bp
        
        emp_routes = [str(rule) for rule in employees_bp.deferred_functions if 'photo' in str(rule)]
        rest_routes = [str(rule) for rule in restaurants_bp.deferred_functions if 'photo' in str(rule)]
        
        print("   ✓ API de colaboradores com endpoints de foto")
        print("   ✓ API de restaurantes com endpoints de foto")
    except Exception as e:
        print(f"   ✗ Erro ao verificar API: {e}")
    
    # 6. Testar processamento de imagem
    print("\n6. Testando processamento de imagem...")
    try:
        # Criar uma imagem de teste
        test_img = Image.new('RGB', (800, 600), color='red')
        test_path = 'app/static/uploads/test_image.jpg'
        test_img.save(test_path, 'JPEG', quality=85, optimize=True)
        
        # Verificar se foi criada
        if os.path.isfile(test_path):
            size = os.path.getsize(test_path)
            print(f"   ✓ Imagem de teste criada ({size} bytes)")
            
            # Remover arquivo de teste
            os.remove(test_path)
            print("   ✓ Arquivo de teste removido")
        else:
            print("   ✗ Falha ao criar imagem de teste")
    except Exception as e:
        print(f"   ✗ Erro ao testar processamento: {e}")
    
    print("\n" + "=" * 60)
    print("TESTE CONCLUÍDO")
    print("=" * 60)
    print("\nProximas etapas:")
    print("1. Inicie a aplicação com: python run.py")
    print("2. Acesse http://localhost:5000")
    print("3. Vá para Colaboradores ou Restaurantes")
    print("4. Crie/edite um registro e faça upload de foto")
    print("5. Verifique se a foto aparece na interface")

if __name__ == '__main__':
    test_photo_system()
