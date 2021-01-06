import datetime
from datetime import timedelta
from functools import partial

from odoo import models, _, api
from odoo.addons.resource.models.resource import make_aware, Intervals
from odoo.tools.float_utils import float_compare


class MrpWorkcenter(models.Model):
    _inherit = 'mrp.workcenter'

    def _get_first_available_slot(self, start_datetime, duration):
        """Get the first available interval for the workcenter in `self`.

        The available interval is disjoinct with all other workorders planned on this workcenter, but
        can overlap the time-off of the related calendar (inverse of the working hours).
        Return the first available interval (start datetime, end datetime) or,
        if there is none before 700 days, a tuple error (False, 'error message').

        :param start_datetime: begin the search at this datetime
        :param duration: minutes needed to make the workorder (float)
        :rtype: tuple
        """
        self.ensure_one()
        start_datetime, revert = make_aware(start_datetime)

        get_available_intervals = partial(self.resource_calendar_id._work_intervals,
                                          domain=[('time_type', 'in', ['other', 'leave'])], resource=self.resource_id)
        get_workorder_intervals = partial(self.resource_calendar_id._leave_intervals,
                                          domain=[('time_type', '=', 'other')], resource=self.resource_id)

        remaining = duration
        start_interval = start_datetime
        delta = timedelta(days=14)

        for n in range(50):  # 50 * 14 = 700 days in advance (hardcoded)
            dt = start_datetime + delta * n
            available_intervals = get_available_intervals(dt, dt + delta)
            workorder_intervals = get_workorder_intervals(dt, dt + delta)
            for start, stop, dummy in available_intervals:
                interval_minutes = (stop - start).total_seconds() / 60
                # If the remaining minutes has never decrease update start_interval
                if remaining == duration:
                    start_interval = start
                # If there is a overlap between the possible available interval and a others WO
                if Intervals([(start_interval, start + timedelta(minutes=min(remaining, interval_minutes)),
                               dummy)]) & workorder_intervals:
                    remaining = duration
                    start_interval = start
                elif float_compare(interval_minutes, remaining, precision_digits=3) >= 0:
                    return revert(start_interval), revert(start + timedelta(minutes=remaining))
                # Decrease a part of the remaining duration
                remaining -= interval_minutes
        return False, 'Not available slot 700 days after the planned start'
