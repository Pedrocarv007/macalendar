from app import create_app
from app.models.restaurant import Restaurant

app = create_app()
app.app_context().push()

try:
    restaurants = Restaurant.query.all()
    for r in restaurants:
        print(f"Restaurante: {r.name}")
        try:
            data = r.to_dict()
            print(f"  OK - {len(data)} campos")
        except Exception as e:
            print(f"  ERRO ao converter to_dict(): {str(e)}")
except Exception as e:
    print(f"ERRO ao carregar: {str(e)}")
    import traceback
    traceback.print_exc()
