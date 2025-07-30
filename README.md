# 🚗 Módulo Car Dealer para Odoo

Este módulo personalizado permite gestionar un concesionario de vehículos desde Odoo, aprovechando los modelos de `product`, `res.partner` y `sale` para crear un flujo completo de venta de autos.

## 📦 Características

- Registro completo de vehículos como productos.
- Gestión de marcas y características técnicas de autos.
- Asociación de vehículos a pedidos de venta.
- Seguimiento del estado del vehículo (`disponible`, `vendido`).
- Integración con clientes y su información adicional (licencia, cédula, preferencias).
- Posibilidad de ampliar con datos del módulo `fleet`.

## Estructura del Modulo

car_dealer/
├── **init**.py
├── **manifest**.py
├── models/
│ ├── **init**.py
│ ├── car_dealer_vehicle.py
│ ├── sale_order_extension.py
│ └── fleet_vehicle_extension.py
├── views/
│ ├── car_dealer_vehicle_views.xml
│ ├── sale_order_views.xml
│ └── fleet_vehicle_views.xml
├── security/
│ ├── ir.model.access.csv
│ └── security.xml

## 🔧 Requisitos

- Odoo 18.
- Módulos requeridos:
  - `base`
  - `product`
  - `sale`
  - `account`

## 🚀 Instalación

1. Clona el repositorio en tu carpeta de addons:
   git clone https://github.com/usuario/repositorio_addons.git

2. Instalalo dentro de tu odoo en la lista de aplicaciones

3. Disfruta
