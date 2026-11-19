# Copyright todoo.uz. License OPL-1 (Odoo Proprietary License v1.0).
{
    'name': 'Partner Phone Unique | Prevent Duplicate Contacts by Phone Number',
    'version': '20.0.1.1.1',
    'category': 'Contacts',
    'summary': 'Block duplicate contacts: warn as soon as a phone number already '
               'used by another contact is typed, and refuse to save it',
    'description': """
Partner Phone Unique
====================
One phone number belongs to one contact.

* Typing a number another contact already has shows a warning right away, with
  the name of that contact.
* Saving is refused: two contacts cannot be saved with the same number.

Numbers are compared on their digits only, so +998 90 123 45 67, 998901234567
and 00998 (90) 123-45-67 are the same number. Duplicates already in the database
do not block the installation.
""",
    'author': 'todoo.uz',
    'website': 'https://todoo.uz',
    'support': 'info@todoo.uz',
    'license': 'OPL-1',
    'images': ['static/description/banner.png'],
    'depends': ['contacts'],
    'installable': True,
    'application': False,
}
