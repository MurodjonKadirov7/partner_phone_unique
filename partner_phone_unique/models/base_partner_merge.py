from odoo import models


class BasePartnerMergeAutomaticWizard(models.TransientModel):
    _inherit = 'base.partner.merge.automatic.wizard'

    def _update_values(self, src_partners, dst_partner):
        # The core writes the number on the destination while the sources, only
        # deleted later, still hold it. Same pick as the core: the destination
        # first, then the last source. A third contact with this number still
        # refuses the merge.
        phone = dst_partner.phone or next(
            (partner.phone for partner in reversed(src_partners) if partner.phone), False)
        src_partners.filtered('phone').sudo().write({'phone': False})
        if phone and phone != dst_partner.phone:
            dst_partner.write({'phone': phone})
        return super()._update_values(src_partners, dst_partner)
