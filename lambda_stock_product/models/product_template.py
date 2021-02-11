# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    product_template_value_ids = fields.One2many("product.template.attribute.value", "product_tmpl_id", string="Product Variant Values")

    def write(self, vals):
        if self.is_product_variant == False and self.product_variant_count > 1:
            if 'weight' not in vals:
                vals['weight'] = self.weight
            if 'volume' not in vals:
                vals['volume'] = self.volume
            for variant in self.product_variant_ids:
                variant.write({
                    "weight": vals['weight'],
                    "volume": vals['volume']
                })
        return super(ProductTemplate, self.sudo()).write(vals)

class ProductTemplateAttributeValue(models.Model):
    _name = 'product.template.attribute.value'
    _inherit = ['product.template.attribute.value', 'mail.thread']

    price = fields.Float(related="product_id.lst_price", string="Original Price")
    product_id = fields.Many2one("product.product", string="Variant Product")
    is_price_linked = fields.Boolean(default=False, string="Is Base Product Price linked?")
    price_extra = fields.Float(
        store=True,
        string="Value Price Extra",
        default=0.0,
        digits='Product Price',
        compute="_compute_price_extra",
        inverse="_set_price_extra",
        help="Extra price for the variant with this attribute value on sale price. eg. 200 price extra, 1000 + 200 = 1200.")

    @api.depends('product_id', 'price')
    def _compute_price_extra(self):
        for attr_val in self:
            if attr_val.is_price_linked:
                attr_val.price_extra = attr_val.price

    def _set_price_extra(self):
        for attribute_value in self:
            attribute_value.price_extra = attribute_value.price_extra

    def write(self, vals):
        if self.read():
            initial_rec = self.read()[0]
            rslt = super(ProductTemplateAttributeValue, self.sudo()).write(vals)
            final_rec = self.read()[0]
            body = "{} Updated the following fields:<br/>".format(final_rec['write_date'].strftime("%d/%m/%y %H:%M"))
            for key in initial_rec:
                if initial_rec[key] != final_rec[key] and key in ['price_extra']:
                    body += "{} changed from {} to {}<br/>".format(self._fields[key].string, initial_rec[key], final_rec[key])
                    self.message_post(body=body, author_id=self.env.user.partner_id.id)
            return rslt
        else:
            return super(ProductTemplateAttributeValue, self.sudo()).write(vals)