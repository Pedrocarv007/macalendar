from django.test import SimpleTestCase

from apps.restaurants.models import Restaurant


class RestaurantScopeTests(SimpleTestCase):
    def test_rafa_is_not_an_operational_calendar_restaurant(self):
        warehouse = Restaurant(name='Armazém Rafa', code='RAFA')
        sql = str(Restaurant.objects.all().query)

        self.assertIn('RAFA', sql)
        self.assertIn('NOT', sql.upper())
        self.assertTrue(warehouse.is_inventory_only)
