{
    'name': 'Inventario Avanzado (Feral Tech)',
    'version': '16.0.3.0.0',
    'category': 'Inventory/Reporting',
    'summary': 'Reportes avanzados de rotación de inventarios y planeación de compras.',
    'description': """
        Inventario Avanzado - Feral Tech
        =================================
        Módulo de reportes avanzados que incluye:
        - Reporte de Rotación de Inventarios con rango de fechas dinámico
        - Sistema de Flags configurable por producto
        - Planeación de Compras con forecast logístico editable
        - Sistema de licenciamiento con verificación de integridad
    """,
    'author': 'Feral Tech',
    'website': 'https://feraltech.co',
    'license': 'OPL-1',
    'depends': [
        'purchase_stock',
        'account',
        'feral_tech_base',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/product_flag_config_views.xml',
        'views/purchase_planning_views.xml',
        'views/res_config_settings_views.xml',
        'wizard/inventory_rotation_wizard_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
