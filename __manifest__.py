{
    'name': 'Inventario Avanzado (Feral Tech)',
    'version': '16.0.1.0.0',
    'category': 'Inventory/Reporting',
    'summary': 'Reportes avanzados de rotación de inventarios y planeación de reorden.',
    'description': """
        Inventario Avanzado - Feral Tech
        =================================
        Módulo de reportes avanzados que incluye:
        - Reporte de Rotación de Inventarios con rango de fechas dinámico
        - Planeación de Reorden (Próximamente)
        - Sistema de licenciamiento con verificación de integridad
    """,
    'author': 'Feral Tech',
    'website': 'https://feraltech.co',
    'license': 'OPL-1',
    'depends': [
        'purchase_stock',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'data/ir_cron.xml',
        'views/res_config_settings_views.xml',
        'wizard/inventory_rotation_wizard_views.xml',
        'wizard/reorder_planning_wizard_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
