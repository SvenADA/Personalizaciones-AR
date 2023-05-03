# -*- coding: utf-8 -*-
#################################################################################
# Author      : Webkul Software Pvt. Ltd. (<https://webkul.com/>)
# Copyright(c): 2015-Present Webkul Software Pvt. Ltd.
# All Rights Reserved.
#
#
#
# This program is copyright property of the author mentioned above.
# You can`t redistribute it and/or modify it.
#
#
# You should have received a copy of the License along with this program.
# If not, see <https://store.webkul.com/license.html/>
#################################################################################
{
  "name"                 :  "Odoo Rest Api",
  "summary"              :  """The module create RESTful API for Odoo and allows you to access and modify data using HTTP requests to manage fetch and manage data from the Odoo.""",
  "category"             :  "Extra Tools",
  "version"              :  "1.0.0",
  "author"               :  "J2L Tech",
  "license"              :  "Other proprietary",
  "support"              :  "Luis Aquino -> laquinobarrientos@gmail.com",
  "description"          :  """Odoo Rest Api
Add record to database
Delete record to Database
Modify data in Odoo database
Use HTTP to modify data
RESTful API in Odoo
Use HTTP requests to fetch data in Odoo""",
  "depends"              :  ['base'],
  "data"                 :  [
                             'security/ir.model.access.csv',
                             'views/rest_api_views.xml',
                             'views/templates.xml',
                            ],
  "demo"                 :  ['demo/demo.xml'],
  "application"          :  True,
  "installable"          :  True,
}