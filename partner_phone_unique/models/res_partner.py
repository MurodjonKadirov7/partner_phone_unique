import re

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

# Numbers are compared on their digits only: spaces, brackets, dashes ignored.
# \d also matches the digits of other scripts (Arabic-Indic, full-width...).
_DIGIT_RE = re.compile(r'\d')
# Below this, a value is a placeholder (0, 000...) rather than a phone number.
_MIN_DIGITS = 5


class ResPartner(models.Model):
    _inherit = 'res.partner'

    # Deliberately not phone_sanitized: that field belongs to phone_validation,
    # holds the E.164 number and is what the phone blacklist, SMS, mass mailing,
    # CRM, WhatsApp and VoIP compare against.
    phone_digits = fields.Char(
        string='Phone Digits',
        compute='_compute_phone_digits',
        store=True,
        index=True,
        help='Digits-only phone used to detect duplicate contacts.',
    )

    @staticmethod
    def _phone_to_digits(number):
        if not number:
            return False
        digits = ''.join(str(int(digit)) for digit in _DIGIT_RE.findall(number))
        # 00 and + are the same international prefix
        if digits.startswith('00'):
            digits = digits[2:]
        return digits if len(digits) >= _MIN_DIGITS else False

    @api.depends('phone')
    def _compute_phone_digits(self):
        for partner in self:
            partner.phone_digits = self._phone_to_digits(partner.phone)

    def _find_phone_duplicate(self, digits, exclude_ids):
        """Return another contact having this number (empty recordset if none)."""
        if not digits:
            return self.browse()
        # sudo: the number is unique in the whole database, including contacts
        # the record rules of a multi-company setup would hide.
        return self.sudo().search([
            ('phone_digits', '=', digits),
            ('id', 'not in', list(exclude_ids)),
            # explicit: a caller's active_test=False must not count archived contacts
            ('active', '=', True),
        ], limit=1)

    def copy_data(self, default=None):
        # The copy of a contact cannot keep a number that must stay unique
        vals_list = super().copy_data(default=default)
        if 'phone' not in (default or {}):
            for vals in vals_list:
                vals.pop('phone', None)
        return vals_list

    @api.constrains('phone_digits', 'active')
    def _check_phone_unique(self):
        # While modules load, the field is computed for the existing contacts
        # and data files create theirs: duplicates already in the database must
        # not block an install or an upgrade. Only users' changes are checked.
        if not self.env.registry.ready:
            return
        for partner in self:
            # An archived contact holds no number; restoring it checks again.
            if not partner.phone_digits or not partner.active:
                continue
            duplicate = partner._find_phone_duplicate(partner.phone_digits, partner.ids)
            if duplicate:
                if not self.env.user._is_internal():
                    # A website visitor must not learn who owns a number.
                    raise ValidationError(_('This phone number is already used by another contact.'))
                raise ValidationError(_(
                    'The phone number "%(phone)s" is already used by another contact: %(name)s.',
                    phone=partner.phone,
                    name=duplicate.display_name,
                ))

    @api.onchange('phone')
    def _onchange_phone_check_duplicate(self):
        digits = self._phone_to_digits(self.phone)
        if not digits:
            return
        # _origin is the saved record; empty on a new contact.
        duplicate = self._find_phone_duplicate(digits, self._origin.ids)
        if duplicate:
            return {'warning': {
                'title': _('Duplicate phone number'),
                'message': _(
                    'This phone number is already used by another contact: %s.',
                    duplicate.display_name,
                ),
            }}
