from odoo import _, api, fields, models
from odoo.exceptions import UserError

INFINITY_DAYS = 9999.0


class InventoryRotationLocationPreset(models.Model):
    _name = 'inventory.rotation.location.preset'
    _description = 'Preset de Ubicaciones para Rotación'
    _order = 'name'

    name = fields.Char(string='Nombre', required=True)
    location_ids = fields.Many2many(
        'stock.location',
        'rotation_preset_location_rel',
        'preset_id',
        'location_id',
        string='Ubicaciones',
    )
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
    )


class InventoryRotationWizard(models.TransientModel):
    _name = 'inventory.rotation.wizard'
    _description = 'Wizard de Rotación de Inventarios'

    date_start = fields.Date(
        string='Fecha Inicio',
        required=True,
        default=fields.Date.today,
    )
    date_end = fields.Date(
        string='Fecha Fin',
        required=True,
        default=fields.Date.today,
    )
    include_future_incoming = fields.Boolean(
        string='Incluir Entrante Futuro',
        help='Permite extender la fecha de búsqueda de inventario entrante '
             'más allá del período de análisis de ventas.',
    )
    incoming_cutoff_date = fields.Date(
        string='Fecha Tope Entrante',
        help='Fecha límite para considerar órdenes de compra entrantes.',
    )
    filter_by_location = fields.Boolean(
        string='Filtrar por Ubicación',
    )
    location_ids = fields.Many2many(
        'stock.location',
        'rotation_wizard_location_rel',
        'wizard_id',
        'location_id',
        string='Ubicaciones',
        domain="[('usage', '=', 'internal'), ('company_id', '=', company_id)]",
    )
    location_preset_id = fields.Many2one(
        'inventory.rotation.location.preset',
        string='Preset',
        domain="[('company_id', '=', company_id)]",
    )
    preset_name = fields.Char(string='Nombre del Preset')
    company_id = fields.Many2one(
        'res.company',
        default=lambda self: self.env.company,
    )
    line_ids = fields.One2many(
        'inventory.rotation.report.line',
        'wizard_id',
        string='Líneas del Reporte',
    )

    @api.onchange('location_preset_id')
    def _onchange_location_preset_id(self):
        if self.location_preset_id:
            self.location_ids = self.location_preset_id.location_ids

    def action_select_all_locations(self):
        self.ensure_one()
        locations = self.env['stock.location'].search([
            ('usage', '=', 'internal'),
            ('company_id', '=', self.env.company.id),
        ])
        self.location_ids = [(6, 0, locations.ids)]
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_save_preset(self):
        self.ensure_one()
        if not self.preset_name:
            raise UserError(_('Ingrese un nombre para el preset.'))
        if not self.location_ids:
            raise UserError(_('Seleccione al menos una ubicación.'))
        preset = self.env['inventory.rotation.location.preset'].create({
            'name': self.preset_name,
            'location_ids': [(6, 0, self.location_ids.ids)],
        })
        self.location_preset_id = preset.id
        self.preset_name = False
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def action_generate_report(self):
        self.ensure_one()
        self.env['advanced.stock.reports.license'].check_license()

        if self.date_start > self.date_end:
            raise UserError(_('La fecha de inicio no puede ser posterior a la fecha fin.'))

        if self.include_future_incoming:
            if not self.incoming_cutoff_date:
                raise UserError(_('Debe indicar una fecha tope para el entrante futuro.'))
            if self.incoming_cutoff_date < self.date_end:
                raise UserError(_('La fecha tope del entrante debe ser igual o posterior a la fecha fin del período.'))

        self.line_ids.unlink()

        # Days-based period calculation for accurate monthly averages
        days_in_range = (self.date_end - self.date_start).days + 1

        # Get selected companies from context (multi-company support)
        allowed_company_ids = self.env.context.get('allowed_company_ids', [self.env.company.id])
        company_ids = tuple(allowed_company_ids)

        # Determine if filtering by specific locations
        use_locations = self.filter_by_location and self.location_ids
        loc_ids = tuple(self.location_ids.ids) if use_locations else None

        date_start_str = fields.Datetime.to_string(
            fields.Datetime.from_string(str(self.date_start) + ' 00:00:00')
        )
        date_end_str = fields.Datetime.to_string(
            fields.Datetime.from_string(str(self.date_end) + ' 23:59:59')
        )

        # --- 1. Outgoing (done moves, internal->customer minus customer->internal returns) ---
        if use_locations:
            self.env.cr.execute("""
                SELECT sm.product_id,
                       SUM(CASE
                           WHEN sm.location_id IN %s AND sl_dest.usage = 'customer'
                               THEN sm.product_uom_qty
                           WHEN sl_src.usage = 'customer' AND sm.location_dest_id IN %s
                               THEN -sm.product_uom_qty
                           ELSE 0
                       END) AS qty
                FROM stock_move sm
                JOIN stock_location sl_src ON sl_src.id = sm.location_id
                JOIN stock_location sl_dest ON sl_dest.id = sm.location_dest_id
                WHERE sm.state = 'done'
                  AND (
                      (sm.location_id IN %s AND sl_dest.usage = 'customer')
                      OR (sl_src.usage = 'customer' AND sm.location_dest_id IN %s)
                  )
                  AND sm.date >= %s
                  AND sm.date <= %s
                  AND sm.company_id IN %s
                GROUP BY sm.product_id
            """, (loc_ids, loc_ids, loc_ids, loc_ids,
                  date_start_str, date_end_str, company_ids))
        else:
            self.env.cr.execute("""
                SELECT sm.product_id,
                       SUM(CASE
                           WHEN sl_src.usage = 'internal' AND sl_dest.usage = 'customer'
                               THEN sm.product_uom_qty
                           WHEN sl_src.usage = 'customer' AND sl_dest.usage = 'internal'
                               THEN -sm.product_uom_qty
                           ELSE 0
                       END) AS qty
                FROM stock_move sm
                JOIN stock_location sl_src ON sl_src.id = sm.location_id
                JOIN stock_location sl_dest ON sl_dest.id = sm.location_dest_id
                WHERE sm.state = 'done'
                  AND (
                      (sl_src.usage = 'internal' AND sl_dest.usage = 'customer')
                      OR (sl_src.usage = 'customer' AND sl_dest.usage = 'internal')
                  )
                  AND sm.date >= %s
                  AND sm.date <= %s
                  AND sm.company_id IN %s
                GROUP BY sm.product_id
            """, (date_start_str, date_end_str, company_ids))
        outgoing_map = {r[0]: r[1] for r in self.env.cr.fetchall()}

        # --- 2. Incoming pending (not done, destination internal) ---
        # Use extended date range if future incoming is enabled
        if self.include_future_incoming and self.incoming_cutoff_date:
            incoming_end_str = fields.Datetime.to_string(
                fields.Datetime.from_string(str(self.incoming_cutoff_date) + ' 23:59:59')
            )
        else:
            incoming_end_str = date_end_str

        if use_locations:
            self.env.cr.execute("""
                SELECT sm.product_id, SUM(sm.product_uom_qty) AS qty
                FROM stock_move sm
                WHERE sm.state NOT IN ('done', 'cancel')
                  AND sm.location_dest_id IN %s
                  AND sm.date >= %s
                  AND sm.date <= %s
                  AND sm.company_id IN %s
                GROUP BY sm.product_id
            """, (loc_ids, date_start_str, incoming_end_str, company_ids))
        else:
            self.env.cr.execute("""
                SELECT sm.product_id, SUM(sm.product_uom_qty) AS qty
                FROM stock_move sm
                JOIN stock_location sl_dest ON sl_dest.id = sm.location_dest_id
                WHERE sm.state NOT IN ('done', 'cancel')
                  AND sl_dest.usage = 'internal'
                  AND sm.date >= %s
                  AND sm.date <= %s
                  AND sm.company_id IN %s
                GROUP BY sm.product_id
            """, (date_start_str, incoming_end_str, company_ids))
        pending_map = {r[0]: r[1] for r in self.env.cr.fetchall()}

        # --- 3. Stock on hand (current qty_available from Odoo) ---
        all_product_ids = set(outgoing_map.keys()) | set(pending_map.keys())

        if use_locations:
            products_with_stock = self.env['product.product'].with_context(
                location=self.location_ids.ids
            ).search([('qty_available', '>', 0)])
        else:
            products_with_stock = self.env['product.product'].search([
                ('qty_available', '>', 0),
            ])
        all_product_ids |= set(products_with_stock.ids)

        stock_map = {}
        if all_product_ids:
            products = self.env['product.product'].browse(list(all_product_ids))
            if use_locations:
                products = products.with_context(location=self.location_ids.ids)
            for prod in products:
                stock_map[prod.id] = prod.qty_available

        # --- 4. Build report lines with flags ---
        company = self.env.company
        # Pre-fetch all custom flag configs to avoid N+1 queries
        custom_flags = {}
        flag_records = self.env['ft.advstock.product.flag'].search([
            ('product_id', 'in', list(all_product_ids)),
            ('company_id', '=', company.id),
        ])
        for rec in flag_records:
            custom_flags[rec.product_id.id] = rec

        lines_vals = []
        for product_id in all_product_ids:
            outgoing = outgoing_map.get(product_id, 0.0)
            pending = pending_map.get(product_id, 0.0)
            stock = stock_map.get(product_id, 0.0)

            # Average daily outgoing → monthly (30-day basis)
            outgoing_avg = (outgoing / days_in_range * 30) if days_in_range > 0 else 0.0

            # Rotation: (stock + incoming) / average monthly outgoing
            total_available = stock + pending
            if outgoing_avg > 0:
                rotation_months = total_available / outgoing_avg
                rotation_days = rotation_months * 30
            else:
                if total_available > 0:
                    rotation_days = INFINITY_DAYS
                    rotation_months = INFINITY_DAYS
                else:
                    rotation_days = 0.0
                    rotation_months = 0.0

            # Determine flag color and direction
            flag_rec = custom_flags.get(product_id)
            if flag_rec:
                y_min = flag_rec.ft_advstock_flag_yellow_min
                g_min = flag_rec.ft_advstock_flag_green_min
                g_max = flag_rec.ft_advstock_flag_green_max
                y_max = flag_rec.ft_advstock_flag_yellow_max
            else:
                y_min = company.ft_advstock_flag_yellow_min
                g_min = company.ft_advstock_flag_green_min
                g_max = company.ft_advstock_flag_green_max
                y_max = company.ft_advstock_flag_yellow_max

            rd = rotation_days
            if g_min <= rd <= g_max:
                flag_color = 'green'
                flag_direction = 'none'
            elif y_min <= rd < g_min:
                flag_color = 'yellow'
                flag_direction = 'down'
            elif g_max < rd <= y_max:
                flag_color = 'yellow'
                flag_direction = 'up'
            elif rd < y_min:
                flag_color = 'red'
                flag_direction = 'down'
            else:
                flag_color = 'red'
                flag_direction = 'up'

            lines_vals.append({
                'wizard_id': self.id,
                'product_id': product_id,
                'outgoing_qty': outgoing,
                'outgoing_avg': outgoing_avg,
                'incoming_pending_qty': pending,
                'stock_on_hand': stock,
                'rotation_months': rotation_months,
                'rotation_days': rotation_days,
                'flag_color': flag_color,
                'flag_direction': flag_direction,
            })

        self.env['inventory.rotation.report.line'].create(lines_vals)

        return {
            'name': _('Rotación de Inventarios (%s → %s)') % (self.date_start, self.date_end),
            'type': 'ir.actions.act_window',
            'res_model': 'inventory.rotation.report.line',
            'view_mode': 'tree',
            'domain': [('wizard_id', '=', self.id)],
            'target': 'current',
            'search_view_id': [self.env.ref(
                'ft_advstock.view_inventory_rotation_report_line_search'
            ).id, 'search'],
            'context': {
                'create': False,
                'edit': False,
            },
        }


class InventoryRotationReportLine(models.TransientModel):
    _name = 'inventory.rotation.report.line'
    _description = 'Línea de Reporte de Rotación'
    _order = 'rotation_months asc'

    NUMERIC_FIELDS = (
        'outgoing_qty', 'outgoing_avg', 'incoming_pending_qty',
        'stock_on_hand', 'rotation_months', 'rotation_days',
    )

    wizard_id = fields.Many2one('inventory.rotation.wizard', ondelete='cascade')
    product_id = fields.Many2one('product.product', string='Producto', readonly=True)
    product_tmpl_id = fields.Many2one(
        related='product_id.product_tmpl_id',
        string='Plantilla',
        readonly=True,
        store=True,
    )
    categ_id = fields.Many2one(
        related='product_id.categ_id',
        string='Categoría',
        readonly=True,
        store=True,
    )
    flag_color = fields.Selection([
        ('green', 'Verde'),
        ('yellow', 'Amarillo'),
        ('red', 'Rojo'),
    ], string='Semáforo', readonly=True)
    flag_direction = fields.Selection([
        ('up', '↑'),
        ('down', '↓'),
        ('none', '—'),
    ], string='Tendencia', readonly=True)
    flag_display = fields.Char(
        string='Flag',
        compute='_compute_flag_display',
    )
    outgoing_qty = fields.Float(string='Saliente Total', readonly=True, digits=(16, 2))
    outgoing_avg = fields.Float(string='Saliente Prom./Mes', readonly=True, digits=(16, 2))
    incoming_pending_qty = fields.Float(string='Entrante Pendiente', readonly=True, digits=(16, 2))
    stock_on_hand = fields.Float(string='Stock a la Mano', readonly=True, digits=(16, 2))
    rotation_months = fields.Float(string='Rotación (Meses)', readonly=True, digits=(16, 2))
    rotation_days = fields.Float(string='Rotación (Días)', readonly=True, digits=(16, 2))

    @api.depends('flag_color', 'flag_direction')
    def _compute_flag_display(self):
        color_icons = {
            'green': '🟢',
            'yellow': '🟡',
            'red': '🔴',
        }
        direction_icons = {
            'up': ' ↑',
            'down': ' ↓',
            'none': '',
        }
        for rec in self:
            color = color_icons.get(rec.flag_color, '')
            direction = direction_icons.get(rec.flag_direction, '')
            rec.flag_display = f"{color}{direction}"

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """Dynamically adjust field digits based on company decimals setting."""
        res = super().fields_get(allfields, attributes)
        if not self.env.company.ft_advstock_use_decimals:
            for field_name in self.NUMERIC_FIELDS:
                if field_name in res:
                    res[field_name]['digits'] = [16, 0]
        return res

    @api.model
    def _format_values(self, values_list):
        """Round values to integers when decimals are off."""
        if not values_list:
            return values_list
        if not self.env.company.ft_advstock_use_decimals:
            for vals in values_list:
                for field_name in self.NUMERIC_FIELDS:
                    if field_name in vals and vals[field_name] is not None:
                        vals[field_name] = int(round(vals[field_name]))
        return values_list

    @api.model
    def search_read(self, domain=None, fields=None, offset=0, limit=None, order=None):
        """Apply formatting to search_read results."""
        result = super().search_read(domain, fields, offset, limit, order)
        return self._format_values(result)

    @api.model
    def read_group(self, domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True):
        """Apply formatting to read_group results (aggregations)."""
        result = super().read_group(domain, fields, groupby, offset, limit, orderby, lazy)
        if not self.env.company.ft_advstock_use_decimals:
            for group in result:
                for field_name in self.NUMERIC_FIELDS:
                    if field_name in group and group[field_name] is not None:
                        group[field_name] = int(round(group[field_name]))
        return result
