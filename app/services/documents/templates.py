from datetime import datetime

def get_birthday_for_current_year(birth_date):
    if not birth_date: return None
    # birth_date pode vir como string ou objeto date
    if isinstance(birth_date, str):
        birth_date = datetime.strptime(birth_date, '%Y-%m-%d')
    
    today = datetime.now()
    try:
        return birth_date.replace(year=today.year)
    except ValueError: # Caso 29/02
        return birth_date.replace(year=today.year, day=28)

def get_strategies(target, restaurant, photo_path, data, generator):
    """
    Mapeia os tipos de documentos para os métodos da classe DocumentGenerator
    que você postou.
    """
    return {
        'bem_vindo': {
            'method': generator.generate_welcome_card,
            'category': 'Boas-vindas',
            'params': {
                'employee_name': target.name,
                'employee_photo_path': photo_path,
                'restaurant_id': restaurant.id
            }
        },
        'aniversario': {
            'method': generator.generate_birthday_card,
            'category': 'Aniversário',
            'params': {
                'employee_name': target.name,
                'birth_date': get_birthday_for_current_year(getattr(target, 'birth_date', None)),
                'employee_photo_path': photo_path,
                'restaurant_id': restaurant.id
            }
        },
        'funcionario_mes': {
            'method': generator.generate_employee_of_the_month_card,
            'category': 'Funcionário do Mês',
            'params': {
                'employee_name': target.name,
                'month_year': data.get('month_year') or data.get('mes_ano'),
                'reason': data.get('reason') or data.get('motivo'),
                'employee_photo_path': photo_path,
                'restaurant_id': restaurant.id
            }
        }
    }