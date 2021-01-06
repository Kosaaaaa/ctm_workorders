# -*- coding: utf-8 -*-
from collections import defaultdict
import json
from odoo import models, fields, api, _
from odoo.tools import format_datetime


class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    is_parallel_work = fields.Boolean(default=False)

    def _action_confirm(self):
        workorders_by_production = defaultdict(lambda: self.env['mrp.workorder'])
        for workorder in self:
            workorders_by_production[workorder.production_id] |= workorder

        for production, workorders in workorders_by_production.items():
            workorders_by_bom = defaultdict(lambda: self.env['mrp.workorder'])
            bom = self.env['mrp.bom']
            moves = production.move_raw_ids | production.move_finished_ids

            for workorder in self:
                if workorder.operation_id.bom_id:
                    bom = workorder.operation_id.bom_id
                if not bom:
                    bom = workorder.production_id.bom_id
                previous_workorder = workorders_by_bom[bom][-1:]
                previous_workorder.next_work_order_id = workorder.id
                workorders_by_bom[bom] |= workorder

                moves.filtered(lambda m: m.operation_id == workorder.operation_id).write({
                    'workorder_id': workorder.id
                })

            exploded_boms, dummy = production.bom_id.explode(production.product_id, 1,
                                                             picking_type=production.bom_id.picking_type_id)
            exploded_boms = {b[0]: b[1] for b in exploded_boms}
            for move in moves:
                if move.workorder_id:
                    continue
                bom = move.bom_line_id.bom_id
                while bom and bom not in workorders_by_bom:
                    bom_data = exploded_boms.get(bom, {})
                    bom = bom_data.get('parent_line') and bom_data['parent_line'].bom_id or False
                if bom in workorders_by_bom:
                    move.write({
                        'workorder_id': workorders_by_bom[bom][-1:].id
                    })
                else:
                    move.write({
                        'workorder_id': workorders_by_bom[production.bom_id][-1:].id
                    })

            for workorders in workorders_by_bom.values():
                if workorders[0].state == 'pending':
                    workorders[0].state = 'ready'
                for workorder in workorders:
                    if workorder.is_parallel_work is True and workorder.state == 'pending':
                        workorder.state = 'ready'
                    workorder._start_nextworkorder()

    # TODO: WHY IT DOES NOT WORK
    # def _get_conflicted_workorder_ids(self):
    #     """Get conlicted workorder(s) with self.
    #
    #     Conflict means having two workorders in the same time in the same workcenter.
    #     If one of workorders is parallel work there is no conflict.
    #
    #     :return: defaultdict with key as workorder id of self and value as related conflicted workorder
    #     """
    #     self.flush(['state', 'date_planned_start', 'date_planned_finished', 'workcenter_id'])
    #     sql = """
    #          SELECT wo1.id, wo2.id
    #          FROM mrp_workorder wo1, mrp_workorder wo2
    #          WHERE
    #              wo1.id IN %s
    #              AND wo1.state IN ('pending','ready')
    #              AND wo2.state IN ('pending','ready')
    #              AND wo1.id != wo2.id
    #              AND wo1.workcenter_id = wo2.workcenter_id
    #              AND (wo1.is_parallel_work IS NOT TRUE OR wo2.is_parallel_work IS NOT TRUE)
    #              AND (DATE_TRUNC('second', wo2.date_planned_start), DATE_TRUNC('second', wo2.date_planned_finished))
    #                  OVERLAPS (DATE_TRUNC('second', wo1.date_planned_start), DATE_TRUNC('second', wo1.date_planned_finished))
    #      """
    #     self.env.cr.execute(sql, [tuple(self.ids)])
    #     res = defaultdict(list)
    #     for wo1, wo2 in self.env.cr.fetchall():
    #         res[wo1].append(wo2)
    #     return res

    @api.depends('production_state', 'date_planned_start', 'date_planned_finished')
    def _compute_json_popover(self):
        previous_wo_data = self.env['mrp.workorder'].read_group(
            [('next_work_order_id', 'in', self.ids)],
            ['ids:array_agg(id)', 'date_planned_start:max', 'date_planned_finished:max'],
            ['next_work_order_id'])
        previous_wo_dict = dict([(x['next_work_order_id'][0], {
            'id': x['ids'][0],
            'date_planned_start': x['date_planned_start'],
            'date_planned_finished': x['date_planned_finished']})
                                 for x in previous_wo_data])
        if self.ids:
            conflicted_dict = self._get_conflicted_workorder_ids()
        for wo in self:
            infos = []
            if not wo.date_planned_start or not wo.date_planned_finished or not wo.ids:
                wo.show_json_popover = False
                wo.json_popover = False
                continue
            if wo.state in ['pending', 'ready']:
                previous_wo = previous_wo_dict.get(wo.id)
                prev_start = previous_wo and previous_wo['date_planned_start'] or False
                prev_finished = previous_wo and previous_wo['date_planned_finished'] or False
                if wo.state == 'pending' and prev_start and not (prev_start > wo.date_planned_start):
                    infos.append({
                        'color': 'text-primary',
                        'msg': _("Waiting the previous work order, planned from %(start)s to %(end)s",
                                 start=format_datetime(self.env, prev_start, dt_format=False),
                                 end=format_datetime(self.env, prev_finished, dt_format=False))
                    })
                if wo.date_planned_finished < fields.Datetime.now():
                    infos.append({
                        'color': 'text-warning',
                        'msg': _("The work order should have already been processed.")
                    })
                if prev_start and prev_start > wo.date_planned_start:
                    infos.append({
                        'color': 'text-danger',
                        'msg': _("Scheduled before the previous work order, planned from %(start)s to %(end)s",
                                 start=format_datetime(self.env, prev_start, dt_format=False),
                                 end=format_datetime(self.env, prev_finished, dt_format=False))
                    })
                # If workorder or next is parallel won't show conflict
                if conflicted_dict.get(wo.id) and not (wo.is_parallel_work or wo.next_work_order_id.is_parallel_work):
                    infos.append({
                        'color': 'text-danger',
                        'msg': _("Planned at the same time as other workorder(s) at %s", wo.workcenter_id.display_name)
                    })
            color_icon = infos and infos[-1]['color'] or False
            wo.show_json_popover = bool(color_icon)
            wo.json_popover = json.dumps({
                'infos': infos,
                'color': color_icon,
                'icon': 'fa-exclamation-triangle' if color_icon in ['text-warning',
                                                                    'text-danger'] else 'fa-info-circle',
                'replan': color_icon not in [False, 'text-primary']
            })
