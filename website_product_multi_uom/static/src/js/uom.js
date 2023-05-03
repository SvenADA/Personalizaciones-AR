odoo.define('website_product_multi_uom.uom', function (require) {
    'use strict';
    require('website_sale.website_sale');

    var publicWidget = require('web.public.widget');
    publicWidget.registry.WebsiteSale.include({
        events: _.extend({}, publicWidget.registry.WebsiteSale.prototype.events || {}, {
            'change #uom_selector': '_onChangeUom_selector',
        }),

        _onChangeUom_selector: function (ev) {
            this.onChangeVariant(ev);
        },
    })

});

odoo.define('website_product_multi_uom.uom1', function (require) {
    'use strict';

    var publicWidget = require('web.public.widget');
    var core = require('web.core');
    var ajax = require('web.ajax');
    var wSaleUtils = require('website_sale.utils');

    require('website_sale.website_sale');
    publicWidget.registry.WebsiteSale.include({


        _getCombinationInfo: function (ev) {
            if ($(ev.target).hasClass('variant_custom_value')) {
                return Promise.resolve();
            }

            const $parent = $(ev.target).closest('.js_product');
            const combination = this.getSelectedVariantValues($parent);
            let parentCombination;

            if ($parent.hasClass('main_product')) {
                parentCombination = $parent.find('ul[data-attribute_exclusions]').data('attribute_exclusions').parent_combination;
                const $optProducts = $parent.parent().find(`[data-parent-unique-id='${$parent.data('uniqueId')}']`);

                for (const optionalProduct of $optProducts) {
                    const $currentOptionalProduct = $(optionalProduct);
                    const childCombination = this.getSelectedVariantValues($currentOptionalProduct);
                    const productTemplateId = parseInt($currentOptionalProduct.find('.product_template_id').val());
                    ajax.jsonRpc(this._getUri('/sale/get_combination_info'), 'call', {
                        'product_template_id': productTemplateId,
                        'product_id': this._getProductId($currentOptionalProduct),
                        'combination': childCombination,
                        'add_qty': parseInt($currentOptionalProduct.find('input[name="add_qty"]').val()),
                        'pricelist_id': this.pricelistId || false,
                        'parent_combination': combination,
                    }).then((combinationData) => {
                        this._onChangeCombination(ev, $currentOptionalProduct, combinationData);
                        this._checkExclusions($currentOptionalProduct, childCombination, combinationData.parent_exclusions);
                    });
                }
            } else {
                parentCombination = this.getSelectedVariantValues(
                    $parent.parent().find('.js_product.in_cart.main_product')
                );
            }

            return ajax.jsonRpc(this._getUri('/sale/get_combination_info'), 'call', {
                'product_template_id': parseInt($parent.find('.product_template_id').val()),
                'product_id': this._getProductId($parent),
                'combination': combination,
                'add_qty': parseInt($parent.find('input[name="add_qty"]').val()),
                'pricelist_id': this.pricelistId || false,
                'parent_combination': parentCombination,
                'select': $("#uom_selector").val(), //param added
                'qty': $(".quantity").val(), //param added
            }).then((combinationData) => {
                this._onChangeCombination(ev, $parent, combinationData);
                this._checkExclusions($parent, combination, combinationData.parent_exclusions);
            });
        },



        _handleAdd: function ($form) {
            var self = this;
            this.$form = $form;

            var productSelector = [
                'input[type="hidden"][name="product_id"]',
                'input[type="radio"][name="product_id"]:checked'
            ];

            var productReady = this.selectOrCreateProduct(
                $form,
                parseInt($form.find(productSelector.join(', ')).first().val(), 10),
                $form.find('.product_template_id').val(),
                false
            );

            return productReady.then(function (productId) {
                $form.find(productSelector.join(', ')).val(productId);

                self.rootProduct = {
                    product_id: productId,
                    quantity: parseFloat($form.find('input[name="add_qty"]').val() || 1),
                    // Extended
                    uom_id: parseInt($form.find('select[name="uom_selector"]').val()),
                    //
                    product_custom_attribute_values: self.getCustomVariantValues($form.find('.js_product')),
                    variant_values: self.getSelectedVariantValues($form.find('.js_product')),
                    no_variant_attribute_values: self.getNoVariantAttributeValues($form.find('.js_product'))
                };

                return self._onProductReady();
            });
        },

        _changeCartQuantity: function ($input, value, $dom_optional, line_id, productIDs) {
            _.each($dom_optional, function (elem) {
                $(elem).find('.js_quantity').text(value);
                productIDs.push($(elem).find('span[data-product-id]').data('product-id'));
            });
            $input.data('update_change', true);
            this._rpc({
                route: "/shop/cart/update_json",
                params: {
                    line_id: line_id,
                    product_id: parseInt($input.data('product-id'), 10),
                    set_qty: value,
                    uom_id: $input.data('line-uom-id')
                },
            }).then(function (data) {
                $input.data('update_change', false);
                var check_value = parseInt($input.val() || 0, 10);
                if (isNaN(check_value)) {
                    check_value = 1;
                }
                if (value !== check_value) {
                    $input.trigger('change');
                    return;
                }
                if (!data.cart_quantity) {
                    return window.location = '/shop/cart';
                }
                wSaleUtils.updateCartNavBar(data);
                $input.val(data.quantity);
                $('.js_quantity[data-line-id=' + line_id + ']').val(data.quantity).text(data.quantity);

                if (data.warning) {
                    var cart_alert = $('.oe_cart').parent().find('#data_warning');
                    if (cart_alert.length === 0) {
                        $('.oe_cart').prepend('<div class="alert alert-danger alert-dismissable" role="alert" id="data_warning">' +
                            '<button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button> ' + data.warning + '</div>');
                    }
                    else {
                        cart_alert.html('<button type="button" class="close" data-dismiss="alert" aria-hidden="true">&times;</button> ' + data.warning);
                    }
                    $input.val(data.quantity);
                }
            });
        },

    });
});