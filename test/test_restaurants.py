"""Testes relacionados ao modelo Restaurant."""
from datetime import date

import pytest

from app import create_app
from app.extensions.database import db
from app.models.employee import Employee
from app.models.restaurant import Restaurant


@pytest.fixture
def app():
    """Aplicação de teste com banco em memória."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


def test_restaurant_to_dict_counts_active_employees(app):
    """to_dict deve contabilizar apenas colaboradores ativos."""
    with app.app_context():
        restaurant = Restaurant(name='Restaurante Teste', is_active=True)
        db.session.add(restaurant)
        db.session.commit()

        active_employee = Employee(
            name='Ativo',
            email='ativo@test.com',
            position='Garçom',
            birth_date=date(1990, 1, 1),
            restaurant_id=restaurant.id,
            is_active=True
        )
        active_employee.set_password('SenhaSegura1!')

        inactive_employee = Employee(
            name='Inativo',
            email='inativo@test.com',
            position='Chef',
            birth_date=date(1990, 1, 1),
            restaurant_id=restaurant.id,
            is_active=False
        )
        inactive_employee.set_password('SenhaSegura1!')

        db.session.add_all([active_employee, inactive_employee])
        db.session.commit()

        data = restaurant.to_dict()

        assert data['name'] == 'Restaurante Teste'
        assert data['employees_count'] == 1
        assert data['manager_name'] is None
