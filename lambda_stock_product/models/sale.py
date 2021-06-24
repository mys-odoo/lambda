# -*- coding: utf-8 -*-

from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    message = fields.Text(string="The following product(s) had their prices changed. Please check off the product(s) that should conform to their price change. Those that remained unchecked will keep their unit price.", readonly=True, store=True)

    def action_confirm(self):
        # popup = self.check_products(True)
        # if popup:
        #     return popup
        return super(SaleOrder, self).action_confirm()

    def action_quotation_send(self):
        # popup = self.check_products(False)
        # if popup:
        #     return popup
        return super(SaleOrder, self).action_quotation_send()

    def action_save_then_confirm(self):
        self.change_product_price()
        return super(SaleOrder, self).action_confirm()

    def action_save_then_email(self):
        self.change_product_price()
        return super(SaleOrder, self).action_quotation_send()

    def change_product_price(self):
        for so in self:
            for sol in so.order_line:
                if sol.change_price:
                    sol.write({
                        'price_unit': sol.alt_price,
                        'change_price': False
                    })

    def check_products(self, confirm):
        for so in self:
            order_line = []
            for sol in so.order_line:
                if sol.product_id.lst_price != sol.price_unit:
                    order_line.append(sol.id)
            if order_line:
                return {
                    'name': 'Sale Warning Wizard',
                    'type': 'ir.actions.act_window',
                    'res_model': 'sale.order',
                    'res_id': so.id,
                    'views': [[self.env.ref('lambda_stock_product.view_sale_price_wizard_lambda').id, 'form']],
                    'target': 'new',
                    'context': {"confirm1": confirm,
                                "confirm2": not confirm
                    }
                }
        return {}

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    change_price = fields.Boolean(string='Change Price?')
    alt_price = fields.Float(string='Alternate Price', related='product_id.lst_price',digits='Product Price', default=0.0)