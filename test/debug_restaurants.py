from app import create_app
from app.models.restaurant import Restaurant

app = create_app()
app.app_context().push()

for r in Restaurant.query.all():
    data = r.to_dict()
    print(f'{r.name}: {data["employees_count"]} funcionários')
    print(f'  Restaurante ativo: {r.is_active}')
    print(f'  Funcionários na relação: {len(r.employees)}')
    for e in r.employees:
        print(f'    - {e.name} (ativo: {e.is_active})')
