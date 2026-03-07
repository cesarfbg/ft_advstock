import base64
import io

from dateutil.relativedelta import relativedelta

from odoo import _, api, fields, models

MONTHS_WINDOW = 5  # 5 before + current + 5 after = 11
NUM_COLS = 2 * MONTHS_WINDOW + 1  # 11

ROW_TYPES = [
    ('initial_inventory', 'Inv. Inicial'),
    ('transit', 'Tránsito'),
    ('purchase_forecast', 'Pronóstico de Compras'),
    ('total', 'Inv. Total'),
    ('sales_forecast', 'Pronóstico de Ventas'),
    ('real_sales', 'Venta Real'),
    ('deviation', 'Desviación %'),
    ('final_inventory', 'Inv. Final'),
    ('rotation', 'Días de Inventario'),
]

EDITABLE_ROWS = {'sales_forecast', 'purchase_forecast'}
INFINITY = 9999.0

FLAG_SYMBOLS = {
    1: '🟢',
    2: '🟡↓',
    3: '🟡↑',
    4: '🔴↓',
    5: '🔴↑',
}


def _normalize_to_first(date):
    """Force any date to the 1st day of its month."""
    return date.replace(day=1) if date else date


def _compute_flag(rotation_days, y_min, g_min, g_max, y_max):
    """Return numeric flag code."""
    rd = rotation_days
    if g_min <= rd <= g_max:
        return 1  # Verde
    elif y_min <= rd < g_min:
        return 2  # Amarillo ↓
    elif g_max < rd <= y_max:
        return 3  # Amarillo ↑
    elif rd < y_min:
        return 4  # Rojo ↓
    else:
        return 5  # Rojo ↑


def _fmt(value, decimals=2):
    """Format a numeric value for cell display."""
    if decimals == 0:
        return str(int(round(value)))
    return f'{value:.{decimals}f}'


def _parse_float(text):
    """Parse a cell string back to float."""
    if not text:
        return 0.0
    # Strip any non-numeric suffix (flag emojis, %, ∞)
    cleaned = text.split(' ')[0].replace(',', '').replace('%', '').replace('∞', '')
    if not cleaned:
        return 0.0
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return 0.0


class PurchasePlanning(models.TransientModel):
    _name = 'ft.advstock.purchase.planning'
    _description = 'Planeación de Compras por Producto'
    _rec_name = 'product_id'

    product_id = fields.Many2one(
        'product.product', string='Producto',
        required=True,
    )
    product_categ_id = fields.Many2one(
        related='product_id.categ_id', string='Categoría',
    )
    product_display_name = fields.Char(
        compute='_compute_product_display_name',
    )
    company_id = fields.Many2one(
        'res.company', string='Compañía',
        required=True, default=lambda self: self.env.company,
    )
    center_date = fields.Date(
        string='Mes Central', required=True,
        default=lambda self: fields.Date.today().replace(day=1),
    )
    line_ids = fields.One2many(
        'ft.advstock.planning.line', 'planning_id',
        string='Líneas de Planeación',
    )

    @api.depends('product_id', 'product_id.name', 'product_id.default_code')
    def _compute_product_display_name(self):
        for rec in self:
            if rec.product_id:
                code = rec.product_id.default_code
                name = rec.product_id.name
                rec.product_display_name = '[%s] %s' % (code, name) if code else name
            else:
                rec.product_display_name = ''

    @api.onchange('center_date')
    def _onchange_center_date(self):
        if self.center_date:
            self.center_date = _normalize_to_first(self.center_date)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('center_date'):
                vals['center_date'] = _normalize_to_first(
                    fields.Date.to_date(vals['center_date'])
                )
        records = super().create(vals_list)
        for rec in records:
            rec._compute_planning_lines()
        return records

    def write(self, vals):
        if vals.get('center_date'):
            vals['center_date'] = _normalize_to_first(
                fields.Date.to_date(vals['center_date'])
            )
        return super().write(vals)

    # ------------------------------------------------------------------
    # Navigation & actions
    # ------------------------------------------------------------------

    @api.model
    def action_open_planning(self):
        """Server action entry point — always show product selector wizard."""
        self.env['advanced.stock.reports.license'].check_license()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ft.advstock.planning.product.wizard',
            'view_mode': 'form',
            'target': 'new',
        }

    def action_change_product(self):
        """Open the product-selector wizard."""
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'ft.advstock.planning.product.wizard',
            'view_mode': 'form',
            'target': 'new',
        }

    def _reload_form(self):
        """Return action to reload the current form with planning context."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'main',
            'context': {**self.env.context, 'planning_center_date': str(self.center_date)},
        }

    def action_prev(self):
        for rec in self:
            rec.center_date = rec.center_date - relativedelta(months=1)
        self._do_refresh()
        return self[:1]._reload_form()

    def action_next(self):
        for rec in self:
            rec.center_date = rec.center_date + relativedelta(months=1)
        self._do_refresh()
        return self[:1]._reload_form()

    def action_today(self):
        today_first = fields.Date.today().replace(day=1)
        for rec in self:
            rec.center_date = today_first
        self._do_refresh()
        return self[:1]._reload_form()

    def action_refresh(self):
        """User-triggered refresh — also equalizes sales forecast to real sales."""
        self._do_refresh()
        return self[:1]._reload_form()

    def action_clear_purchase_forecast(self):
        """Delete all purchase forecast records for the current product."""
        self.ensure_one()
        self.env['ft.advstock.purchase.forecast'].search([
            ('product_id', '=', self.product_id.id),
            ('company_id', '=', self.company_id.id),
        ]).unlink()
        self._do_refresh()
        return self._reload_form()

    def action_open_product(self):
        """Open the product form view."""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'product.product',
            'res_id': self.product_id.id,
            'view_mode': 'form',
            'target': 'current',
        }


    def action_export_xlsx(self):
        """Generate and download an Excel file with the current planning data."""
        self.ensure_one()
        try:
            import xlsxwriter
        except ImportError:
            raise models.UserError(_('xlsxwriter no está instalado en el servidor.'))

        output = io.BytesIO()
        wb = xlsxwriter.Workbook(output, {'in_memory': True})
        ws = wb.add_worksheet('Planeación')

        # Formats
        header_fmt = wb.add_format({
            'bold': True, 'bg_color': '#4472C4', 'font_color': '#FFFFFF',
            'border': 1, 'align': 'center',
        })
        label_fmt = wb.add_format({'bold': True, 'border': 1})
        cell_fmt = wb.add_format({'border': 1, 'align': 'center'})
        title_fmt = wb.add_format({'bold': True, 'font_size': 14})

        # Title
        product_name = self.product_display_name or self.product_id.display_name
        ws.write(0, 0, product_name, title_fmt)

        # Column headers (months)
        months = self._get_months_list()
        ws.write(2, 0, 'Concepto', header_fmt)
        for i, m in enumerate(months):
            ws.write(2, i + 1, self._format_month_label(m), header_fmt)

        # Data rows
        for line in self.line_ids.sorted('sequence'):
            row = line.sequence + 3
            ws.write(row, 0, line.row_label, label_fmt)
            for i in range(NUM_COLS):
                val = getattr(line, 'col_%d' % i) or ''
                ws.write(row, i + 1, val, cell_fmt)

        # Auto-fit column widths
        ws.set_column(0, 0, 22)
        ws.set_column(1, NUM_COLS, 14)

        wb.close()
        xlsx_data = base64.b64encode(output.getvalue())

        code = self.product_id.default_code or self.product_id.name
        att = self.env['ir.attachment'].create({
            'name': 'Planeacion_%s.xlsx' % code,
            'type': 'binary',
            'datas': xlsx_data,
            'mimetype': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        })
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/content/%d?download=true' % att.id,
            'target': 'new',
        }

    def _do_refresh(self):
        self.env['advanced.stock.reports.license'].check_license()
        for planning in self:
            planning._equalize_sales_forecast()
            planning._compute_planning_lines()

    def _equalize_sales_forecast(self):
        """Set sales forecast equal to real sales for all past months."""
        self.ensure_one()
        today = fields.Date.today()
        current_month_start = today.replace(day=1)
        months = self._get_months_list()

        allowed_company_ids = self.env.context.get(
            'allowed_company_ids', [self.env.company.id]
        )
        company_ids = tuple(allowed_company_ids)
        companies = self.env['res.company'].browse(allowed_company_ids)
        picking_type_ids = list(set(
            pt_id for c in companies
            for pt_id in c.ft_advstock_planning_picking_type_ids.ids
        ))

        past_months = [m for m in months if m < current_month_start]
        if not past_months:
            return

        sales_map = self._get_real_sales_map(
            self.product_id.id, company_ids, past_months, picking_type_ids
        )

        SalesForecast = self.env['ft.advstock.sales.forecast']
        for month in past_months:
            real_sales = sales_map.get(month, 0.0)
            existing = SalesForecast.search([
                ('product_id', '=', self.product_id.id),
                ('month_date', '=', month),
                ('company_id', '=', self.company_id.id),
            ], limit=1)
            if existing:
                existing.quantity = real_sales
            else:
                SalesForecast.create({
                    'product_id': self.product_id.id,
                    'month_date': month,
                    'quantity': real_sales,
                    'company_id': self.company_id.id,
                })

    # ------------------------------------------------------------------
    # Core computation
    # ------------------------------------------------------------------

    def _get_months_list(self):
        """Return list of 11 month-start dates centered on center_date."""
        center = self.center_date.replace(day=1)
        return [center + relativedelta(months=i) for i in range(-MONTHS_WINDOW, MONTHS_WINDOW + 1)]

    def _compute_planning_lines(self):
        """Compute 9 planning rows (metrics) with 11 month columns each."""
        self.ensure_one()
        company = self.company_id
        product = self.product_id
        today = fields.Date.today()
        current_month_start = today.replace(day=1)

        months = self._get_months_list()

        # Multicompany: aggregate across all selected companies
        allowed_company_ids = self.env.context.get('allowed_company_ids', [self.env.company.id])
        company_ids = tuple(allowed_company_ids)
        companies = self.env['res.company'].browse(allowed_company_ids)

        excluded_loc_ids = list(set(
            loc_id for c in companies for loc_id in c.ft_advstock_excluded_location_ids.ids
        ))
        picking_type_ids = list(set(
            pt_id for c in companies for pt_id in c.ft_advstock_planning_picking_type_ids.ids
        ))

        # Gather data in batch
        initial_inv_map = self._get_initial_inventory_map(product.id, company_ids, months, excluded_loc_ids)
        transit_map = self._get_transit_map(product.id, company_ids, months, current_month_start)
        sales_map = self._get_real_sales_map(product.id, company_ids, months, picking_type_ids)
        sales_forecast_map = self._get_sales_forecast_map(product.id, company_ids, months)
        purchase_forecast_map = self._get_purchase_forecast_map(product.id, company_ids, months)
        final_inv_map = self._get_final_inventory_map(product.id, company_ids, months, excluded_loc_ids, current_month_start)

        # Flag thresholds (per-product override or global from main company)
        flag_rec = self.env['ft.advstock.product.flag'].search([
            ('product_id', '=', product.id),
            ('company_id', '=', company.id),
        ], limit=1)
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

        # Build column data per metric row
        row_data = {rt: {} for rt, _ in ROW_TYPES}
        prev_final = None

        for i, month_start in enumerate(months):
            is_past = month_start < current_month_start
            is_future = month_start > current_month_start
            col = f'col_{i}'

            # Initial Inventory
            if is_future and prev_final is not None:
                initial_inv = prev_final
            else:
                initial_inv = initial_inv_map.get(month_start, 0.0)

            transit = transit_map.get(month_start, 0.0)
            purchase_forecast = purchase_forecast_map.get(month_start, 0.0)
            total_inv = initial_inv + transit + purchase_forecast
            sales_forecast = sales_forecast_map.get(month_start, 0.0)
            real_sales = sales_map.get(month_start, 0.0) if not is_future else 0.0

            if sales_forecast and real_sales:
                deviation = ((real_sales - sales_forecast) / sales_forecast) * 100
            else:
                deviation = None  # show as "-"

            if is_past:
                final_inv = final_inv_map.get(month_start, 0.0)
            else:
                final_inv = total_inv - sales_forecast

            prev_final = final_inv

            next_month = month_start + relativedelta(months=1)
            next_forecast = sales_forecast_map.get(next_month, 0.0)
            rotation = (final_inv / next_forecast) * 30 if next_forecast else INFINITY

            flag_val = _compute_flag(rotation, y_min, g_min, g_max, y_max)
            flag_symbol = FLAG_SYMBOLS.get(flag_val, '')

            # Format as Char for display
            row_data['initial_inventory'][col] = _fmt(initial_inv)
            row_data['transit'][col] = _fmt(transit)
            row_data['purchase_forecast'][col] = _fmt(purchase_forecast)
            row_data['total'][col] = _fmt(total_inv)
            row_data['sales_forecast'][col] = _fmt(sales_forecast)
            row_data['real_sales'][col] = _fmt(real_sales)
            row_data['final_inventory'][col] = _fmt(final_inv)

            if deviation is None:
                row_data['deviation'][col] = '-'
            else:
                row_data['deviation'][col] = f'{deviation:.1f}%'

            rotation_capped = min(rotation, INFINITY)
            row_data['rotation'][col] = f'{rotation_capped:.0f} {flag_symbol}'

        # Replace lines atomically
        self.line_ids.unlink()
        line_vals = []
        for seq, (row_type, row_label) in enumerate(ROW_TYPES):
            vals = {
                'planning_id': self.id,
                'sequence': seq,
                'row_type': row_type,
                'row_label': row_label,
            }
            vals.update(row_data[row_type])
            line_vals.append(vals)

        self.env['ft.advstock.planning.line'].create(line_vals)

    # ------------------------------------------------------------------
    # Data fetching helpers (SQL for performance)
    # ------------------------------------------------------------------

    def _get_initial_inventory_map(self, product_id, company_ids, months, excluded_loc_ids):
        """Net stock at the 1st day of each month (sum of done moves before that date)."""
        result = {}
        if not months:
            return result

        excluded_clause = ""
        excluded_params = []
        if excluded_loc_ids:
            excluded_clause = "AND sl.id NOT IN %s"
            excluded_params = [tuple(excluded_loc_ids)]

        for month_start in months:
            self.env.cr.execute("""
                SELECT COALESCE(SUM(
                    CASE
                        WHEN sm.location_dest_id = sl.id THEN sm.product_uom_qty
                        WHEN sm.location_id = sl.id THEN -sm.product_uom_qty
                        ELSE 0
                    END
                ), 0) AS net_qty
                FROM stock_move sm
                JOIN stock_location sl ON (
                    sl.id = sm.location_dest_id OR sl.id = sm.location_id
                )
                WHERE sm.product_id = %%s
                  AND sm.company_id IN %%s
                  AND sm.state = 'done'
                  AND sm.date < %%s
                  AND sl.usage = 'internal'
                  %s
            """ % excluded_clause, [product_id, company_ids, month_start] + excluded_params)
            row = self.env.cr.fetchone()
            result[month_start] = row[0] if row else 0.0

        return result

    def _get_final_inventory_map(self, product_id, company_ids, months, excluded_loc_ids, current_month_start):
        """Net stock at end of each past month."""
        result = {}
        past_months = [m for m in months if m < current_month_start]
        if not past_months:
            return result

        excluded_clause = ""
        excluded_params = []
        if excluded_loc_ids:
            excluded_clause = "AND sl.id NOT IN %s"
            excluded_params = [tuple(excluded_loc_ids)]

        for month_start in past_months:
            month_end = month_start + relativedelta(months=1)
            self.env.cr.execute("""
                SELECT COALESCE(SUM(
                    CASE
                        WHEN sm.location_dest_id = sl.id THEN sm.product_uom_qty
                        WHEN sm.location_id = sl.id THEN -sm.product_uom_qty
                        ELSE 0
                    END
                ), 0) AS net_qty
                FROM stock_move sm
                JOIN stock_location sl ON (
                    sl.id = sm.location_dest_id OR sl.id = sm.location_id
                )
                WHERE sm.product_id = %%s
                  AND sm.company_id IN %%s
                  AND sm.state = 'done'
                  AND sm.date < %%s
                  AND sl.usage = 'internal'
                  %s
            """ % excluded_clause, [product_id, company_ids, month_end] + excluded_params)
            row = self.env.cr.fetchone()
            result[month_start] = row[0] if row else 0.0

        return result

    def _get_transit_map(self, product_id, company_ids, months, current_month_start):
        """Receipts from confirmed POs per month via stock moves (pickings).

        Queries stock_move linked to purchase order lines to get the actual
        receipt date instead of the PO's date_planned.

        Current month: includes both done and pending moves (full picture).
        Other months: only pending moves (not yet received).
        Returns handle direction: incoming to internal = receipt (+),
        outgoing from internal = return (-).
        """
        result = {m: 0.0 for m in months}
        if not months:
            return result

        date_from = months[0]
        date_to = months[-1] + relativedelta(months=1)

        self.env.cr.execute("""
            SELECT DATE_TRUNC('month', sm.date)::date AS month_start,
                   COALESCE(SUM(
                       CASE
                           WHEN sl_src.usage != 'internal' AND sl_dest.usage = 'internal'
                               THEN sm.product_uom_qty
                           WHEN sl_src.usage = 'internal' AND sl_dest.usage != 'internal'
                               THEN -sm.product_uom_qty
                           ELSE 0
                       END
                   ), 0) AS qty
            FROM stock_move sm
            JOIN stock_location sl_src ON sl_src.id = sm.location_id
            JOIN stock_location sl_dest ON sl_dest.id = sm.location_dest_id
            WHERE sm.product_id = %s
              AND sm.company_id IN %s
              AND sm.purchase_line_id IS NOT NULL
              AND sm.date >= %s
              AND sm.date < %s
              AND (
                  (DATE_TRUNC('month', sm.date)::date = %s AND sm.state != 'cancel')
                  OR
                  (DATE_TRUNC('month', sm.date)::date != %s AND sm.state NOT IN ('done', 'cancel'))
              )
            GROUP BY DATE_TRUNC('month', sm.date)
        """, [product_id, company_ids, date_from, date_to,
              current_month_start, current_month_start])

        for row in self.env.cr.fetchall():
            month_key = row[0]
            if month_key in result:
                result[month_key] = row[1]

        return result

    def _get_real_sales_map(self, product_id, company_ids, months, picking_type_ids):
        """Done moves per month for configured picking types, respecting direction.

        Outgoing from internal locations are summed as sales.
        Incoming to internal locations (returns) are subtracted.
        """
        result = {m: 0.0 for m in months}
        if not months or not picking_type_ids:
            return result

        date_from = months[0]
        date_to = months[-1] + relativedelta(months=1)

        self.env.cr.execute("""
            SELECT DATE_TRUNC('month', sm.date)::date AS month_start,
                   COALESCE(SUM(
                       CASE
                           WHEN sl_src.usage = 'internal' THEN sm.product_uom_qty
                           WHEN sl_dest.usage = 'internal' THEN -sm.product_uom_qty
                           ELSE 0
                       END
                   ), 0) AS qty
            FROM stock_move sm
            JOIN stock_picking sp ON sp.id = sm.picking_id
            JOIN stock_location sl_src ON sl_src.id = sm.location_id
            JOIN stock_location sl_dest ON sl_dest.id = sm.location_dest_id
            WHERE sm.product_id = %s
              AND sm.company_id IN %s
              AND sm.state = 'done'
              AND sm.date >= %s
              AND sm.date < %s
              AND sp.picking_type_id IN %s
            GROUP BY DATE_TRUNC('month', sm.date)
        """, [product_id, company_ids, date_from, date_to, tuple(picking_type_ids)])

        for row in self.env.cr.fetchall():
            month_key = row[0]
            if month_key in result:
                result[month_key] = row[1]

        return result

    def _get_sales_forecast_map(self, product_id, company_ids, months):
        """Load sales forecast for the product across all relevant months."""
        result = {m: 0.0 for m in months}
        if not months:
            return result

        # Also fetch one extra month ahead for rotation calculation
        extended_end = months[-1] + relativedelta(months=1)
        result[extended_end] = 0.0

        forecasts = self.env['ft.advstock.sales.forecast'].search([
            ('product_id', '=', product_id),
            ('company_id', 'in', list(company_ids)),
            ('month_date', '>=', months[0]),
            ('month_date', '<=', extended_end),
        ])
        for f in forecasts:
            result[f.month_date] = result.get(f.month_date, 0.0) + f.quantity

        return result

    def _get_purchase_forecast_map(self, product_id, company_ids, months):
        """Load purchase forecast for the product across all relevant months."""
        result = {m: 0.0 for m in months}
        if not months:
            return result

        forecasts = self.env['ft.advstock.purchase.forecast'].search([
            ('product_id', '=', product_id),
            ('company_id', 'in', list(company_ids)),
            ('month_date', '>=', months[0]),
            ('month_date', '<=', months[-1]),
        ])
        for f in forecasts:
            result[f.month_date] = result.get(f.month_date, 0.0) + f.quantity

        return result

    @staticmethod
    def _format_month_label(date):
        """Format a date as 'MMM YYYY' in Spanish."""
        month_names = {
            1: 'ENE', 2: 'FEB', 3: 'MAR', 4: 'ABR',
            5: 'MAY', 6: 'JUN', 7: 'JUL', 8: 'AGO',
            9: 'SEP', 10: 'OCT', 11: 'NOV', 12: 'DIC',
        }
        return '%s %s' % (month_names[date.month], date.year)


class PurchasePlanningLine(models.TransientModel):
    _name = 'ft.advstock.planning.line'
    _description = 'Línea de Planeación de Compras'
    _order = 'planning_id, sequence'

    planning_id = fields.Many2one(
        'ft.advstock.purchase.planning', string='Planeación',
        required=True,
    )
    sequence = fields.Integer(default=0)
    row_type = fields.Selection(ROW_TYPES, string='Tipo de Fila')
    row_label = fields.Char(string='Concepto')

    col_0 = fields.Char(string='Mes -5')
    col_1 = fields.Char(string='Mes -4')
    col_2 = fields.Char(string='Mes -3')
    col_3 = fields.Char(string='Mes -2')
    col_4 = fields.Char(string='Mes -1')
    col_5 = fields.Char(string='Mes actual')
    col_6 = fields.Char(string='Mes +1')
    col_7 = fields.Char(string='Mes +2')
    col_8 = fields.Char(string='Mes +3')
    col_9 = fields.Char(string='Mes +4')
    col_10 = fields.Char(string='Mes +5')

    @api.model
    def fields_get(self, allfields=None, attributes=None):
        """Dynamically set column headers to month labels based on center_date."""
        res = super().fields_get(allfields, attributes)
        center_str = self.env.context.get('planning_center_date')
        if center_str:
            try:
                center = fields.Date.from_string(center_str).replace(day=1)
            except (ValueError, AttributeError):
                center = fields.Date.today().replace(day=1)
        else:
            center = fields.Date.today().replace(day=1)

        current_month = fields.Date.today().replace(day=1)

        for i in range(NUM_COLS):
            field_name = f'col_{i}'
            if field_name in res:
                month = center + relativedelta(months=i - MONTHS_WINDOW)
                label = PurchasePlanning._format_month_label(month)
                if month == current_month:
                    label = f'► {label} ◄'
                res[field_name]['string'] = label
                res[field_name]['sortable'] = False
        return res

    def write(self, vals):
        """Sync forecast/purchase forecast row edits back to persistent models."""
        res = super().write(vals)
        col_set = {f'col_{i}' for i in range(NUM_COLS)}
        changed_cols = col_set & set(vals)
        if changed_cols:
            SalesForecast = self.env['ft.advstock.sales.forecast']
            PurchaseForecast = self.env['ft.advstock.purchase.forecast']
            for line in self:
                if line.row_type not in EDITABLE_ROWS:
                    continue
                planning = line.planning_id
                center = planning.center_date.replace(day=1)
                for i in range(NUM_COLS):
                    col_name = f'col_{i}'
                    if col_name not in vals:
                        continue
                    month = center + relativedelta(months=i - MONTHS_WINDOW)
                    qty = _parse_float(vals[col_name])

                    if line.row_type == 'sales_forecast':
                        existing = SalesForecast.search([
                            ('product_id', '=', planning.product_id.id),
                            ('month_date', '=', month),
                            ('company_id', '=', planning.company_id.id),
                        ], limit=1)
                        if existing:
                            existing.quantity = qty
                        else:
                            SalesForecast.create({
                                'product_id': planning.product_id.id,
                                'month_date': month,
                                'quantity': qty,
                                'company_id': planning.company_id.id,
                            })
                    elif line.row_type == 'purchase_forecast':
                        existing = PurchaseForecast.search([
                            ('product_id', '=', planning.product_id.id),
                            ('month_date', '=', month),
                            ('company_id', '=', planning.company_id.id),
                        ], limit=1)
                        if existing:
                            existing.quantity = qty
                        else:
                            PurchaseForecast.create({
                                'product_id': planning.product_id.id,
                                'month_date': month,
                                'quantity': qty,
                                'company_id': planning.company_id.id,
                            })
        return res
