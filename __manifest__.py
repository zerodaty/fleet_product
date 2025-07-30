{
        'name': "fleet_product",

        'summary': "Extension de Fleet",

        'description': 
        """
        Extension del modulo fleet para agregar Funcionalidad de:
        - Fleet como Productos
        - Servicios con Clasificacion (preventivo y correctivo) 
        - Servicios con producto de stock 
        - Seguro para los servicios
        - Alquiler de flotas
        """,

        'author': "Frany",
        'website': "https://github.com/zerodaty",
        'category': 'Services',
        'version': '5.0',
        'depends': ['base','fleet','account','product','sale','contacts','account_fleet','account_disallowed_expenses_fleet'],

        'data': [
            'security/ir.model.access.csv',
            'data/fleet_product_categories.xml',
            'data/fleet_product_productos.xml',
            'data/fleet_product_service.xml',
            'data/fleet_vehicle_state_data.xml',
            'report/fleet_service_report_templates.xml',
            'views/fleet_vehicle_log_services_views.xml',
            'views/fleet_vehicle_insurance_views.xml',
            'views/fleet_vehicle_view.xml',
        ],
        'demo': [
            'demo/demo.xml',
        ],
        'installable':True,
        'application':True,
        'license': 'LGPL-3',
}

