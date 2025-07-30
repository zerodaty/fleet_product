from odoo.tests.common import TransactionCase
from odoo.exceptions import UserError 

class TestServiceTotalCost(TransactionCase):

    def setUp(self):
        """
        Método de preparación. Se ejecuta antes de cada prueba.
        Ideal para crear registros que usaremos en múltiples tests.
        """
        super().setUp()
        # Creamos los registros base para no repetirlos en cada test
        self.VehicleModel = self.env['fleet.vehicle.model']
        test_model = self.VehicleModel.create({
            'name': 'Test Model Car',
            'brand_id': self.env['fleet.vehicle.model.brand'].create({'name': 'Test Brand'}).id
        })
        self.test_vehicle = self.env['fleet.vehicle'].create({
            'model_id': test_model.id,
        })
        # Creamos también un producto que usaremos en las líneas
        self.test_product = self.env['product.product'].create({
            'name': 'Filtro de Aceite de Prueba'
        })

    def test_total_cost_calculation(self):
        '''
        Prueba el cálculo de 'amount' con costos de mano de obra y partes.
        '''
        # Registro de servicio principal
        service_record = self.env['fleet.vehicle.log.services'].create({
            'vehicle_id': self.test_vehicle.id,
            'labor_cost': 50.0,
        })

        service_record.write({
            'product_line_ids': [
                (0, 0, {'product_id': self.test_product.id, 'quantity': 2, 'price_unit': 25}), # Subtotal = 50
                (0, 0, {'product_id': self.test_product.id, 'quantity': 1, 'price_unit': 100}) # Subtotal = 100
            ]
        })
        # Odoo recalculará automáticamente `parts_cost` (50+100 = 150) y luego `amount`.

        # Total esperado = labor_cost (50) + parts_cost (150) = 200
        self.assertAlmostEqual(
            service_record.amount,
            200.0,
            msg="El costo total 'amount' no es la suma correcta de mano de obra y partes."
        )

        service_record.write({'labor_cost': 20.0})
        self.assertAlmostEqual(
            service_record.amount,
            170.0,
            msg="El 'amount' no se recalculó correctamente tras cambiar el labor_cost."
        )