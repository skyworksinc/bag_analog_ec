# -*- coding: utf-8 -*-

import yaml

from bag.core import BagProject

from analog_ec.layout.dac.rladder.top import RDACArray


if __name__ == '__main__':
    with open('specs_test/analog_ec/rdac/array.yaml', 'r') as f:
        block_specs = yaml.load(f)

    local_dict = locals()
    if 'bprj' not in local_dict:
        print('creating BAG project')
        bprj = BagProject()

    else:
        print('loading BAG project')
        bprj = local_dict['bprj']

    # bprj.generate_cell(block_specs, RDACArray, debug=True, save_cache=True)
    # bprj.generate_cell(block_specs, RDACArray, debug=True, use_cache=True)
    bprj.generate_cell(block_specs, RDACArray, debug=True)
    # bprj.generate_cell(block_specs, RDACArray, gen_lay=False, gen_sch=True)
