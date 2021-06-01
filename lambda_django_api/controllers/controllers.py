# -*- coding: utf-8 -*-
from odoo import http, fields
from odoo.http import request
import json
import base64
import requests
from ast import literal_eval
from datetime import datetime, timedelta
from werkzeug.urls import url_encode
from odoo.tools import html2plaintext
import pytz
import os
from odoo.modules.module import get_module_resource


class LambdaApi(http.Controller):

    def _ids2str(self, ids):
        return ','.join([str(i) for i in sorted(ids)])

    def create_new_product_with_initial_variants(self, bom):
        product_tmpl_obj = request.env['product.template'].sudo().create({
                    'name': bom.get('product'),
                    'type': 'product',
                    'django_id': bom.get('id'),
                    'django_serial_number': bom.get('serial_number'),
                    'sale_ok': True,
                    'purchase_ok': False,
                    'route_ids': [[6, False, [5,1]]]
                })
        attribute_ids = [0]
        # Prepare Attributes and Values
        attributes = request.env['product.attribute'].sudo().search([('display_type', '=', 'select'),
                                                                    ('create_variant', '=', 'dynamic')])
        #Add to Product
        for attribute in attributes:
            line = request.env['product.template.attribute.line'].sudo().search([
                ('attribute_id', '=', attribute.id),
                ('product_tmpl_id', '=', product_tmpl_obj.id),
            ])
            if not line:
                line = request.env['product.template.attribute.line'].sudo().create({
                    'attribute_id': attribute.id,
                    'product_tmpl_id': product_tmpl_obj.id,
                    'value_ids': [(6, 0, attribute.value_ids.ids)],
                })
        product_template_attribute_value = request.env['product.template.attribute.value'].sudo().search([('product_tmpl_id', '=', product_tmpl_obj.id)])
        for i in product_template_attribute_value:
            product = request.env['product.product'].sudo().search([('name', '=', i.product_attribute_value_id.name)])
            i.write({
                        'is_price_linked': True,
                        'product_id': product.id,
                    })
        return product_tmpl_obj

    def create_attribute_value(self, product_tmpl_obj, sku):
        #Search/Create attriubte
        attribute = request.env['product.attribute'].sudo().search([('name', '=', sku.get('category')),
                                                                        ('display_type', '=', 'select'),
                                                                        ('create_variant', '=', 'dynamic')])
        #Search/Create attribute_value
        if len(attribute) == 0:
                attribute = request.env['product.attribute'].sudo().create({
                    'name': sku.get('category'),
                    'display_type': 'select',
                    'create_variant': 'dynamic',
                })
        attribute_value = request.env['product.attribute.value'].sudo().create({
            'name': sku.get('name'),
            'attribute_id': attribute.id,
            'django_component_id': sku.get('id'),
        })
        product_product = request.env['product.product'].sudo().create({
            'name': sku.get('name'),
            'type': 'product',
            'lst_price': sku.get('cost'),
            'sale_ok': True,
            'purchase_ok': True,
        })
        #Add to Product / Price
        line = request.env['product.template.attribute.line'].sudo().search([
            ('attribute_id', '=', attribute.id),
            ('product_tmpl_id', '=', product_tmpl_obj.id),
        ])
        if len(line) == 0:
            line = request.env['product.template.attribute.line'].sudo().create({
                'attribute_id': attribute.id,
                'product_tmpl_id': product_tmpl_obj.id,
                'value_ids': [(6, 0, attribute.value_ids.ids)],
            })
        else: 
            line.write({'value_ids': attribute.value_ids.ids})

        product_template_attribute_value = request.env['product.template.attribute.value'].sudo().search([('product_tmpl_id', '=', product_tmpl_obj.id),
                                                                                                        ('product_attribute_value_id', '=', attribute_value.id),
                                                                                                        ('attribute_id', '=', attribute.id)])
        product_template_attribute_value.write({
                    'is_price_linked': True,
                    'product_id': product_product.id,
                })

    #Initial Variant
    @http.route('/api/UpdateVariant/<string:product_name>', type='http', auth="public", methods=['GET'], website=True)
    def update_variant(self, product_name, **get):
        path = get_module_resource('lambda_django_api', 'static/src/', 'components.json')
        componentFile = open(path, 'r')
        product_tmpl_obj = request.env['product.template'].sudo().search([('name', '=', product_name)])
        file_tmp = json.loads(componentFile.read())
        attribute_ids = [0]
        # Prepare Attributes and Values
        for item in file_tmp:
            attribute = request.env['product.attribute'].sudo().search([('name', '=', item.get('category')),
                                                                        ('display_type', '=', 'select'),
                                                                        ('create_variant', '=', 'dynamic')
                                                                    ])
            if len(attribute) == 0:
                attribute = request.env['product.attribute'].sudo().create({
                    'name': item.get('category'),
                    'display_type': 'select',
                    'create_variant': 'dynamic',
                })
            attribute_value = request.env['product.attribute.value'].sudo().search([('name', '=', item.get('name')),('attribute_id', '=', attribute.id)])
            if len(attribute_value) == 0:
                attribute_value = request.env['product.attribute.value'].sudo().create({
                    'name': item.get('name'),
                    'attribute_id': attribute.id,
                    'django_component_id': item.get('id'),
                })
                product_product = request.env['product.product'].sudo().create({
                    'name': item.get('name'),
                    'type': 'product',
                    'lst_price': item.get('cost'),
                    'sale_ok': True,
                    'purchase_ok': True,
                })
            if attribute.id not in attribute_ids:
                attribute_ids.append(attribute.id)
        #Add to Product
        for attribute_id in attribute_ids[1:len(attribute_ids)]:
            attribute = request.env['product.attribute'].sudo().search([('id', '=', attribute_id)])
            line = request.env['product.template.attribute.line'].sudo().search([
                ('attribute_id', '=', attribute.id),
                ('product_tmpl_id', '=', product_tmpl_obj.id),
            ])
            if not line:
                line = request.env['product.template.attribute.line'].sudo().create({
                    'attribute_id': attribute.id,
                    'product_tmpl_id': product_tmpl_obj.id,
                    'value_ids': [(6, 0, attribute.value_ids.ids)],
                })
        product_template_attribute_value = request.env['product.template.attribute.value'].sudo().search([('product_tmpl_id', '=', product_tmpl_obj.id)])
        for i in product_template_attribute_value:
            product = request.env['product.product'].sudo().search([('name', '=', i.product_attribute_value_id.name)])
            i.write({
                        'is_price_linked': True,
                        'product_id': product.id,
                    })

    @http.route('/api/CreateOrder', type='json', auth="public", website=True)
    def create_order(self, **post):
        post_data = json.loads(request.httprequest.data)
        result = {}
        #Bill to
        bill_to_organization = post_data.get('bill_to_organization')
        bill_to_email = post_data.get('bill_to_email')
        bill_to_phone = post_data.get('bill_to_phone')
        bill_to_address = post_data.get('bill_to_address')
        #Ship to
        ship_to_organization = post_data.get('ship_to_organization')
        ship_to_email = post_data.get('ship_to_email')
        ship_to_phone = post_data.get('ship_to_phone')
        ship_to_address = post_data.get('ship_to_address')
        res_partner_id = None
        if bill_to_organization == ship_to_organization:
            res_partner_id = request.env['res.partner'].sudo().search([('email', '=', ship_to_email), ('phone', '=', ship_to_phone)])
            if len(res_partner_id) == 0:
                res_partner_id = request.env['res.partner'].api_create(ship_to_address, ship_to_email, ship_to_phone)
        #SALE ORDER Datas
        if res_partner_id:
            sale_person = post_data.get('owner')
            sale_person_obj = request.env['res.users'].sudo().search([('name', '=', sale_person)])
            if not sale_person_obj:
                http.request.env['res.users'].sudo().create({'name': sale_person,
                                                        'login': sale_person+'@lambda.com' })
            new_sale_order = request.env['sale.order'].sudo().create({
                                        'user_id': request.env['res.users'].sudo().search([('name', '=', post_data.get('owner'))]).id or None,
                                        'partner_id': res_partner_id.id,
                                        'date_order': datetime.utcfromtimestamp(post_data.get('date')).strftime('%Y-%m-%d %H:%M:%S'),
                                        'pdf_url': post_data.get('pdf_url'),
                                        'build_sheet_url': post_data.get('build_sheet_url'),
                                        'django_so_id': post_data.get('id'),
                                        'django_purchase_order_id': post_data.get('purchase_order_id'),
                                        'django_purchase_order_terms': post_data.get('purchase_order_terms'),
                                        })

            #Note
            notes = post_data.get('notes')
            if (len(notes) > 0):
                for note in notes:
                    new_sale_order.message_post(body=note.get('body'))
            #Attachment
            attachments = post_data.get('files')
            if (len(attachments) > 0):
                for attachment in attachments:
                    ir_attachment = request.env['ir.attachment'].sudo().create({
                        'name': attachment.get('name'),
                        'res_model': 'sale.order',
                        'res_id': new_sale_order.id,
                        'type': 'url',
                        'url': attachment.get('url'),
                     })

            #Product
            #Discount
            dicsount_product = request.env['product.product'].sudo().search([('name', '=', 'Discount')])
            if len(dicsount_product) > 0:
                request.env['sale.order.line'].sudo().create({
                    'order_id': new_sale_order.id,
                    'product_id': dicsount_product.id,
                    'name': 'Discount',
                    'price_unit': post_data.get('discount')*-1
                })
            #is_configurable_product
            # 0. Prepare sku_list: 
            boms = post_data.get('boms')
            for bom in boms:
                product_tmpl_obj = request.env['product.template'].sudo().search([('name', '=', bom.get('product'))])
                if len(product_tmpl_obj) == 0:
                    product_tmpl_obj = self.create_new_product_with_initial_variants(bom)
                
                sku_list = [0]
                for component in bom.get('components'):
                    attribute_value = request.env['product.attribute.value'].sudo().search([('django_component_id', '=', component.get('sku').get('id'))])
                    if len(attribute_value) == 0:
                        self.create_attribute_value(product_tmpl_obj, component.get('sku'))

                    attribute_value = request.env['product.attribute.value'].sudo().search([('django_component_id', '=', component.get('sku').get('id'))])
                    product_template_attribute_value = request.env['product.template.attribute.value'].sudo().search([('product_tmpl_id', '=', product_tmpl_obj.id)])
                    for value in product_template_attribute_value:
                        if value.attribute_id.id == attribute_value.attribute_id.id and value.product_attribute_value_id.id == attribute_value.id:
                            sku_list.append(value.id)
                sku_list = sku_list[1:len(sku_list)]
            # 1. Create product with combination_indices
            #TODO: If not => Create, exist, use again
                product = request.env['product.product'].sudo().search([
                                ('combination_indices', '=', self._ids2str(sku_list)),
                                ('product_tmpl_id', '=', product_tmpl_obj.id)
                            ])
                if len(product) == 0:
                    print("create product with new variants")
                    product = request.env['product.product'].sudo().create({
                                    'product_template_attribute_value_ids': sku_list,
                                    'type': 'product',
                                    'active': 1,
                                    'product_tmpl_id': product_tmpl_obj.id,
                                })
            # 2. add this product to line 
                product_name = product.name
                if len (product.name_get())>0:
                    product_name = product.name_get()[0][1]
                request.env['sale.order.line'].sudo().create({
                    'order_id': new_sale_order.id,
                    'name': product_name,
                    'product_id': product.id,
                })

            #Shipment
            shipments = post_data.get('shipments')
            if len(shipments) > 0:
                # for shipment in shipments:
                new_sale_order.commitment_date = datetime.utcfromtimestamp(shipments[0].get('date_unix_time')).strftime('%Y-%m-%d %H:%M:%S')
                new_sale_order.action_confirm()
                for picking in new_sale_order.picking_ids:
                    picking.carrier_tracking_ref = shipments[0].get('tracking_number')

        return new_sale_order