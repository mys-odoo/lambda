# -*- coding: utf-8 -*-
from odoo import api, fields, models, _, tools
from odoo.osv import expression
from odoo.exceptions import UserError, ValidationError

class ProductAttributeValueInherit(models.Model):
    _inherit = "product.attribute.value"

    django_component_id = fields.Char(string='Django Id')

class ProductTemplate(models.Model):
    _inherit = "product.template"

    django_id = fields.Char(string='Django Id')
    django_serial_number = fields.Char(string='Django Serial Number')