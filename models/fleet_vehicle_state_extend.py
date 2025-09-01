# models/fleet_vehicle_state_extend.py
from odoo import fields, models

class FleetVehicleState(models.Model):
    _inherit = 'fleet.vehicle.state'

    is_workshop_state = fields.Boolean(
        string="Es un Estado de Taller",
        default=False,
        help="Marcar esta casilla si el estado pertenece al flujo de trabajo del taller y no al ciclo de vida general del vehículo."
    )  