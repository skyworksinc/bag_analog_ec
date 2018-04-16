# -*- coding: utf-8 -*-

"""This package defines various passives template classes.
"""

from typing import TYPE_CHECKING, Dict, Set, Any

from bag.layout.util import BBox
from bag.layout.routing import TrackID
from bag.layout.template import TemplateBase

from abs_templates_ec.analog_core.substrate import SubstrateContact

if TYPE_CHECKING:
    from bag.layout.template import TemplateDB


class MOMCapCore(TemplateBase):
    """A metal-only finger cap.

    ports are drawn on the layer above cap_top_layer.

    Parameters
    ----------
    temp_db : :class:`bag.layout.template.TemplateDB`
            the template database.
    lib_name : str
        the layout library name.
    params : dict[str, any]
        the parameter values.
    used_names : set[str]
        a set of already used cell names.
    **kwargs :
        dictionary of optional parameters.  See documentation of
        :class:`bag.layout.template.TemplateBase` for details.
    """

    def __init__(self, temp_db, lib_name, params, used_names, **kwargs):
        # type: (TemplateDB, str, Dict[str, Any], Set[str], **kwargs) -> None
        TemplateBase.__init__(self, temp_db, lib_name, params, used_names, **kwargs)
        self._sch_params = None

    @property
    def sch_params(self):
        return self._sch_params

    @classmethod
    def get_params_info(cls):
        # type: () -> Dict[str, str]
        return dict(
            cap_bot_layer='MOM cap bottom layer.',
            cap_top_layer='MOM cap top layer.',
            cap_width='MOM cap width, in layout units.',
            cap_height='MOM cap height, in layout units.',
            cap_margin='margin between cap and boundary, in layout units.',
            port_width='port track width, in number of tracks.',
            port_idx='port track index.  Can be int, two-int tuple, or None.  Defaults to center.',
            cap_options='MOM cap layout options.',
            half_blk_x='True to allow half horizontal blocks.',
            half_blk_y='True to allow half vertical blocks.',
            show_pins='True to show pin labels.',
        )

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            cap_margin=0,
            port_width=1,
            port_idx=None,
            cap_options=None,
            half_blk_x=True,
            half_blk_y=True,
            show_pins=True,
        )

    def draw_layout(self):
        # type: () -> None
        cap_bot_layer = self.params['cap_bot_layer']
        cap_top_layer = self.params['cap_top_layer']
        cap_width = self.params['cap_width']
        cap_height = self.params['cap_height']
        cap_margin = self.params['cap_margin']
        port_width = self.params['port_width']
        port_idx = self.params['port_idx']
        cap_options = self.params['cap_options']
        half_blk_x = self.params['half_blk_x']
        half_blk_y = self.params['half_blk_y']
        show_pins = self.params['show_pins']

        res = self.grid.resolution

        # setup capacitor options
        port_layer = cap_top_layer + 1
        top_w = self.grid.get_track_width(port_layer, port_width, unit_mode=True)
        cap_port_width = self.grid.get_min_track_width(cap_top_layer, top_w=top_w, unit_mode=True)
        if cap_options is None:
            cap_options = dict(port_widths={cap_top_layer: cap_port_width})
        elif 'port_widths' in cap_options:
            cap_options = cap_options.copy()
            cap_options['port_widths'] = {cap_top_layer: cap_port_width}
        bot_w = self.grid.get_track_width(cap_top_layer, cap_port_width, unit_mode=True)

        # get port locations
        min_len = self.grid.get_min_length(port_layer, port_width, unit_mode=True)
        via_ext = self.grid.get_via_extensions(cap_top_layer, cap_port_width, port_width,
                                               unit_mode=True)[1]
        res_len = top_w
        port_len = max(top_w, min_len - 2 * via_ext - bot_w - res_len)

        # set size
        cap_width = int(round(cap_width / res))
        cap_height = int(round(cap_height / res))
        cap_margin = int(round(cap_margin / res))
        bnd_box = BBox(0, 0, cap_width, cap_height, res, unit_mode=True)
        self.set_size_from_bound_box(port_layer, bnd_box, round_up=True,
                                     half_blk_x=half_blk_x, half_blk_y=half_blk_y)
        bnd_box = self.bound_box

        # draw cap
        cap_width = bnd_box.width_unit - 2 * cap_margin
        cap_height = bnd_box.height_unit - 2 * cap_margin
        cap_xl = bnd_box.xc_unit - cap_width // 2
        cap_yb = bnd_box.yc_unit - cap_height // 2
        cap_box = BBox(cap_xl, cap_yb, cap_xl + cap_width, cap_yb + cap_height, res, unit_mode=True)
        num_layer = cap_top_layer - cap_bot_layer + 1
        cap_ports = self.add_mom_cap(cap_box, cap_bot_layer, num_layer, **cap_options)

        cp, cn = cap_ports[cap_top_layer]
        cp = cp[0]
        cn = cn[0]
        idx_default = self.grid.coord_to_nearest_track(port_layer, cp.middle, half_track=True)
        if port_idx is None:
            plus_idx = minus_idx = idx_default
        elif isinstance(port_idx, int):
            plus_idx = minus_idx = port_idx
        else:
            minus_idx, plus_idx = port_idx
            if minus_idx is None:
                minus_idx = idx_default
            if plus_idx is None:
                plus_idx = idx_default
        plus_tid = TrackID(port_layer, plus_idx, width=port_width)
        minus_tid = TrackID(port_layer, minus_idx, width=port_width)

        if cp.track_id.base_index < cn.track_id.base_index:
            warr0, warr1 = cp, cn
            name0, name1 = 'plus', 'minus'
            tid0, tid1 = plus_tid, minus_tid
        else:
            warr0, warr1 = cn, cp
            name0, name1 = 'minus', 'plus'
            tid0, tid1 = minus_tid, plus_tid

        warr0 = self.connect_to_tracks(warr0, tid0)
        warr1 = self.connect_to_tracks(warr1, tid1)
        res_len *= res
        port_len *= res
        self.add_res_metal_warr(port_layer, tid0.base_index, warr0.lower - res_len, warr0.lower,
                                width=port_width)
        self.add_res_metal_warr(port_layer, tid1.base_index, warr1.upper, warr1.upper + res_len,
                                width=port_width)
        warr0 = self.add_wires(port_layer, tid0.base_index, warr0.lower - res_len - port_len,
                               warr0.lower - res_len, width=port_width)
        warr1 = self.add_wires(port_layer, tid1.base_index, warr1.upper + res_len,
                               warr1.upper + res_len + port_len, width=port_width)

        self.add_pin(name0, warr0, show=show_pins)
        self.add_pin(name1, warr1, show=show_pins)

        res_w = top_w * res * self.grid.layout_unit
        res_l = res_len * self.grid.layout_unit
        self._sch_params = dict(
            w=res_w,
            l=res_l,
            layer=port_layer,
        )


class MOMCapChar(TemplateBase):
    """A class that appended substrate contacts on top and bottom of a ResArrayBase.

    Parameters
    ----------
    temp_db : TemplateDB
            the template database.
    lib_name : str
        the layout library name.
    params : Dict[str, Any]
        the parameter values.
    used_names : Set[str]
        a set of already used cell names.
    **kwargs
        dictionary of optional parameters.  See documentation of
        :class:`bag.layout.template.TemplateBase` for details.
    """

    def __init__(self, temp_db, lib_name, params, used_names, **kwargs):
        # type: (TemplateDB, str, Dict[str, Any], Set[str], **kwargs) -> None
        TemplateBase.__init__(self, temp_db, lib_name, params, used_names, **kwargs)
        self._sch_params = None

    @property
    def sch_params(self):
        return self._sch_params

    @classmethod
    def get_params_info(cls):
        # type: () -> Dict[str, str]
        return dict(
            cap_bot_layer='MOM cap bottom layer.',
            cap_top_layer='MOM cap top layer.',
            cap_width='MOM cap width, in layout units.',
            cap_height='MOM cap height, in layout units.',
            sub_lch='Substrate channel length.',
            sub_w='Substrate width.',
            sub_type='Substrate type.  Either "ptap" or "ntap".',
            threshold='Substrate threshold.',
            cap_margin='margin between cap and boundary, in layout units.',
            port_width='port track width, in number of tracks.',
            port_idx='port track index.  Can be int, two-int tuple, or None.  Defaults to center.',
            show_pins='True to show pin labels.',
            cap_options='MOM cap layout options.',
            sub_tr_w='substrate track width in number of tracks.  None for default.',
        )

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            cap_margin=0,
            port_width=1,
            port_idx=None,
            show_pins=True,
            cap_options=None,
            sub_tr_w=None,
        )

    def draw_layout(self):
        """Draw the layout of a dynamic latch chain.
        """
        sub_lch = self.params['sub_lch']
        sub_w = self.params['sub_w']
        sub_type = self.params['sub_type']
        threshold = self.params['threshold']
        sub_tr_w = self.params['sub_tr_w']
        show_pins = self.params['show_pins']

        cap_params = self.params.copy()
        cap_params['show_pins'] = False
        cap_params['half_blk_x'] = False
        cap_params['half_blk_y'] = True
        master = self.new_template(params=cap_params, temp_cls=MOMCapCore)
        self._sch_params = master.sch_params.copy()
        top_layer = master.top_layer
        cap_box = master.bound_box

        if sub_w == 0:
            # do not draw substrate contact.
            inst = self.add_instance(master, inst_name='XCAP', loc=(0, 0), unit_mode=True)
            for port_name in inst.port_names_iter():
                self.reexport(inst.get_port(port_name), show=show_pins)
            self.array_box = inst.array_box
            self.set_size_from_bound_box(top_layer, cap_box)
        else:
            res = self.grid.resolution
            blkw, blkh = self.grid.get_block_size(top_layer, unit_mode=True)

            # draw contact and move array up
            sub_params = dict(
                top_layer=top_layer,
                lch=sub_lch,
                w=sub_w,
                sub_type=sub_type,
                threshold=threshold,
                port_width=sub_tr_w,
                well_width=cap_box.width,
                max_nxblk=cap_box.width_unit // blkw,
                show_pins=False,
                is_passive=False,
            )
            sub_master = self.new_template(params=sub_params, temp_cls=SubstrateContact)
            sub_box = sub_master.bound_box
            sub_x = (cap_box.width_unit - sub_box.width_unit) // 2

            # compute substrate X coordinate so substrate is on its own private horizontal pitch
            bot_inst = self.add_instance(sub_master, inst_name='XBSUB', loc=(sub_x, 0),
                                         unit_mode=True)
            res_inst = self.add_instance(master, inst_name='XCAP',
                                         loc=(0, sub_box.height_unit), unit_mode=True)
            top_yo = sub_box.height_unit * 2 + cap_box.height_unit
            top_inst = self.add_instance(sub_master, inst_name='XTSUB', loc=(sub_x, top_yo),
                                         orient='MX', unit_mode=True)

            # connect implant layers of resistor array and substrate contact together
            for lay in self.grid.tech_info.get_well_layers(sub_type):
                self.add_rect(lay, self.get_rect_bbox(lay))

            # export supplies and recompute array_box/size
            sub_port_name = 'VDD' if sub_type == 'ntap' else 'VSS'
            self.reexport(bot_inst.get_port(sub_port_name), label=sub_port_name + ':',
                          show=show_pins)
            self.reexport(top_inst.get_port(sub_port_name), label=sub_port_name + ':',
                          show=show_pins)
            arr_box = BBox(0, bot_inst.array_box.bottom_unit, res_inst.bound_box.right_unit,
                           top_inst.array_box.top_unit, res, unit_mode=True)
            bnd_box = arr_box.extend(y=0, unit_mode=True).extend(y=top_yo, unit_mode=True)
            self.array_box = arr_box
            self.set_size_from_bound_box(top_layer, bnd_box)
            self.add_cell_boundary(bnd_box)

            for port_name in res_inst.port_names_iter():
                self.reexport(res_inst.get_port(port_name), show=show_pins)

            self._sch_params['sub_name'] = sub_port_name
