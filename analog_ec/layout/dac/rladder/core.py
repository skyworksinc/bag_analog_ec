# -*- coding: utf-8 -*-

"""This module defines the resistor ladder DAC template.
"""

from typing import Dict, Set, Any, Union

from bag.layout.template import TemplateDB, TemplateBase
from bag.layout.util import BBox

from analog_ec.layout.passives.resistor.ladder import ResLadderTop


class ResLadderDAC(TemplateBase):
    """A voltage DAC made of resistor string ladder.

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
    **kwargs :
        dictionary of optional parameters.  See documentation of
        :class:`bag.layout.template.TemplateBase` for details.
    """

    def __init__(self, temp_db, lib_name, params, used_names, **kwargs):
        # type: (TemplateDB, str, Dict[str, Any], Set[str], **kwargs) -> None
        TemplateBase.__init__(self, temp_db, lib_name, params, used_names, **kwargs)

    @classmethod
    def get_params_info(cls):
        # type: () -> Dict[str, str]
        return dict(
            nin0='number of select bits for mux level 0.',
            nin1='number of select bits for mux level 1.',
            res_params='resistor ladder parameters.',
            mux_params='passgate mux parameters.',
            nout='number of outputs.',
            show_pins='True to show pins.',
        )

    @classmethod
    def get_default_param_values(cls):
        # type: () -> Dict[str, Any]
        return dict(
            nout=1,
            show_pins=True,
        )

    def draw_layout(self):
        # type: () -> None
        nin0 = self.params['nin0']
        nin1 = self.params['nin1']
        res_params = self.params['res_params']
        mux_params = self.params['mux_params']
        nout = self.params['nout']
        show_pins = self.params['show_pins']

        if nout <= 0:
            raise ValueError('nout must be positive.')

        res = self.grid.resolution
        num_mux_left = nout // 2
        num_mux_right = nout - num_mux_left
        num_col = 2 ** nin0
        num_row = 2 ** nin1
        nbits_tot = nin0 + nin1

        # make masters
        mux_params = dict(col_nbits=col_nbits, row_nbits=row_nbits, config_file=config_file)
        if num_mux_left > 0:
            mux_params['num_mux'] = num_mux_left
            lmux_master = self.new_template(params=mux_params, temp_cls=RLadderMuxArray)
        else:
            lmux_master = None

        mux_params['num_mux'] = num_mux_right
        rmux_master = self.new_template(params=mux_params, temp_cls=RLadderMuxArray)

        res_params = dict(l=l, w=w, sub_lch=sub_lch, sub_w=sub_w, sub_type=sub_type, threshold=threshold,
                          nx=num_col, ny=num_row, ndum=ndum, res_type=res_type)
        res_master = self.new_template(params=res_params, temp_cls=ResLadderTop)

        # figure out Y coordinates
        mux_warr = rmux_master.get_port('in<1>').get_pins()[0]
        pin_layer = mux_warr.layer_id
        tr_pitch = self.grid.get_track_pitch(pin_layer, unit_mode=True)
        mux_tr = mux_warr.track_id.base_index
        res_tr = res_master.get_port('out<1>').get_pins()[0].track_id.base_index
        res_yo = int(round(max(mux_tr - res_tr, 0))) * tr_pitch
        mux_yo = int(round(max(res_tr - mux_tr, 0))) * tr_pitch

        # place left mux
        sup_table = {'VDD': [], 'VSS': []}
        if lmux_master is not None:
            blk_w, blk_h = self.grid.get_size_dimension(lmux_master.size, unit_mode=True)
            lmux_inst = self.add_instance(lmux_master, loc=(blk_w, mux_yo), orient='MY', unit_mode=True)

            # gather supply and re-export inputs
            for port_name, port_list in sup_table.items():
                port_list.extend(lmux_inst.get_all_port_pins(port_name))
            for mux_idx in range(num_mux_left):
                self.reexport(lmux_inst.get_port('out<%d>' % mux_idx), show=True)
                for bit_idx in range(nbits_tot):
                    self.reexport(lmux_inst.get_port('code<%d>' % (bit_idx + mux_idx * nbits_tot)), show=True)

            vref_left = int(round(lmux_inst.get_port('in<1>').get_pins()[0].lower / res))
            xo = blk_w
            self.array_box = lmux_inst.array_box
        else:
            xo = 0
            vref_left = -1
            self.array_box = BBox.get_invalid_bbox()

        # place resistor ladder
        res_inst = self.add_instance(res_master, loc=(xo, res_yo), unit_mode=True)
        for port_name, port_list in sup_table.items():
            port_list.extend(res_inst.get_all_port_pins(port_name))
        if vref_left < 0:
            vref_left = int(round(res_inst.get_port('out<1>').get_pins()[0].lower / res))

        res_w, res_h = self.grid.get_size_dimension(res_master.size, unit_mode=True)
        xo += res_w
        # place right mux
        rmux_inst = self.add_instance(rmux_master, loc=(xo, mux_yo), unit_mode=True)
        rmux_w, rmux_h = self.grid.get_size_dimension(rmux_master.size, unit_mode=True)
        xo += rmux_w
        out_off = num_mux_left
        in_off = num_mux_left * nbits_tot
        for port_name, port_list in sup_table.items():
            port_list.extend(rmux_inst.get_all_port_pins(port_name))
        for mux_idx in range(num_mux_right):
            old_name = 'out<%d>' % mux_idx
            new_name = 'out' if num_out == 1 else 'out<%d>' % (mux_idx + out_off)
            self.reexport(rmux_inst.get_port(old_name), net_name=new_name, show=True)
            for bit_idx in range(nbits_tot):
                old_name = 'code<%d>' % (bit_idx + mux_idx * nbits_tot)
                new_name = 'code<%d>' % (bit_idx + mux_idx * nbits_tot + in_off)
                self.reexport(rmux_inst.get_port(old_name), net_name=new_name, show=True)
        vref_right = int(round(rmux_inst.get_port('in<1>').get_pins()[0].upper / res))

        for vref_idx in range(2 ** nbits_tot):
            vref_warr = rmux_inst.get_port('in<%d>' % vref_idx).get_pins()[0]
            vref_tr = vref_warr.track_id.base_index
            vref_layer = vref_warr.track_id.layer_id
            self.add_wires(vref_layer, vref_tr, vref_left, vref_right, unit_mode=True)

        # set size
        yo = max(mux_yo + rmux_h, res_yo + res_h)
        top_layer = sup_table['VDD'][0].layer_id + 1
        self.size = self.grid.get_size_tuple(top_layer, xo, yo, round_up=True, unit_mode=True)
        self.array_box = self.bound_box

        # do power fill
        sup_width = 2
        vdd_list, vss_list = self.do_power_fill(top_layer, sup_table['VDD'], sup_table['VSS'],
                                                sup_width=sup_width, fill_margin=0.5, edge_margin=0.2)
        self.add_pin('VDD', vdd_list)
        self.add_pin('VSS', vss_list)
