from odoo.exceptions import ValidationError
from odoo.tests.common import TransactionCase, tagged


@tagged('post_install', '-at_install')
class TestPartnerPhoneUnique(TransactionCase):
    """Phone uniqueness, including multi-company behaviour (the constraint is
    intentionally global: the same physical person must not be duplicated
    across companies)."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_a = cls.env.company
        cls.company_b = cls.env['res.company'].create({'name': 'PPU Test Co B'})

    def test_phone_digits_compute(self):
        partner = self.env['res.partner'].create({
            'name': 'Sanitize Me',
            'phone': '+998 (91) 111-22-33',
        })
        self.assertEqual(partner.phone_digits, '998911112233')
        partner.phone = False
        self.assertFalse(partner.phone_digits)

    def test_duplicate_phone_blocked(self):
        self.env['res.partner'].create({
            'name': 'First Owner',
            'phone': '+998 91 555 44 33',
        })
        with self.assertRaises(ValidationError):
            self.env['res.partner'].create({
                'name': 'Second Owner',
                # Same digits, different formatting.
                'phone': '998915554433',
            })

    def test_duplicate_phone_blocked_across_companies(self):
        """A partner of company A and a partner of company B with the same
        digits must be rejected: uniqueness is database-wide."""
        self.env['res.partner'].create({
            'name': 'Company A Contact',
            'phone': '+998 90 777 66 55',
            'company_id': self.company_a.id,
        })
        with self.assertRaises(ValidationError):
            self.env['res.partner'].create({
                'name': 'Company B Contact',
                'phone': '+998 (90) 777-66-55',
                'company_id': self.company_b.id,
            })

    def test_no_phone_is_not_a_duplicate(self):
        partners = self.env['res.partner'].create([
            {'name': 'No Phone 1'},
            {'name': 'No Phone 2'},
        ])
        self.assertEqual(len(partners), 2)
        self.assertFalse(partners[0].phone_digits)

    def test_rewrite_same_phone_on_same_partner_ok(self):
        partner = self.env['res.partner'].create({
            'name': 'Self Update',
            'phone': '+998 93 123 99 88',
        })
        # Re-formatting the partner's own number must not trip the constraint.
        partner.phone = '998 93 1239988'
        self.assertEqual(partner.phone_digits, '998931239988')

    def test_update_to_existing_phone_blocked(self):
        self.env['res.partner'].create({
            'name': 'Original Number Holder',
            'phone': '+998 94 222 11 00',
        })
        other = self.env['res.partner'].create({
            'name': 'Other Person',
            'phone': '+998 94 222 11 01',
        })
        with self.assertRaises(ValidationError):
            other.phone = '+998 94 222 11 00'

    def test_international_prefix_is_the_same_number(self):
        self.env['res.partner'].create({'name': 'Plus', 'phone': '+998 95 100 20 30'})
        with self.assertRaises(ValidationError):
            self.env['res.partner'].create({'name': 'Zeros', 'phone': '00998 95 100 20 30'})

    def test_same_batch_is_checked(self):
        with self.assertRaises(ValidationError):
            self.env['res.partner'].create([
                {'name': 'Batch 1', 'phone': '+998 95 200 30 40'},
                {'name': 'Batch 2', 'phone': '998952003040'},
            ])

    def test_phone_without_digits_is_ignored(self):
        partners = self.env['res.partner'].create([
            {'name': 'Text 1', 'phone': 'none'},
            {'name': 'Text 2', 'phone': 'none'},
        ])
        self.assertFalse(partners[0].phone_digits)

    def test_archived_contact_frees_the_number(self):
        old = self.env['res.partner'].create({'name': 'Old', 'phone': '+998 95 300 40 50'})
        old.active = False
        new = self.env['res.partner'].create({'name': 'New', 'phone': '+998 95 300 40 50'})
        self.assertEqual(new.phone_digits, '998953004050')
        # restoring the old contact would duplicate the number
        with self.assertRaises(ValidationError):
            old.active = True

    def test_onchange_warns_with_the_other_contact(self):
        self.env['res.partner'].create({'name': 'Number Owner', 'phone': '+998 95 400 50 60'})
        new = self.env['res.partner'].new({'name': 'Typing', 'phone': '95 400 50 60'})
        self.assertFalse(new._onchange_phone_check_duplicate(), 'different digits')
        new.phone = '998 95 400 50 60'
        warning = new._onchange_phone_check_duplicate()['warning']
        self.assertIn('Number Owner', warning['message'])

    def test_onchange_on_own_number_does_not_warn(self):
        partner = self.env['res.partner'].create({'name': 'Me', 'phone': '+998 95 500 60 70'})
        virtual = self.env['res.partner'].new({'phone': '998955006070'}, origin=partner)
        self.assertFalse(virtual._onchange_phone_check_duplicate())

    def test_digits_of_other_scripts_are_the_same_number(self):
        self.env['res.partner'].create({'name': 'Latin', 'phone': '+998 95 700 80 90'})
        for phone in ('+٩٩٨ ٩٥ ٧٠٠ ٨٠ ٩٠', '۹۹۸۹۵۷۰۰۸۰۹۰', '９９８９５７００８０９０', '٠٠٩٩٨٩٥٧٠٠٨٠٩٠'):
            with self.assertRaises(ValidationError), self.env.cr.savepoint():
                self.env['res.partner'].create({'name': 'Other script', 'phone': phone})

    def test_archived_contact_frees_the_number_in_any_context(self):
        self.env['res.partner'].create({'name': 'Old', 'phone': '+998 95 800 90 10', 'active': False})
        Partner = self.env['res.partner'].with_context(active_test=False)
        new = Partner.create({'name': 'New', 'phone': '+998 95 800 90 10'})
        self.assertEqual(new.phone_digits, '998958009010')
        typed = Partner.new({'phone': '+998 95 800 90 11'})
        self.assertFalse(typed._onchange_phone_check_duplicate())

    def test_duplicate_a_contact(self):
        partner = self.env['res.partner'].create({'name': 'Original', 'phone': '+998 95 900 10 20'})
        copy = partner.copy()
        self.assertFalse(copy.phone)
        self.assertEqual(partner.phone_digits, '998959001020')
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            partner.copy({'phone': partner.phone})

    def _merge(self, partners, destination):
        # action_merge: the button of the wizard
        self.env['base.partner.merge.automatic.wizard'].create({
            'partner_ids': [(6, 0, partners.ids)],
            'dst_partner_id': destination.id,
        }).action_merge()
        self.env.flush_all()
        self.assertFalse((partners - destination).exists())

    def test_merge_moves_the_number_to_the_destination(self):
        source = self.env['res.partner'].create({'name': 'Source', 'phone': '+998 97 100 20 30'})
        destination = self.env['res.partner'].create({'name': 'Destination'})
        self._merge(source + destination, destination)
        self.assertEqual(destination.phone, '+998 97 100 20 30')
        self.assertEqual(destination.phone_digits, '998971002030')
        # the merge leaves no exemption behind
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self.env['res.partner'].create({'name': 'After', 'phone': '+998 97 100 20 30'})

    def test_merge_keeps_the_number_of_the_destination(self):
        source = self.env['res.partner'].create({'name': 'Source', 'phone': '+998 97 200 30 40'})
        destination = self.env['res.partner'].create({'name': 'Destination', 'phone': '+998 97 200 30 41'})
        self._merge(source + destination, destination)
        self.assertEqual(destination.phone, '+998 97 200 30 41')

    def test_merge_duplicates_already_in_the_database(self):
        # The way out of the duplicates the module found at install
        source = self.env['res.partner'].create({'name': 'Source', 'phone': '+998 97 300 40 50'})
        destination = self.env['res.partner'].create({'name': 'Destination'})
        # Odoo 18: hisoblangan phone_digits flush paytida yoziladi — SQL'dan oldin
        # flush qilinmasa, u SQL qo'ygan qiymatni ustidan yozadi
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE res_partner SET phone = %s, phone_digits = %s WHERE id = %s",
            ['998 97 300 40 50', '998973004050', destination.id])
        destination.invalidate_recordset(['phone', 'phone_digits'])
        self._merge(source + destination, destination)
        self.assertEqual(destination.phone, '998 97 300 40 50')
        self.assertEqual(destination.phone_digits, '998973004050')

    def test_import_reports_the_duplicate_row(self):
        self.env['res.partner'].create({'name': 'Owner', 'phone': '+998 97 500 60 70'})
        result = self.env['res.partner'].load(['name', 'phone'], [
            ['Row 1', '+998 97 500 60 71'],
            ['Row 2', '998975006070'],
        ])
        self.assertFalse(result['ids'])
        # load() also repeats the error of a failed batch on its first row
        self.assertIn(
            (1, 'error'),
            [(message['rows']['from'], message['type']) for message in result['messages']])
        self.assertIn('Owner', result['messages'][-1]['message'])

    def test_phone_validation_field_is_left_alone(self):
        """phone_sanitized belongs to phone_validation (blacklist, SMS...)."""
        partner = self.env['res.partner'].create({
            'name': 'E164', 'phone': '+998 95 600 70 80',
            'country_id': self.env.ref('base.uz').id,
        })
        if 'phone_sanitized' in partner._fields:
            self.assertEqual(partner.phone_sanitized, '+998956007080')
        self.assertEqual(partner.phone_digits, '998956007080')

    def test_merge_refused_when_a_third_contact_has_the_number(self):
        source = self.env['res.partner'].create({'name': 'Source', 'phone': '+998 97 400 50 60'})
        destination = self.env['res.partner'].create({'name': 'Destination'})
        third = self.env['res.partner'].create({'name': 'Third'})
        # Odoo 18: hisoblangan phone_digits flush paytida yoziladi — SQL'dan oldin
        # flush qilinmasa, u SQL qo'ygan qiymatni ustidan yozadi
        self.env.flush_all()
        self.env.cr.execute(
            "UPDATE res_partner SET phone = %s, phone_digits = %s WHERE id = %s",
            ['998 97 400 50 60', '998974005060', third.id])
        third.invalidate_recordset(['phone', 'phone_digits'])
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self._merge(source + destination, destination)

    def test_no_context_key_bypasses_the_check(self):
        self.env['res.partner'].create({'name': 'Owner', 'phone': '+998 97 600 70 80'})
        with self.assertRaises(ValidationError):
            self.env['res.partner'].with_context(partner_phone_unique_merge=True).create(
                {'name': 'Bypass', 'phone': '+998 97 600 70 80'})

    def test_placeholder_numbers_are_not_duplicates(self):
        partners = self.env['res.partner'].create([
            {'name': 'Zero 1', 'phone': '0'},
            {'name': 'Zero 2', 'phone': '0'},
            {'name': 'Zero 3', 'phone': '000'},
        ])
        self.assertFalse(partners.filtered('phone_digits'))

    def test_visitor_does_not_learn_the_owner(self):
        self.env['res.partner'].create({'name': 'Secret Owner', 'phone': '+998 97 700 80 90'})
        public = self.env.ref('base.public_user')
        with self.assertRaises(ValidationError) as error:
            self.env['res.partner'].with_user(public).sudo().create(
                {'name': 'Visitor', 'phone': '+998 97 700 80 90'})
        self.assertNotIn('Secret Owner', str(error.exception))


    # ------------------------------------------------------------------
    # Odoo 18: res.partner also has a Mobile field, checked the same way
    # ------------------------------------------------------------------
    def test_mobile_taken_by_another_contacts_phone(self):
        self.env['res.partner'].create({'name': 'Phone Owner', 'phone': '+998 97 810 20 30'})
        with self.assertRaises(ValidationError) as error, self.env.cr.savepoint():
            self.env['res.partner'].create({'name': 'Dup', 'mobile': '998978102030'})
        self.assertIn('Phone Owner', str(error.exception))
        self.assertIn('998978102030', str(error.exception), 'the number that was typed')

    def test_phone_taken_by_another_contacts_mobile(self):
        self.env['res.partner'].create({'name': 'Mobile Owner', 'mobile': '+998 97 820 20 30'})
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self.env['res.partner'].create({'name': 'Dup', 'phone': '00998 97 820 20 30'})
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self.env['res.partner'].create({'name': 'Dup 2', 'mobile': '998978202030'})

    def test_same_number_in_phone_and_mobile_of_one_contact(self):
        partner = self.env['res.partner'].create(
            {'name': 'Both', 'phone': '+998 97 830 20 30', 'mobile': '998978302030'})
        self.assertEqual(partner.mobile_digits, partner.phone_digits)
        partner.write({'mobile': '+998 97 830 20 30'})

    def test_onchange_on_mobile_warns(self):
        self.env['res.partner'].create({'name': 'Number Owner', 'phone': '+998 97 840 20 30'})
        new = self.env['res.partner'].new({'name': 'Typing', 'mobile': '998978402030'})
        self.assertIn('Number Owner', new._onchange_mobile_check_duplicate()['warning']['message'])
        partner = self.env['res.partner'].create({'name': 'Me', 'mobile': '+998 97 850 20 30'})
        virtual = self.env['res.partner'].new({'mobile': '998978502030'}, origin=partner)
        self.assertFalse(virtual._onchange_mobile_check_duplicate(), 'own number')

    def test_duplicate_a_contact_drops_the_mobile(self):
        partner = self.env['res.partner'].create({'name': 'Original', 'mobile': '+998 97 860 20 30'})
        self.assertFalse(partner.copy().mobile)

    def test_archived_contact_frees_its_mobile(self):
        self.env['res.partner'].create({'name': 'Old', 'mobile': '+998 97 870 20 30', 'active': False})
        new = self.env['res.partner'].create({'name': 'New', 'phone': '+998 97 870 20 30'})
        self.assertEqual(new.phone_digits, '998978702030')

    def test_merge_moves_the_mobile_and_the_phone(self):
        # The source holds one number in both fields: no false duplicate on merge
        source = self.env['res.partner'].create(
            {'name': 'Source', 'phone': '+998 97 880 20 30', 'mobile': '+998 97 880 20 30'})
        destination = self.env['res.partner'].create({'name': 'Destination'})
        self._merge(source + destination, destination)
        self.assertEqual(destination.phone, '+998 97 880 20 30')
        self.assertEqual(destination.mobile, '+998 97 880 20 30')
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            self.env['res.partner'].create({'name': 'After', 'mobile': '998978802030'})
