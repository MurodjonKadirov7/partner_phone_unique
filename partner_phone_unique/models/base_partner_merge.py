from odoo import models


class BasePartnerMergeAutomaticWizard(models.TransientModel):
    _inherit = 'base.partner.merge.automatic.wizard'

    def _update_values(self, src_partners, dst_partner):
        # The core writes the number on the destination while the sources, only
        # deleted later, still hold it. Same pick as the core: the destination
        # first, then the last source. A third contact with this number still
        # refuses the merge.
        # Odoo 18: the same for the Mobile field. Both fields of the sources are
        # cleared first: a source may hold one number in its Phone and Mobile.
        numbers = {
            field_name: dst_partner[field_name] or next(
                (partner[field_name] for partner in reversed(src_partners) if partner[field_name]), False)
            for field_name in ('phone', 'mobile')
        }
        src_partners.filtered(lambda partner: partner.phone or partner.mobile).sudo().write(
            {'phone': False, 'mobile': False})
        values = {
            field_name: number for field_name, number in numbers.items()
            if number and number != dst_partner[field_name]
        }
        if values:
            dst_partner.write(values)
        return super()._update_values(src_partners, dst_partner)
