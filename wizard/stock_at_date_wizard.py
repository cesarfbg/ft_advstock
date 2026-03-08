from collections import defaultdict

from odoo import _, api, fields, models


class StockAtDateWizard(models.TransientModel):
    _name = 'ft.advstock.stock.at.date.wizard'
    _description = 'Inventario a la Fecha'

    date = fields.Datetime(
        string='Fecha de Corte', required=True,
        default=lambda self: fields.Datetime.now(),
    )
    company_id = fields.Many2one(
        'res.company', string='Compañía',
        required=True, default=lambda self: self.env.company,
    )
    line_ids = fields.One2many(
        'ft.advstock.stock.at.date.line', 'wizard_id',
        string='Líneas de Inventario',
    )

    def action_compute(self):
        """Compute stock at the selected date and display results."""
        self.ensure_one()
        self.env['advanced.stock.reports.license'].check_license()

        company_ids = tuple(
            self.env.context.get('allowed_company_ids', [self.env.company.id])
        )

        # All internal locations (no exclusions for this report)
        all_internal = self.env['stock.location'].search([
            ('usage', '=', 'internal'),
        ])
        location_ids = tuple(all_internal.ids) or (0,)

        stock_data = self._reconstruct_stock_at_date(
            date=self.date,
            product_ids=None,
            company_ids=company_ids,
            location_ids=location_ids,
            group_by_lot=True,
        )

        # Build warehouse name cache
        wh_by_loc = {}
        warehouses = self.env['stock.warehouse'].search([
            ('company_id', 'in', list(company_ids)),
        ])
        for wh in warehouses:
            for loc in self.env['stock.location'].search([
                ('id', 'child_of', wh.lot_stock_id.id),
            ]):
                wh_by_loc[loc.id] = wh.name

        # Build result lines
        self.line_ids.unlink()
        line_vals = []

        # Pre-fetch related records for performance
        product_ids = list(set(k[0] for k in stock_data))
        location_ids_used = list(set(k[1] for k in stock_data))
        lot_ids = list(set(k[2] for k in stock_data if k[2]))

        products = {p.id: p for p in self.env['product.product'].browse(product_ids)}
        locations = {l.id: l for l in self.env['stock.location'].browse(location_ids_used)}
        lots = {l.id: l for l in self.env['stock.lot'].browse(lot_ids)} if lot_ids else {}

        for (product_id, location_id, lot_id), qty in stock_data.items():
            if not qty:
                continue
            product = products.get(product_id)
            location = locations.get(location_id)
            lot = lots.get(lot_id) if lot_id else None
            if not product or not location:
                continue

            line_vals.append({
                'wizard_id': self.id,
                'warehouse_name': wh_by_loc.get(location_id, ''),
                'location_id': location_id,
                'location_name': location.complete_name,
                'product_id': product_id,
                'product_name': product.display_name,
                'product_categ_id': product.categ_id.id,
                'lot_id': lot_id or False,
                'lot_name': lot.name if lot else '',
                'quantity': qty,
                'uom_id': product.uom_id.id,
            })

        if line_vals:
            self.env['ft.advstock.stock.at.date.line'].create(line_vals)

        return {
            'type': 'ir.actions.act_window',
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
            'context': {**self.env.context, 'stock_at_date_computed': True},
        }

    # ------------------------------------------------------------------
    # Centralized stock reconstruction method
    # ------------------------------------------------------------------

    @api.model
    def _reconstruct_stock_at_date(self, date, product_ids, company_ids,
                                   location_ids=None, group_by_lot=True):
        """Reconstruct stock at a given date by starting from current quants
        and undoing moves that happened after the cutoff date.

        Args:
            date: datetime cutoff (stock as of this moment)
            product_ids: list of product IDs to filter (None = all products)
            company_ids: tuple of company IDs
            location_ids: tuple of internal location IDs to consider
                          (None = all internal locations)
            group_by_lot: if True, returns per-lot detail using stock_move_line;
                          if False, aggregates without lot using stock_move
                          (better performance for planning)

        Returns:
            If group_by_lot=True:
                dict {(product_id, location_id, lot_id): qty}
            If group_by_lot=False:
                dict {(product_id, location_id): qty}
        """
        if not company_ids:
            return {}

        # Step 1: Determine target locations
        if location_ids is None:
            all_internal = self.env['stock.location'].search([
                ('usage', '=', 'internal'),
            ])
            location_ids = tuple(all_internal.ids) or (0,)

        loc_set = set(location_ids)

        # Step 2: Read current stock.quant
        product_filter = ""
        params_quant = [company_ids, location_ids]
        if product_ids:
            product_filter = "AND sq.product_id IN %s"
            params_quant.append(tuple(product_ids))

        if group_by_lot:
            self.env.cr.execute("""
                SELECT sq.product_id, sq.location_id,
                       COALESCE(sq.lot_id, 0), SUM(sq.quantity)
                FROM stock_quant sq
                WHERE sq.company_id IN %%s
                  AND sq.location_id IN %%s
                  %s
                GROUP BY sq.product_id, sq.location_id, sq.lot_id
            """ % product_filter, params_quant)
        else:
            self.env.cr.execute("""
                SELECT sq.product_id, sq.location_id, SUM(sq.quantity)
                FROM stock_quant sq
                WHERE sq.company_id IN %%s
                  AND sq.location_id IN %%s
                  %s
                GROUP BY sq.product_id, sq.location_id
            """ % product_filter, params_quant)

        stock = defaultdict(float)
        for row in self.env.cr.fetchall():
            if group_by_lot:
                key = (row[0], row[1], row[2] or False)
                stock[key] = row[3]
            else:
                key = (row[0], row[1])
                stock[key] = row[2]

        # Step 3: Get done moves AFTER the cutoff date and undo them
        product_filter_move = ""
        params_move = [date, company_ids, location_ids, location_ids]
        if product_ids:
            product_filter_move = "AND sm.product_id IN %s"
            params_move.append(tuple(product_ids))

        if group_by_lot:
            self.env.cr.execute("""
                SELECT sml.product_id, sm.location_id, sm.location_dest_id,
                       COALESCE(sml.lot_id, 0), SUM(sml.qty_done)
                FROM stock_move_line sml
                JOIN stock_move sm ON sm.id = sml.move_id
                WHERE sm.state = 'done'
                  AND sml.date > %%s
                  AND sm.company_id IN %%s
                  AND (sm.location_id IN %%s OR sm.location_dest_id IN %%s)
                  %s
                GROUP BY sml.product_id, sm.location_id,
                         sm.location_dest_id, sml.lot_id
            """ % product_filter_move, params_move)

            for row in self.env.cr.fetchall():
                pid, loc_src, loc_dest, lot_id, qty = row
                lot_id = lot_id or False
                # Undo: reverse destination entry
                if loc_dest in loc_set:
                    stock[(pid, loc_dest, lot_id)] -= qty
                # Undo: reverse source exit
                if loc_src in loc_set:
                    stock[(pid, loc_src, lot_id)] += qty
        else:
            self.env.cr.execute("""
                SELECT sm.product_id, sm.location_id, sm.location_dest_id,
                       SUM(sm.product_uom_qty)
                FROM stock_move sm
                WHERE sm.state = 'done'
                  AND sm.date > %%s
                  AND sm.company_id IN %%s
                  AND (sm.location_id IN %%s OR sm.location_dest_id IN %%s)
                  %s
                GROUP BY sm.product_id, sm.location_id, sm.location_dest_id
            """ % product_filter_move, params_move)

            for row in self.env.cr.fetchall():
                pid, loc_src, loc_dest, qty = row
                if loc_dest in loc_set:
                    stock[(pid, loc_dest)] -= qty
                if loc_src in loc_set:
                    stock[(pid, loc_src)] += qty

        # Step 4: Filter out zero/negative entries
        return {k: v for k, v in stock.items() if round(v, 4) > 0}


class StockAtDateLine(models.TransientModel):
    _name = 'ft.advstock.stock.at.date.line'
    _description = 'Línea de Inventario a la Fecha'
    _order = 'warehouse_name, location_name, product_name'

    wizard_id = fields.Many2one(
        'ft.advstock.stock.at.date.wizard', string='Wizard',
        required=True, ondelete='cascade',
    )
    warehouse_name = fields.Char(string='Almacén')
    location_id = fields.Many2one('stock.location', string='Ubicación')
    location_name = fields.Char(string='Ubicación (Nombre)')
    product_id = fields.Many2one('product.product', string='Producto')
    product_name = fields.Char(string='Producto (Nombre)')
    product_categ_id = fields.Many2one('product.category', string='Categoría')
    lot_id = fields.Many2one('stock.lot', string='Lote/Serie')
    lot_name = fields.Char(string='Lote (Nombre)')
    quantity = fields.Float(string='Cantidad', digits='Product Unit of Measure')
    uom_id = fields.Many2one('uom.uom', string='UdM')
