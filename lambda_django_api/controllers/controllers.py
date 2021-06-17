# -*- coding: utf-8 -*-
from odoo import http, fields, _
from odoo.http import request, Response
from odoo.service import wsgi_server
from odoo.exceptions import UserError
import logging
import json
import traceback
import base64
import requests
from ast import literal_eval
from datetime import datetime, timedelta
from werkzeug.urls import url_encode
from odoo.tools import html2plaintext
import pytz
import os
from odoo.modules.module import get_module_resource
_logger = logging.getLogger(__name__)
BASE_URL = "https://lambdalabs.com/"

class LambdaApi(http.Controller):
    
    ##Initial Variant
    @http.route('/api/UpdateVariant/<string:product_name>', type='http', auth="public", methods=['GET'], website=True)
    def update_variant(self, product_name, **get):
        print("update_variant")
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
            if len(product) >1:
                i.write({
                            'is_price_linked': True,
                            'product_id': product[1].id,
                        })
            else: 
                i.write({
                            'is_price_linked': True,
                            'product_id': product.id,
                        })

    @http.route('/api/order/create', type='json', auth="public", website=True)
    def create_order(self, **post):
        res = {
            'meta': {
                'status': False,
                'message': None
            },
            'data': {
            }
        }
        error =''
        #Check TOKEN
        token = request.httprequest.environ.get('HTTP_TOKEN', False)
        user = request.env['res.users'].check_token(token)
        if not user or not token:
            res['meta'].update({
                "status_code": 403,
                'message': 'Something wrong with your token, please contact Admin.',
            })
            return res
        #End check TOKEN
        try:
            post_data = json.loads(request.httprequest.data)
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
                    print("len === 0")
                    res_partner_id = request.env['res.partner'].api_create(ship_to_organization, ship_to_email, ship_to_phone, bill_to_address, ship_to_address)
                else:
                    request.env['res.partner'].check_bill_or_ship_to_adddress(res_partner_id, bill_to_address, is_bill=True)
                    request.env['res.partner'].check_bill_or_ship_to_adddress(res_partner_id, ship_to_address, is_bill=False)
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
                                            # 'pdf_url': BASE_URL + post_data.get('pdf_url'),
                                            # 'build_sheet_url': BASE_URL + post_data.get('build_sheet_url'),
                                            'django_so_id': post_data.get('id'),
                                            'django_purchase_order_id': post_data.get('purchase_order_id'),
                                            'django_purchase_order_terms': post_data.get('purchase_order_terms'),
                                            })
                res['meta'].update({
                        "status": True,
                        'message': 'Create order successfull.',
                    })
                res['data'].update({"sale_order_id": new_sale_order.id,
                                    "odoo_customer_id": res_partner_id.id
                                    })
                #Note
                notes = post_data.get('notes')
                if (len(notes) > 0):
                    for note in notes:
                        new_sale_order.message_post(body=note.get('body'))
                #Attachment
                pdf_url_attachment = request.env['ir.attachment'].sudo().create({
                            'name': "PDF Invoice",
                            'res_model': 'sale.order',
                            'res_id': new_sale_order.id,
                            'type': 'url',
                            'url': BASE_URL + post_data.get('pdf_url'),
                        })
                build_sheet_url_attachment = request.env['ir.attachment'].sudo().create({
                            'name': "Build Sheets",
                            'res_model': 'sale.order',
                            'res_id': new_sale_order.id,
                            'type': 'url',
                            'url': BASE_URL + post_data.get('build_sheet_url'),
                        })
                attachments = post_data.get('files')
                if (len(attachments) > 0):
                    for attachment in attachments:
                        ir_attachment = request.env['ir.attachment'].sudo().create({
                            'name': attachment.get('name'),
                            'res_model': 'sale.order',
                            'res_id': new_sale_order.id,
                            'type': 'url',
                            'url': BASE_URL + attachment.get('url'),
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
                boms = post_data.get('boms')
                for bom in boms:
                    #I. PROCESS PRODUCT
                    product_tmpl_obj = request.env['product.template'].sudo().search([('name', '=ilike', bom.get('product'))])
                    if len(product_tmpl_obj) == 0:
                        product_tmpl_obj = self.create_new_product_with_initial_variants(bom)
                        # self.defind_bom_for_new_product(product_tmpl_obj, bom)
                    #II. PROCESS LIST COMPONENTS
                    sku_list = [0]
                        #BOM
                    bom_obj = request.env['mrp.bom'].sudo().search([('product_tmpl_id', '=', product_tmpl_obj.id), ('type', '=', 'normal')])
                    if len(bom_obj) == 0:
                        bom_obj = request.env['mrp.bom'].sudo().create({
                            'product_tmpl_id': product_tmpl_obj.id,
                            'type': 'normal',
                            'product_qty': 1,
                        })
                        #Prepard sku_list and BOM's compoments
                    for component in bom.get('components'):
                        django_component_id = component.get('sku').get('id')
                        if component.get('qty') > 1:
                            django_component_id = self._redefind_sku_id(component.get('sku').get('id'), component.get('qty'))
                        print(django_component_id)
                        attribute_value = request.env['product.attribute.value'].sudo().search([('django_component_id', '=', django_component_id)])
                        print(attribute_value)
                        if len(attribute_value) == 0:
                            attribute_value = self.create_attribute_value(product_tmpl_obj, component.get('sku'), component.get('qty'))

                        
                        product_template_attribute_value = request.env['product.template.attribute.value'].sudo().search([('product_tmpl_id', '=', product_tmpl_obj.id),
                                                                                                            ('product_attribute_value_id', '=', attribute_value.id),
                                                                                                            ('attribute_id', '=', attribute_value.attribute_id.id)])
                        if len(product_template_attribute_value) > 0:
                            #Append SKU
                            sku_list.append(product_template_attribute_value.id)
                            #Master BOM process
                            self.process_master_bom(bom_obj, product_template_attribute_value, component.get('qty'))
                            
                        
                    sku_list = sku_list[1:len(sku_list)]
                    ##III. PROCESS PRODUCT WITH SALE ORDER LINES
                    # 1. Create product with combination_indices
                    #TODO: If not => Create, exist => use again
                    product = request.env['product.product'].sudo().search([
                                    ('combination_indices', '=', self._ids2str(sku_list)),
                                    ('product_tmpl_id', '=', product_tmpl_obj.id)
                                ])
                    if len(product) == 0:
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
                        'serial_number': bom.get('serial_number')
                    })

                #Shipment
                shipments = post_data.get('shipments')
                if len(shipments) > 0:
                    # for shipment in shipments:
                    new_sale_order.commitment_date = datetime.utcfromtimestamp(shipments[0].get('date_unix_time')).strftime('%Y-%m-%d %H:%M:%S')
                    new_sale_order.action_confirm()
                    for picking in new_sale_order.picking_ids:
                        picking.carrier_tracking_ref = shipments[0].get('tracking_number')
        except Exception as e:
            error = 'Please check data request again.'
            _logger.info("\n%s", traceback.format_exc())
            pass
        if error:
            res['meta'].update({
                'message': error,
            })
        return res

    #UpdateCustomer
    @http.route('/api/order/update_customer', type='json', auth="public", website=True)
    def update_customer(self, **post):
        res = {
            'meta': {
                'status': False,
                'message': None
            },
            'data': {
            }
        }
        error =''
        #Check TOKEN
        token = request.httprequest.environ.get('HTTP_TOKEN', False)
        user = request.env['res.users'].check_token(token)
        if not user or not token:
            res['meta'].update({
                "status_code": 403,
                'message': 'Something wrong with your token, please contact Admin.',
            })
            return res
        #End check TOKEN
        try:
            post_data = json.loads(request.httprequest.data)
            result = {}
            customer_id = post_data.get('odoo_customer_id')
            bill_to_address = post_data.get('bill_to_address')
            ship_to_address = post_data.get('ship_to_address')

            request.env['res.partner'].api_update(customer_id, post_data.get('ship_to_organization'), post_data.get('ship_to_email'), post_data.get('ship_to_phone'), bill_to_address, ship_to_address)
            res['meta'].update({
                        "status": True,
                        'message': 'Update customer successfull.',
                    })
            res['data'].update({"customer_id": customer_id})
        except Exception as e:
            error = 'Please check data request again.'
            _logger.info("\n%s", traceback.format_exc())
            pass
        if error:
            res['meta'].update({
                'message': error,
            })
        return res

    @http.route('/api/order/delete/', type='json', auth="none", csrf=False)
    def delete_order(self, **kwargs):
        res = {
            'meta': {
                'status': False,
                'message': None
            },
            'data': {
            }
        }
        error = ''
        #Check TOKEN
        token = request.httprequest.environ.get('HTTP_TOKEN', False)
        user = request.env['res.users'].check_token(token)
        if not user or not token:
            res['meta'].update({
                "status_code": 403,
                'message': 'Something wrong with your token, please contact Admin.',
            })
            return res
        #End check TOKEN
        try:
            values = json.loads(request.httprequest.data)
            sale_order_obj = request.env['sale.order'].sudo().browse(values.get('sale_order_id', False))
            sale_order_obj.write({
                            'state': 'cancel',
                        })
            sale_order_obj.unlink()
            res['meta'].update({
                    "status": True,
                    'message': 'Delete order successfull.',
                })
        except Exception as e:
            error = u'Please check data request again.'
            _logger.info("\n%s", traceback.format_exc())
            pass
        
        if error:
            res['meta'].update({
                'message': error,
            })
        return res

    @http.route('/api/sku/fetch_all', type='json', auth="none", csrf=False)
    def fetch_all_sku(self, **kwargs):
        res = {
            'meta': {
                'status': False,
                'message': None
            },
            'data': {
            }
        }
        error = ''
        #Check TOKEN
        token = request.httprequest.environ.get('HTTP_TOKEN', False)
        user = request.env['res.users'].check_token(token)
        if not user or not token:
            res['meta'].update({
                "status_code": 403,
                'message': 'Something wrong with your token, please contact Admin.',
            })
            return res
        #End check TOKEN
        try:
            array = [0]
            attribute_values = request.env['product.attribute.value'].sudo().search([('django_component_id', '!=', '')])
            for attribute_value in attribute_values:
                value = {}
                value['id'] = attribute_value.django_component_id
                value['name'] = attribute_value.name
                array.append(value)
            res['meta'].update({
                    "status": True,
                    'message': 'Fetch all SKU successfull.',
                })
            res['data'].update({
                    "sku_data": array[1:len(array)]
                })
        except Exception as e:
            error = u'Please check data request again.'
            _logger.info("\n%s", traceback.format_exc())
            pass
        
        if error:
            res['meta'].update({
                'message': error,
            })
        return res
    
    
    ###UTILS
    def process_master_bom(self, bom_obj, product_template_attribute_value, product_quantity):
        print("process_master_bom")
        print(product_template_attribute_value)
        bom_line = request.env['mrp.bom.line'].sudo().search([('bom_id', '=', bom_obj.id),('product_id', '=', product_template_attribute_value.product_id.id)])
        is_exist = False
        if len(bom_line) > 0:
            for line in bom_line:
                if product_template_attribute_value.id in line.bom_product_template_attribute_value_ids.ids:
                    is_exist = True
        
        if not is_exist:
            request.env['mrp.bom.line'].sudo().create({
                'bom_id': bom_obj.id,
                'product_id': product_template_attribute_value.product_id.id,
                'product_qty': product_quantity,
                'bom_product_template_attribute_value_ids': [(6, 0, [product_template_attribute_value.id])]
                })    

    def _ids2str(self, ids):
        return ','.join([str(i) for i in sorted(ids)])
    
    def _redefind_sku_id(self, id, qty):
        return id + '_qty_' + str(qty)
    
    def _redefind_sku_name(self, name , qty):
        return str(qty) + ' X ' + name

    def create_new_product_with_initial_variants(self, bom):
        print("create_new_product_with_initial_variants")
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

    def create_attribute_value(self, product_tmpl_obj, sku, product_qty):
        print("create_attribute_value")
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
        attribute_value_name = sku.get('name')
        attribute_value_id = sku.get('id')
        if product_qty > 1:
            attribute_value_id = self._redefind_sku_id(sku.get('id'), product_qty)
            attribute_value_name = self._redefind_sku_name(sku.get('name'), product_qty)
        attribute_value = request.env['product.attribute.value'].sudo().create({
            'name': attribute_value_name,
            'attribute_id': attribute.id,
            'django_component_id': attribute_value_id,
        })

        product_product = request.env['product.product'].sudo().search([('name', '=', sku.get('name')),
                                                                        ('type', '=', 'product'),
                                                                        ('lst_price', '=', sku.get('cost'))])
        
        if len(product_product) == 0:
            product_product = request.env['product.product'].sudo().create({
                'name': sku.get('name'),
                'type': 'product',
                'lst_price': sku.get('cost'),
                'sale_ok': True,
                'purchase_ok': True,
            })
        else:
            for i in product_product:
                if i.lst_price == sku.get('cost'):
                    product_product = i
                    break
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
        print(product_template_attribute_value)
        print(product_product)
        
        if product_qty > 1:
            product_template_attribute_value.write({
                        'product_id': product_product.id,
                        'is_price_linked': False,
                        'price_extra': product_qty * sku.get('cost')
                    })
        else:
            product_template_attribute_value.write({
                        'is_price_linked': True,
                        'product_id': product_product.id,
                    })
        return attribute_value