# -*- coding: utf-8 -*-
{
    'name': "Lambda: Extra Prices",

    'summary': """Lambda sells custom computers that are “built” during the selling process (product configurator) by adding different components, which creates different variants of the finished good. The base product’s price is $0 + components with extra prices. A lot of components are used in lots of different finished products. The goal is to “link” the price field on the product with the extra price field on the variant.""",

    'description': """
        Task ID: 2388232
        Requirement 1 - Link the price field with the extra price field
        Create an automated process of updating the “extra price” field on a variant across the whole system through updating the price on a product. First, we have to “link” a product with a variant so that then we can update the price on the product itself and that will auto-populate onto the extra prices. Users should still be able to change extra prices on variants manually.
        Requirement 2 - Have a pop-up window on the Quotation form view
        In an existing quote, it should ask for updated prices due to a change in component price. It should show a pop up for which component price has changed and give the option to Sales Rep to accept these changes. This change should not reflect automatically in a confirmed Sales Order.
        Requirement 3 - Change the extra price field type
        Change the extra price field type to be able to track the changes (which user manually changed the price)  in the chatter.
        Requirement 4 - Add weight to the base product form view
        Add weight and volume fields to the base product to auto-populate to all the variants of the product when changing on the base product.
        Requirement 5 - weight, volume, and shipping method confirmation
        Once a Delivery Order is confirmed, there should be a pop up confirming three things:
        Is the weight correct?
        Is the volume correct?
        What’s the shipping method for this order?
        If weight and volume are correct - confirm button, otherwise - enter weight/volume. The shipping carrier line should be replicating the “Add Shipping” option from the Sales Order form view.
        Requirement 6 - labels auto print
        Print FedEx label and packing slip automatically once the delivery order is validated.
        Requirement 7 - Automatically post invoice
        Once a delivery order is validated - an invoice for the respective sales order is created, posted, and printed automatically.

    """,

    'author': "Odoo Inc",
    'website': "http://www.odoo.com",
    'category': 'Custom Development',
    'license': 'OEEL-1',
    'version': '0.1',
    'depends': ['stock','sale_management'],
    'data': [
        'views/stock_picking_views.xml',
        'views/product_attributes_views.xml',
        'views/product_template_views.xml',
        'views/product_warning_wizard.xml',
        'views/delivery_warning_wizard.xml',
    ]
}
