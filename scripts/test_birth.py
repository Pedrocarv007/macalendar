from dotenv import load_dotenv
import os
import sys

# 1. Garante que o Python encontre a pasta 'app'
sys.path.append(os.getcwd())

load_dotenv()  

from app import create_app
from datetime import datetime
from sqlalchemy import extract
from app.models.employee import Employee
from app.models.restaurant import Restaurant
from app.utils.auto_templates import process_auto_generation
from app.utils.document_generator import DocumentGenerator
from app.models.workers import Worker

def run_monthly_automated_birthdays():
    generator = DocumentGenerator() 
    restaurant = Restaurant.query.first() 
    
    if not restaurant:
        print("❌ Nenhum restaurante encontrado.")
        return

    hoje = datetime.now()
    mes_atual = hoje.month
    
    emp_birthdays = Employee.query.filter(
        extract('month', Employee.birth_date) == mes_atual
    ).all()

    work_birthdays = Worker.query.filter(
        extract('month', Worker.birth_date) == mes_atual
    ).all()

    aniversariantes = emp_birthdays + work_birthdays

    for emp in aniversariantes:
       
        try:
            data_aniversario = emp.birth_date.replace(year=hoje.year)
        except ValueError: 
            # Caso raro: nasceu 29 de fevereiro em ano bissexto
            data_aniversario = emp.birth_date.replace(year=hoje.year, month=3, day=1)

        print(f"🚀 Gerando para: {emp.name} (Dia: {data_aniversario.strftime('%d/%m')})")
        
        
        process_auto_generation(
            strategy_key='aniversario',
            target=emp,
            restaurant=restaurant,
            photo_path=emp.photo_url,
            data={'data_evento': data_aniversario}, 
            generator=generator
        )

if __name__ == "__main__":
    app = create_app()
    with app.app_context():
        print("--- INICIANDO SCRIPT DE AUTOMAÇÃO ---")
        run_monthly_automated_birthdays()
        print("--- SCRIPT FINALIZADO ---")