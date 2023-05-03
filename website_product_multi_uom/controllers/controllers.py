# -*- coding: utf-8 -*-
import json
from odoo.addons.website_sale.controllers.main import WebsiteSale
from odoo.addons.sale.controllers.variant import VariantController
from odoo import http, fields
from odoo.http import request
from odoo.tools.json import scriptsafe as json_scriptsafe


class ProductUOM(WebsiteSale):
    @http.route(['/shop/cart/update'], type='http', auth="public", methods=['POST'], website=True)
    def cart_update(self, product_id, add_qty=1, set_qty=0, **kw):
        """This route is called when adding a product to cart (no options)."""
        sale_order = request.website.sale_get_order(force_create=True)
        if sale_order.state != 'draft':
            request.session['sale_order_id'] = None
            sale_order = request.website.sale_get_order(force_create=True)

        product_custom_attribute_values = None
        if kw.get('product_custom_attribute_values'):
            product_custom_attribute_values = json_scriptsafe.loads(kw.get('product_custom_attribute_values'))

        no_variant_attribute_values = None
        if kw.get('no_variant_attribute_values'):
            no_variant_attribute_values = json_scriptsafe.loads(kw.get('no_variant_attribute_values'))
        product_uom_id = request.env["product.product"].sudo().browse(int(product_id)).uom_id
        order_dict = sale_order._cart_update(
            product_id=int(product_id),
            add_qty=add_qty,
            set_qty=set_qty,
            product_custom_attribute_values=product_custom_attribute_values,
            no_variant_attribute_values=no_variant_attribute_values,
            product_uom=int(kw.get('uom_id')) if kw.get('uom_id') else product_uom_id.id
        )

        ##########################################################################################
        # Extended Code Block
        line_id = order_dict['line_id']
        line_obj = http.request.env['sale.order.line'].sudo().search([("id", "=", int(line_id))])
        line_obj.product_uom = int(kw.get('uom_id')) if kw.get('uom_id') else line_obj.product_id.uom_id.id
        line_obj.product_uom_change()
        # End
        ##########################################################################################

        if kw.get('express'):
            return request.redirect("/shop/checkout?express=1")

        return request.redirect("/shop/cart")

    @http.route(['/shop/cart/update_json'], type='json', auth="public", methods=['POST'], website=True, csrf=False)
    def cart_update_json(self, product_id, line_id=None, add_qty=None, set_qty=None, display=True, **kw):
        """
        This route is called :
            - When changing quantity from the cart.
            - When adding a product from the wishlist.
            - When adding a product to cart on the same page (without redirection).
        """
        order = request.website.sale_get_order(force_create=1)
        if order.state != 'draft':
            request.website.sale_reset()
            if kw.get('force_create'):
                order = request.website.sale_get_order(force_create=1)
            else:
                return {}

        pcav = kw.get('product_custom_attribute_values')
        nvav = kw.get('no_variant_attribute_values')
        product_uom_id = request.env["product.product"].sudo().browse(int(product_id)).uom_id
        value = order._cart_update(
            product_id=product_id,
            line_id=line_id,
            add_qty=add_qty,
            set_qty=set_qty,
            product_custom_attribute_values=json_scriptsafe.loads(pcav) if pcav else None,
            no_variant_attribute_values=json_scriptsafe.loads(nvav) if nvav else None,
            product_uom=int(kw.get('uom_id')) if kw.get('uom_id') else product_uom_id.id

        )

        ##########################################################################################
        # Extended Code Block
        line_id = value['line_id']
        line_obj = http.request.env['sale.order.line'].sudo().search([("id", "=", int(line_id))])
        line_obj.product_uom = int(kw.get('uom_id')) if kw.get('uom_id') else line_obj.product_id.uom_id.id
        line_obj.product_uom_change()
        # End
        ##########################################################################################

        if not order.cart_quantity:
            request.website.sale_reset()
            return value

        order = request.website.sale_get_order()
        value['cart_quantity'] = order.cart_quantity

        if not display:
            return value

        value['website_sale.cart_lines'] = request.env['ir.ui.view']._render_template("website_sale.cart_lines", {
            'website_sale_order': order,
            'date': fields.Date.today(),
            'suggested_products': order._cart_accessories()
        })
        value['website_sale.short_cart_summary'] = request.env['ir.ui.view']._render_template("website_sale.short_cart_summary", {
            'website_sale_order': order,
        })
        return value


class VariantControllerExtended(VariantController):
    @http.route(['/sale/get_combination_info'], type='json', auth="user", methods=['POST'])
    def get_combination_info(self, product_template_id, product_id, combination, add_qty, pricelist_id, **kw):
        ##########################################################################################
        # Extended Code Block
        uom_id = None
        if kw.get('select'):
            selected_uom = int(kw.get('select'))
            uom_id = http.request.env['uom.uom'].sudo().browse(selected_uom)
            if uom_id.uom_type == 'bigger':
                add_qty = add_qty * uom_id.factor_inv
            if uom_id.uom_type == 'smaller':
                add_qty = add_qty / uom_id.factor
        # End
        ##########################################################################################

        combination = request.env['product.template.attribute.value'].browse(combination)
        pricelist = self._get_pricelist(pricelist_id)
        ProductTemplate = request.env['product.template']
        if 'context' in kw:
            ProductTemplate = ProductTemplate.with_context(**kw.get('context'))
        product_template = ProductTemplate.browse(int(product_template_id))
        res = product_template._get_combination_info(combination, int(product_id or 0), int(add_qty or 1), pricelist)
        if 'parent_combination' in kw:
            parent_combination = request.env['product.template.attribute.value'].browse(kw.get('parent_combination'))
            if not combination.exists() and product_id:
                product = request.env['product.product'].browse(int(product_id))
                if product.exists():
                    combination = product.product_template_attribute_value_ids
            res.update({
                'is_combination_possible': product_template._is_combination_possible(combination=combination,
                                                                                     parent_combination=parent_combination),
                'parent_exclusions': product_template._get_parent_attribute_exclusions(
                    parent_combination=parent_combination)
            })
        ##########################################################################################
        # Extended Code Block
        if uom_id:
            product_obj = http.request.env['product.product'].sudo().browse(int(product_id))
            pro_uom_id = product_obj.uom_id
            ref_price = 0
            product_qty = int(kw.get('qty'))
            if pro_uom_id.uom_type == 'bigger':
                ref_price = res['list_price'] / pro_uom_id.factor_inv
            if pro_uom_id.uom_type == 'reference':
                ref_price = res['list_price']
            if pro_uom_id.uom_type == 'smaller':
                ref_price = res['list_price'] * pro_uom_id.factor

            act_uom_id = http.request.env['uom.uom'].sudo().browse(int(kw.get('select')))
            act_price = 0
            if act_uom_id.uom_type == 'bigger':
                act_price = ref_price * act_uom_id.factor_inv
            if act_uom_id.uom_type == 'reference':
                act_price = ref_price
            if act_uom_id.uom_type == 'smaller':
                act_price = ref_price / uom_id.factor

            res['list_price'] = act_price * product_qty
            res['price'] = act_price * product_qty
        # End
        ##########################################################################################
        return res
