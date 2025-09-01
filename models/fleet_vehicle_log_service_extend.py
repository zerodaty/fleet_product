# -*- coding: utf-8 -*-
from odoo import models, fields, api, Command
from odoo.exceptions import UserError

class FleetVehicleLogServices(models.Model):
    """
    Heredamos el modelo de servicios de flota para agregar campos
    y lógica de negocio relacionados con los costos de productos.
    """
    
    _inherit = 'fleet.vehicle.log.services'

    service_classification = fields.Selection(
        [
            ('preventive', 'Preventivo'),
            ('corrective', 'Correctivo')
        ],
        string='Clasificación de Servicio',
        default='preventive',
        required=True
    )

    # --- Campos de Costos ---

    # El costo de la mano de obra.
    labor_cost = fields.Monetary(
        'Costo de Mano de Obra',
        tracking=True 
    )

    # El One2many hacia nuestras líneas de producto.
    product_line_ids = fields.One2many(
        'fleet.service.product.line', # El modelo al que nos conectamos
        'service_id',                 # El campo en ese modelo que apunta de vuelta aquí
        string='Productos Utilizados'
    )
    
    # El costo total de solo los productos.
    parts_cost = fields.Monetary(
        string='Costo de Productos',
        compute='_compute_parts_cost',
        store=True, # Lo guardamos para poder usarlo en el cómputo del total.
        tracking=True
    )
    
    # SOBREESCRIBIR CAMPO EXISTENTE: 'amount' ahora será nuestro total calculado.
    amount = fields.Monetary(
        'Costo Total',  
        compute='_compute_total_cost',
        store=True, 
        readonly=False, 
        inverse='_inverse_amount',
    )
    
       # Vainas pal seguro 
    insurance_policy_id = fields.Many2one(
        'fleet.vehicle.insurance',
        string='Póliza Utilizada',
        tracking=True
    )

    insurance_coverage_amount = fields.Monetary(
        string='Monto Cubierto por Seguro',
        tracking=True
    )
    
    net_cost = fields.Monetary(
        string='Costo Neto para la Empresa',
        compute='_compute_net_cost',
        store=True, # Importante para poder usarlo en informes
        tracking=True
    )
    
    vehicle_id_has_active_policies = fields.Boolean(
        related='vehicle_id.has_active_policies',
        string="El Vehículo Tiene Pólizas" # Etiqueta opcional para depuración
    )
    
    # Cambios para la logica de seleccion PRUEBA

    #Replantear el campo (NOTA estoy modificando algo que tal vez no vaya pal baile)
    
    purchaser_id = fields.Many2one(
        'res.partner',
        string="Driver", 
        domain=lambda self: self._get_drivers_with_vehicle_domain(),
    )
    
    
    
    
    #Replantear la logica de relacion de auto a conductor pa que sea de conductor a autos
    
    @api.onchange('purchaser_id')
    def _onchange_purchaser_id_set_vehicle(self):
        """
        CUANDO el usuario selecciona un conductor (`purchaser_id`) en el formulario,
        este método se dispara para buscar y asignar automáticamente el vehículo asociado.
        """
        # Solo si hay un conductor seleccionado.
        if self.purchaser_id:
            # Buscamos en el modelo 'fleet.vehicle'
            # que tenga este `res.partner` como su conductor actual.
            vehicle = self.env['fleet.vehicle'].search([
                ('driver_id', '=', self.purchaser_id.id)
            ], limit=1)

            if vehicle:
                self.vehicle_id = vehicle

    def _get_drivers_with_vehicle_domain(self):
       """
       Dominio para el campo purchaser_id
       Devuelve un filtro que es solo pa los que tienen carro TOCA REVISAR ESTA VAINA Pq no estoy seguro
       """
       vehicles_with_driver = self.env['fleet.vehicle'].search([('driver_id', '!=', False)])
       # Extraemos una lista de los IDs únicos de esos conductores.
       driver_ids = vehicles_with_driver.mapped('driver_id').ids
       # Construimos y devolvemos el dominio.
       return [('id', 'in', driver_ids)]

    # --- Cosa que agrege pal reporte ---
    
    sale_order_id = fields.Many2one(
        'sale.order', 
        string='Pedido de Venta', 
        readonly=True,
        copy=False,    # Al duplicar un servicio, no queremos que se copie el enlace al pedido anterior.
        tracking=True
    )
    insurer_sale_order_id = fields.Many2one(
        'sale.order', 
        string='Presupuesto Aseguradora', 
        readonly=True, 
        copy=False,
        tracking=True
    )
    sale_order_count = fields.Integer(
        string="Cuenta de Presupuestos", 
        compute='_compute_sale_order_count'
    )  
    
    # Para las fechas del kanban PROYECTO PROPIO
    
    estimated_delivery_date = fields.Date(
        string='Fecha de Entrega Estimada',
        tracking=True,  # Es útil ver si la fecha prometida cambia
        default=fields.Date.context_today
    )

    @api.depends('labor_cost', 'parts_cost')
    def _compute_total_cost(self):
        """
        Calcula el costo total sumando mano de obra y productos. 
        """
        for service in self:
            service.amount = service.labor_cost + service.parts_cost
    
            
    def _inverse_amount(self):
        """
        Método inverso para el campo 'amount'. Si alguien edita el 'Costo Total' manualmente, 
        la diferencia se asignará a 'Costo de Mano de Obra'.
        Esto mantiene la compatibilidad y un comportamiento intuitivo.
        """
        for service in self:
            # Si el total se edita, la mano de obra es la diferencia.
            service.labor_cost = service.amount - service.parts_cost
    
    # Logica pa el seguro
    
    @api.depends('amount', 'insurance_coverage_amount')
    def _compute_net_cost(self):
        """Calcula el costo real que asume la empresa."""
        for service in self:
            service.net_cost = service.amount - service.insurance_coverage_amount
            
    # AUTOMATIZAR LA BENDITA SELECCIÓN POR MILESIMA VEZ FUNCIONAAAAA AAAAAAAAAAAHHHH
    
    @api.onchange('vehicle_id', 'date')
    def _onchange_vehicle_set_policy(self):
        """
        Cuando se selecciona un vehículo, busca automáticamente la póliza propietaria
        más relevante (la que vence más tarde pero que ya está activa) y la propone.
        """
        if self.vehicle_id and self.date:
            # Buscamos pólizas para este vehículo, del tipo 'owner', que estén vigentes en la fecha del servicio.
            # Ordenamos por fecha de vencimiento descendente para obtener la más reciente.
            domain = [
                ('vehicle_id', '=', self.vehicle_id.id),
                ('policy_type', '=', 'owner'),
                ('start_date', '<=', self.date),
                ('end_date', '>=', self.date),
            ]
            relevant_policy = self.env['fleet.vehicle.insurance'].search(domain, order='end_date desc', limit=1)

            # Asignamos la póliza encontrada. Si no encuentra ninguna, asigna False (vacío).
            self.insurance_policy_id = relevant_policy
        else:
            # Si no hay vehículo o fecha, nos aseguramos de que el campo de póliza esté vacío.
            self.insurance_policy_id = False
            
    #---------------------------------------------------------#
    # Metodo que me dio chatGPT y que debo revisar (Pendiente)
    #---------------------------------------------------------#
    def action_create_sale_orders(self):
        """
        Este método se llama desde el botón 'Crear Presupuesto'.
        Crea un nuevo Pedido de Venta (sale.order) basado en los datos
        de este registro de servicio. REVISAR
        """
        self.ensure_one() # Asegura que solo se está ejecutando en un registro a la vez
    
            # --- VALIDACIONES DE NEGOCIO ---
        if self.sale_order_id or self.insurer_sale_order_id:
            raise UserError("Ya se han generado los documentos de venta para este servicio.")
        if not self.purchaser_id:
            raise UserError("Por favor, seleccione un 'Conductor / Cliente' antes de continuar.")
        
        # Validaciones específicas de la póliza de seguro
        if self.insurance_policy_id:
            if not (self.insurance_policy_id.start_date <= self.date <= self.insurance_policy_id.end_date):
                raise UserError("La fecha de este servicio está fuera del periodo de vigencia de la póliza de seguro seleccionada.")
            if self.insurance_coverage_amount > self.insurance_policy_id.cost:
                raise UserError(f"El monto de la cobertura del seguro ({self.insurance_coverage_amount}) no puede exceder el límite de la póliza ({self.insurance_policy_id.cost}).")
    
        # --- PREPARACIÓN DEL PRESUPUESTO PARA EL CLIENTE ---
        client_order_lines = []
        
        # Línea de Mano de Obra
        if self.labor_cost > 0:
            labor_product = self.env.ref('fleet_product.product_template_labor').product_variant_id
            client_order_lines.append(Command.create({
                'product_id': labor_product.id,
                'name': 'Mano de Obra del Servicio: ' + (self.description or ''),
                'product_uom_qty': 1,
                'price_unit': self.labor_cost
            }))
            
        # Líneas de Repuestos
        for line in self.product_line_ids:
            client_order_lines.append(Command.create({
                'product_id': line.product_id.id,
                'name': line.product_id.name,
                'product_uom_qty': line.quantity,
                'price_unit': line.product_id.list_price
            }))
            
        # Línea de Descuento por Seguro (si aplica)
        if self.insurance_coverage_amount > 0:
            adjustment_product = self.env.ref('fleet_product.product_template_insurance_adjustment').product_variant_id
            client_order_lines.append(Command.create({
                'product_id': adjustment_product.id,
                'name': f"Ajuste por Cobertura (Póliza: {self.insurance_policy_id.name})",
                'product_uom_qty': 1,
                'price_unit': -self.insurance_coverage_amount
            }))
            
        # --- CREACIÓN Y VINCULACIÓN DE LOS PRESUPUESTOS ---
        # Solo procedemos a crear si hay algo que facturar al cliente
        if not client_order_lines:
             raise UserError("No hay nada que facturar. Añada un costo de mano de obra o productos al servicio.")
    
        # Crear SO del Cliente
        client_so = self.env['sale.order'].create({
            'partner_id': self.purchaser_id.id,
            'order_line': client_order_lines,
            'origin': f"Servicio Flota: {self.description or ''}"
        })
        
        # Crear SO de la Aseguradora (si aplica)
        insurer_so = False
        if self.insurance_coverage_amount > 0:
            if not self.insurance_policy_id.insurer_id:
                raise UserError("La póliza debe tener una compañía aseguradora asociada para poder generar su presupuesto.")
            
            coverage_product = self.env.ref('fleet_product.product_template_insurance_coverage').product_variant_id
            insurer_so = self.env['sale.order'].create({
                'partner_id': self.insurance_policy_id.insurer_id.id,
                'order_line': [Command.create({
                    'product_id': coverage_product.id,
                    'name': f"Reclamo Cobertura - Servicio: {self.description or ''} ({self.vehicle_id.name})",
                    'product_uom_qty': 1,
                    'price_unit': self.insurance_coverage_amount,
                })],
                'origin': f"Servicio Flota: {self.description or ''}"
            })
    
        # Asignar los nuevos IDs al servicio EN UNA SOLA OPERACIÓN DE ESCRITURA
        vals_to_write = {'sale_order_id': client_so.id}
        if insurer_so:
            vals_to_write['insurer_sale_order_id'] = insurer_so.id
        
        self.write(vals_to_write)
        
        # NO RETORNAMOS NINGUNA ACCIÓN. El framework de Odoo simplemente recargará la vista.
        return True
    
    
    @api.onchange('vehicle_id')
    def _onchange_vehicle_id_set_contacts(self):
        # Cuando selecciono un vehículo, automáticamente propongo su conductor principal como el contacto del servicio.
        if self.vehicle_id:
            self.purchaser_id = self.vehicle_id.driver_id
        else:
            self.purchaser_id = False
        
    #-------------------------------------------
    # Nuevos Metodos para el 5.0 MODIFICACIONES 
    #-------------------------------------------------
    # En la clase FleetVehicleLogServices de tu archivo .py

    def action_in_progress(self):
        """ Cambia el estado del servicio a 'En Curso' y actualiza el estado operativo del vehículo. """
        self.ensure_one()

        state_available = self.env.ref('fleet_product.fleet_vehicle_state_available')
        state_in_workshop = self.env.ref('fleet_product.fleet_vehicle_state_in_workshop')

        # [CORRECCIÓN CLAVE]: Nos aseguramos de leer y escribir en NUESTRO campo 'operational_state_id'.
        if self.vehicle_id.operational_state_id == state_available:
            self.vehicle_id.write({'operational_state_id': state_in_workshop.id})

        self.write({'state': 'running'})
        return True

    def action_done(self):
        """ Finaliza el servicio y, si es el último, actualiza el estado operativo del vehículo. """
        self.ensure_one()
        if not self.sale_order_id:
            raise UserError("No se puede finalizar este servicio. Primero debe generar el 'Presupuesto' para el cliente.")

        vehicle = self.vehicle_id
        self.write({'state': 'done'})

        # Refrescamos el campo para obtener el valor actualizado después de la escritura
        vehicle.invalidate_recordset(['active_service_count'])

        if vehicle.active_service_count == 0:
            state_available = self.env.ref('fleet_product.fleet_vehicle_state_available')
            # [CORRECCIÓN CLAVE]: Escribimos en NUESTRO campo 'operational_state_id'.
            vehicle.write({'operational_state_id': state_available.id})

        return True

    def action_cancel(self):
        """ Cancela el servicio y los documentos asociados, y revisa el estado operativo del vehículo. """
        for service in self:
            vehicle = service.vehicle_id

            # Cancelamos los SOs
            if service.sale_order_id and service.sale_order_id.state != 'cancel':
                service.sale_order_id.action_cancel()
            if service.insurer_sale_order_id and service.insurer_sale_order_id.state != 'cancel':
               service.insurer_sale_order_id.action_cancel()

            service.write({'state': 'cancelled'})

            vehicle.invalidate_recordset(['active_service_count'])
            if vehicle.active_service_count == 0:
                state_available = self.env.ref('fleet_product.fleet_vehicle_state_available')
                # [CORRECCIÓN CLAVE]: Escribimos en NUESTRO campo 'operational_state_id'.
                vehicle.write({'operational_state_id': state_available.id})

        return True

    # def action_in_progress(self):
    #     """ Cambia el estado del servicio a 'En Curso'. """
    #     self.ensure_one()
    #     self.write({'state': 'running'})
    #     if self.vehicle_id.operational_state_id.id == self.env.ref('fleet_product.fleet_vehicle_state_available').id:
    #         state_in_workshop = self.env.ref('fleet_product.fleet_vehicle_state_in_workshop')
    #         self.vehicle_id.write({'operational_state_id': state_in_workshop.id})
    #     return True

    # def action_done(self):
    #     """ Finaliza el servicio. """
    #     self.ensure_one()
    #     # Validación: No se puede finalizar sin haber creado la documentación para el cliente
    #     if not self.sale_order_id:
    #         # Aquí podríamos crear un wizard, pero para empezar, un UserError es más rápido y cumple la función.
    #         raise UserError("No se puede finalizar este servicio. Primero debe generar el 'Presupuesto' para el cliente.")
    #     self.write({'state': 'done'})
    #     if self.vehicle_id.operational_state_id.id == self.env.ref('fleet_product.fleet_vehicle_state_available').id:
    #         state_in_workshop = self.env.ref('fleet_product.fleet_vehicle_state_in_workshop')
    #         self.vehicle_id.write({'operational_state_id': state_in_workshop.id})
    #     return True
        

    # def action_cancel(self):
    #     """ Cancela el servicio y los documentos asociados. """
    #     # Este método puede operar en múltiples registros a la vez si se quisiera
    #     for service in self:
            
    #         # Si hay un pedido de venta principal, lo cancelamos.
    #         if service.sale_order_id and service.sale_order_id.state != 'cancel':
    #             service.sale_order_id.action_cancel()
            
    #         # ¡ACTUALIZACIÓN 5.0! Ahora también cancela el SO de la aseguradora.
    #         if service.insurer_sale_order_id and service.insurer_sale_order_id.state != 'cancel':
    #            service.insurer_sale_order_id.action_cancel()
            
    #         service.write({'state': 'cancelled'})
    #     return True
    
      # --- MÉTODO COMPUTE PARA EL BOTÓN INTELIGENTE MODIFICACION 5.0---
    def _compute_sale_order_count(self):
        """ Cuenta cuántos pedidos de venta están vinculados a este servicio. """
        for service in self:
            count = 0
            if service.sale_order_id:
                count += 1
            if service.insurer_sale_order_id:
                count += 1
            service.sale_order_count = count
    
        # --- MÉTODO PARA EL BOTÓN INTELIGENTE M 5.0---
    def action_view_sale_orders(self):
        '''
        Función para mostrar los pedidos de venta generados por el servicio
        '''
        self.ensure_one()
        
        # Recopilamos los IDs de los pedidos de venta existentes
        domain = [('id', 'in', (self.sale_order_id.id, self.insurer_sale_order_id.id))]
        
        # Devolvemos una acción que muestra una lista (si hay > 1) o un formulario (si hay = 1)
        return {
            'name': 'Presupuestos Generados',
            'type': 'ir.actions.act_window',
            'res_model': 'sale.order',
            'view_mode': 'list,form',
            'domain': domain,
            'target': 'current',
        }
    # SOBRESCRIBIMOS EL MÉTODO DE CREACIÓN
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            # Si se está creando un servicio CON un vehículo...
            if 'vehicle_id' in vals:
                vehicle = self.env['fleet.vehicle'].browse(vals['vehicle_id'])
                last_odometer = vehicle.odometer
                new_odometer_val = vals.get('odometer', 0)

                # 1. Validación: El nuevo valor no puede ser menor que el último.
                if new_odometer_val < last_odometer:
                    raise UserError(
                        "Error: El valor del odómetro introducido (%s %s) es inferior al último valor registrado para este vehículo (%s %s)." %
                        (new_odometer_val, vehicle.odometer_unit, last_odometer, vehicle.odometer_unit)
                    )

                # 2. Replicamos la lógica del 'inverse': creamos el registro de odómetro.
                # Odoo espera un 'odometer_id', no un 'odometer'.
                if 'odometer' in vals:
                    odometer_log = self.env['fleet.vehicle.odometer'].create({
                        'value': new_odometer_val,
                        'date': vals.get('date', fields.Date.context_today(self)),
                        'vehicle_id': vehicle.id
                    })
                    # Reemplazamos el float por el ID del registro que acabamos de crear.
                    vals['odometer_id'] = odometer_log.id
                    # Borramos la clave original para no confundir al ORM.
                    del vals['odometer']

        # Llamamos al método de creación original con los valores ya procesados.
        return super().create(vals_list)


    # SOBRESCRIBIMOS EL MÉTODO DE ESCRITURA (EDICIÓN)
    def write(self, vals):
        # La misma lógica, pero para cuando se edita un registro existente.
        if 'odometer' in vals and self.vehicle_id:
            last_odometer = self.vehicle_id.odometer
            new_odometer_val = vals['odometer']
            
            # 1. Validación
            if new_odometer_val < last_odometer:
                # Comparamos con el penúltimo registro, porque el 'last_odometer' puede ser el que estamos editando
                previous_omdometers = self.env['fleet.vehicle.odometer'].search([('vehicle_id', '=', self.vehicle_id.id)], limit=2, order='value desc')
                if len(previous_omdometers) > 1 and new_odometer_val < previous_omdometers[1].value:
                     raise UserError(
                        "Error: El valor del odómetro introducido (%s %s) es inferior a un registro anterior para este vehículo (%s %s)." %
                        (new_odometer_val, self.odometer_unit, previous_omdometers[1].value, self.odometer_unit)
                    )

            # 2. Replicamos la lógica del 'inverse'
            if self.odometer != new_odometer_val:
                odometer_log = self.env['fleet.vehicle.odometer'].create({
                    'value': new_odometer_val,
                    'date': vals.get('date', self.date),
                    'vehicle_id': self.vehicle_id.id
                })
                vals['odometer_id'] = odometer_log.id
                del vals['odometer']
        
    # Metodo para evitar que se pueda mofidicar un servicio ya finalizado o cancelado
    def write(self, vals):
        # Validación de readonly para servicios cerrados
        for service in self:
            if service.state in ['done', 'cancelled'] and any(field in vals for field in ['vehicle_id', 'odometer', 'amount', 'labor_cost']):
                raise UserError("Acción no permitida: No se puede modificar un servicio que ya ha sido finalizado o cancelado.")

        # Lógica de escritura del odómetro
        if 'odometer' in vals and self.vehicle_id:
            if self.odometer != vals['odometer']:
                odometer_log = self.env['fleet.vehicle.odometer'].create({
                    'value': vals['odometer'],
                    'date': vals.get('date', self.date),
                    'vehicle_id': self.vehicle_id.id
                })
                vals['odometer_id'] = odometer_log.id
                del vals['odometer']
        
        return super(FleetVehicleLogServices, self).write(vals)
    
    
    # --- CAMPO DE CONTRATO PARA MANTENIMIENTO ---
    # Este campo permite vincular un contrato de mantenimiento específico al servicio. 
    contract_id = fields.Many2one(
        'account.analytic.account',
        string='Contrato Aplicado',
        tracking=True,
        # El dominio asegura que solo podamos elegir contratos del cliente del vehículo
        domain="[('partner_id', '=', vehicle_id.customer_id)]"
    )
    analytic_account_id = fields.Many2one(
        'account.analytic.account', 
        string='Cuenta Analítica',
        # Este campo debería ser de solo lectura para el usuario normal,
        # ya que lo rellenaremos automáticamente.
        readonly=True,
        copy=False, # No queremos copiar la cuenta analítica al duplicar un servicio
        help="Cuenta analítica vinculada al contrato aplicado, para seguimiento de costos."
    )
    
    @api.onchange('vehicle_id')
    def _onchange_vehicle_id_set_contacts_and_contract(self):
        if self.vehicle_id:
            # Lógica existente: proponer el contacto
            self.purchaser_id = self.vehicle_id.driver_id

            self.odometer = self.vehicle_id.odometer

            # Lógica existente: proponer el plan de mantenimiento
            self.contract_id = self.vehicle_id.maintenance_contract_id
    
            # ¡NUEVA LÓGICA DE RENTABILIDAD!
            # Copiamos el contrato a la cuenta analítica.
            self.analytic_account_id = self.vehicle_id.maintenance_contract_id
            
        else:
            self.purchaser_id = False
            self.contract_id = False
            self.analytic_account_id = False # Limpiamos también este campo
            
    @api.constrains('odometer', 'vehicle_id')
    def _check_odometer(self):
        for service in self:
            # Odoo ya calcula el último valor del odómetro en service.vehicle_id.odometer.
            # Simplemente validamos que nuestro nuevo valor no sea menor.
            # Añadimos una pequeña tolerancia (ej. 1 km) por si se trata de una corrección.
            if service.vehicle_id and service.odometer < service.vehicle_id.odometer:
                raise UserError(
                    "Error: El valor del odómetro introducido (%s %s) es inferior al último valor registrado para este vehículo (%s %s)." % 
                    (service.odometer, service.odometer_unit, service.vehicle_id.odometer, service.odometer_unit)
                )
            