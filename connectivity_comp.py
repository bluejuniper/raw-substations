#!/usr/bin/env python

import argparse, json

power_equivelence_tolerence = 1e-2
voltage_equivelence_tolerence = 1e-1

def main(args):
    raw_case = parse_raw(args.raw_file)

    print('raw , %d, %d, %d' % (len(raw_case['buses']), len(raw_case['branches']), len(raw_case['transformers'])))

    for k,v in raw_case.items():
        print('{} - {}'.format(k, len(v)))
    print('')

    bus_lookup = { int(bus[0]):bus for bus in raw_case['buses'] }

    bus_sub_lookup = {}
    for bus in raw_case['buses']:
        bus_id = int(bus[0])
        #print(bus_id)
        bus_sub_lookup[bus_id] = set([bus_id])

    for trans in raw_case['transformers']:
        pr_bus = int(trans[0])
        sn_bus = int(trans[1])
        tr_bus = int(trans[2])

        if tr_bus == 0:
            bus_id_set = bus_sub_lookup[pr_bus] | bus_sub_lookup[sn_bus]
        else:
            bus_id_set = bus_sub_lookup[pr_bus] | bus_sub_lookup[sn_bus] | bus_sub_lookup[tr_bus]

        for bus_id in bus_id_set:
            bus_sub_lookup[bus_id] = bus_id_set

        #print(pr_bus, sn_bus, tr_bus)

    substation_buses = []
    for k,v in bus_sub_lookup.items():
        if not v in substation_buses:
            substation_buses.append(v)

    #for v in substation_buses:
    #    print(v)
    bus_data_lookup = {}
    for bus in raw_case['buses']:
        bus_id = int(bus[0])
        bus_data = {
            'id':bus_id,
            'name':'{} - {}'.format(bus_id, bus[1]),
            'loads':[],
            'generators':[],
            'fixed_shunts':[],
            'switched_shunts':[],
            'facts':[]
        }
        bus_data_lookup[bus_id] = bus_data

    for i, load in enumerate(raw_case['loads']):
        load_id = i+1
        bus_id = int(load[0])
        load_data = {
            'id':load_id,
            'name':'{} - {} {}'.format(load_id, bus_id, load[1]),
        }
        bus_data_lookup[bus_id]['loads'].append(load_data)

    for i, generator in enumerate(raw_case['gens']):
        gen_id = i+1
        bus_id = int(generator[0])
        generator_data = {
            'id':gen_id,
            'name':'{} - {} {}'.format(gen_id, bus_id, generator[1]),
        }
        bus_data_lookup[bus_id]['generators'].append(generator_data)

    for i, fixed_shunt in enumerate(raw_case['f_shunts']):
        f_shunt_id = i+1
        bus_id = int(fixed_shunt[0])
        fixed_shunt_data = {
            'id':f_shunt_id,
            'name':'{} - {} {}'.format(f_shunt_id, bus_id, fixed_shunt[1]),
        }
        bus_data_lookup[bus_id]['fixed_shunts'].append(fixed_shunt_data)

    for i, switched_shunt in enumerate(raw_case['s_shunts']):
        s_shunt_id = i+1
        bus_id = int(switched_shunt[0])
        switched_shunt_data = {
            'id':s_shunt_id,
            'name':'{} - {}'.format(s_shunt_id, bus_id),
        }
        bus_data_lookup[bus_id]['switched_shunts'].append(switched_shunt_data)

    for i, facts in enumerate(raw_case['facts']):
        facts_id = i+1
        from_bus = int(facts[1])
        to_bus = int(facts[2])
        if to_bus == 0:
            facts_data = {
                'id':facts_id,
                'name':'{} - {} {}'.format(facts_id, from_bus, facts[0]),
            }
            bus_data_lookup[from_bus]['facts'].append(facts_data)


    # for k,v in bus_data_lookup.items():
    #     print('{} - {}'.format(k, v))
    # print('')


    bus_sub_lookup = {}
    substations = []
    for i, sub_buses in enumerate(substation_buses):
        sub_id = i+1
        substation = {
            'id': sub_id,
            'name': 'subsation {}'.format(sub_id),
            'transformer_groups': [],
            'branch_groups': []
        }

        buses = []
        for bus_id in sub_buses:
            buses.append(bus_data_lookup[bus_id])
            bus_sub_lookup[bus_id] = substation
        substation['buses'] = buses

        substations.append(substation)

        # if len(sub_data['bus_ids']) > 1:
        #     print(sub_name)
        #     print('  ' + str(sub_data['bus_ids']))
        #     print('  ' + str(sub_data['bus_names']))
        #     print('')


    transformer_lookup = {}
    for i, trans in enumerate(raw_case['transformers']):
        trans_id = i+1
        pr_bus = int(trans[0])
        sn_bus = int(trans[1])
        tr_bus = int(trans[2])

        if tr_bus == 0:
            key = (pr_bus, sn_bus)
        else:
            key = (pr_bus, sn_bus, tr_bus)
        if not key in transformer_lookup:
            transformer_lookup[key] = []
        transformer_lookup[key].append((trans_id, trans))


    for k, v in transformer_lookup.items():
        bus_sub = bus_sub_lookup[k[0]]
        assert(all([ bus_sub == bus_sub_lookup[bus_id] for bus_id in k]))
        transformer_list = []
        for trans_id, trans in v:
            trans_data = {'id':trans_id}
            if len(k) == 2:
                trans_data['name'] = '{} - {} {} {}'.format(trans_id, k[0], k[1], trans[3])
            else:
                trans_data['name'] = '{} - {} {} {} {}'.format(trans_id, k[0], k[1], k[2], trans[3])
            transformer_list.append(trans_data)
        bus_sub['transformer_groups'].append(transformer_list)


    branch_bp_lookup = {}
    for i, branch in enumerate(raw_case['branches']):
        branch_id = i+1
        from_bus = int(branch[0])
        to_bus = int(branch[1])

        #print(from_bus, to_bus)
        #assert(bus_sub_lookup[from_bus] != bus_sub_lookup[to_bus])

        key = (from_bus, to_bus)
        if not key in branch_bp_lookup:
            branch_bp_lookup[key] = []
        branch_bp_lookup[key].append((branch_id, branch))

    facts_bp_lookup = {}
    for i, facts in enumerate(raw_case['facts']):
        facts_id = i+1
        from_bus = int(facts[1])
        to_bus = int(facts[2])

        if to_bus != 0:
            assert(bus_sub_lookup[from_bus] != bus_sub_lookup[to_bus])

            key = (from_bus, to_bus)
            if not key in facts_bp_lookup:
                facts_bp_lookup[key] = []
            facts_bp_lookup[key].append((facts_id, facts))

    tt_dc_bp_lookup = {}
    for i, tt_dc in enumerate(raw_case['tt_dc']):
        tt_dc_id = i+1
        from_bus = int(tt_dc[1][0])
        to_bus = int(tt_dc[2][0])

        assert(bus_sub_lookup[from_bus] != bus_sub_lookup[to_bus])

        key = (from_bus, to_bus)
        if not key in tt_dc_bp_lookup:
            tt_dc_bp_lookup[key] = []
        tt_dc_bp_lookup[key].append((tt_dc_id, tt_dc))

    vsc_dc_bp_lookup = {}
    for i, vsc_dc in enumerate(raw_case['vsc_dc']):
        vsc_dc_id = i+1
        from_bus = int(vsc_dc[1][0])
        to_bus = int(vsc_dc[2][0])

        assert(bus_sub_lookup[from_bus] != bus_sub_lookup[to_bus])

        key = (from_bus, to_bus)
        if not key in vsc_dc_bp_lookup:
            vsc_dc_bp_lookup[key] = []
        vsc_dc_bp_lookup[key].append((vsc_dc_id, vsc_dc))


    corridor_branch_lookup = {}
    for (from_bus, to_bus), v in branch_bp_lookup.items():
        branch_list = []
        for branch_id, branch in v:
            branch_data = {
                'id':branch_id,
                'name': '{} - {} {} {}'.format(branch_id, branch[0], branch[1], branch[2])
            }
            branch_list.append(branch_data)

        #print('{} {} {}'.format(from_bus, to_bus, v))
        sub_from = bus_sub_lookup[from_bus]
        sub_to = bus_sub_lookup[to_bus]
        if sub_from == sub_to:
            sub_from['branch_groups'].append(branch_list)
        else:
            if sub_from['id'] > sub_to['id']:
                sub_from = bus_sub_lookup[to_bus]
                sub_to = bus_sub_lookup[from_bus]
            corridor_key = (sub_from['id'], sub_to['id'])
            if not corridor_key in corridor_branch_lookup:
                corridor_branch_lookup[corridor_key] = []
            corridor_branch_lookup[corridor_key].append(branch_list)


    corridor_facts_lookup = {}
    for (from_bus, to_bus), v in facts_bp_lookup.items():
        facts_list = []
        for facts_id, facts in v:
            facts_data = {
                'id':facts_id,
                'name': '{} - {} {} {}'.format(facts_id, branch[1], branch[2], branch[0])
            }
            facts_list.append(branch_data)

        #print('{} {} {}'.format(from_bus, to_bus, v))
        sub_from = bus_sub_lookup[from_bus]
        sub_to = bus_sub_lookup[to_bus]

        if sub_from['id'] > sub_to['id']:
            sub_from = bus_sub_lookup[to_bus]
            sub_to = bus_sub_lookup[from_bus]
        corridor_key = (sub_from['id'], sub_to['id'])
        if not corridor_key in corridor_facts_lookup:
            corridor_facts_lookup[corridor_key] = []
        corridor_facts_lookup[corridor_key].append(facts_list)


    corridor_tt_dc_lookup = {}
    for (from_bus, to_bus), v in tt_dc_bp_lookup.items():
        tt_dc_list = []
        for tt_dc_id, tt_dc in v:
            tt_dc_data = {
                'id':tt_dc_id,
                'name': '{} - {} {}'.format(tt_dc_id, from_bus, to_bus)
            }
            tt_dc_list.append(tt_dc_data)

        #print('{} {} {}'.format(from_bus, to_bus, v))
        sub_from = bus_sub_lookup[from_bus]
        sub_to = bus_sub_lookup[to_bus]

        if sub_from['id'] > sub_to['id']:
            sub_from = bus_sub_lookup[to_bus]
            sub_to = bus_sub_lookup[from_bus]
        corridor_key = (sub_from['id'], sub_to['id'])
        if not corridor_key in corridor_tt_dc_lookup:
            corridor_tt_dc_lookup[corridor_key] = []
        corridor_tt_dc_lookup[corridor_key].append(tt_dc_list)


    corridor_vsc_dc_lookup = {}
    for (from_bus, to_bus), v in vsc_dc_bp_lookup.items():
        vsc_dc_list = []
        for vsc_dc_id, tt_vsc in v:
            vsc_dc_data = {
                'id':tt_dc_id,
                'name': '{} - {} {}'.format(vsc_dc_id, from_bus, to_bus)
            }
            vsc_dc_list.append(vsc_dc_data)

        #print('{} {} {}'.format(from_bus, to_bus, v))
        sub_from = bus_sub_lookup[from_bus]
        sub_to = bus_sub_lookup[to_bus]

        if sub_from['id'] > sub_to['id']:
            sub_from = bus_sub_lookup[to_bus]
            sub_to = bus_sub_lookup[from_bus]
        corridor_key = (sub_from['id'], sub_to['id'])
        if not corridor_key in corridor_vsc_dc_lookup:
            corridor_vsc_dc_lookup[corridor_key] = []
        corridor_vsc_dc_lookup[corridor_key].append(vsc_dc_list)


    corridors = []
    corridor_keys = set().union(
        corridor_branch_lookup.keys(),
        corridor_facts_lookup.keys(),
        corridor_tt_dc_lookup.keys(),
        corridor_vsc_dc_lookup.keys()
    )

    for i, corridor_key in enumerate(corridor_keys):
        corr_id = i+1
        corridor = {
            'id': corr_id,
            'name': 'corridor {}'.format(corr_id),
            'from_substation': corridor_key[0],
            'to_substation': corridor_key[1],
            'branch_groups': [],
            'facts_groups':[],
            'tt_dc_groups':[],
            'vsc_dc_groups':[],
        }

        if corridor_key in corridor_branch_lookup:
            corridor['branch_groups'] = corridor_branch_lookup[corridor_key]

        if corridor_key in corridor_facts_lookup:
            corridor['facts_groups'] = corridor_facts_lookup[corridor_key]

        if corridor_key in corridor_tt_dc_lookup:
            corridor['tt_dc_groups'] = corridor_tt_dc_lookup[corridor_key]

        if corridor_key in corridor_vsc_dc_lookup:
            corridor['vsc_dc_groups'] = corridor_vsc_dc_lookup[corridor_key]

        corridors.append(corridor)


    connectivity = {
        'case': args.raw_file,
        'substations': substations,
        'corridors': corridors
    }
    print('Nodes: %d' % len(raw_case['buses']))
    print('Edges: %d' % (len(raw_case['branches'])+len(raw_case['transformers'])+len(raw_case['tt_dc'])+len(raw_case['vsc_dc'])))
    print('')
    print('Substations: %d' % len(substations))
    print('Corridors: %d' % len(corridors))

    with open('connectivity_test_1.json', 'w') as outfile:
        json.dump(connectivity, outfile, sort_keys=True, indent=2, separators=(',', ': '))


def parse_raw(raw_file_location):
    with open(raw_file_location, 'r') as raw_file: 
        raw_lines = raw_file.readlines()

    raw_case = {}

    bus_lines = []
    raw_case['buses'] = bus_lines

    load_lines = []
    raw_case['loads'] = load_lines

    fixed_shunt_lines = []
    raw_case['f_shunts'] = fixed_shunt_lines

    gen_lines = []
    raw_case['gens'] = gen_lines

    switched_shunt_lines = []
    raw_case['s_shunts'] = switched_shunt_lines

    branch_lines = []
    raw_case['branches'] = branch_lines

    transformer_lines = []
    raw_case['transformers'] = transformer_lines

    two_terminal_dc_lines = []
    raw_case['tt_dc'] = two_terminal_dc_lines

    vsc_dc_lines = []
    raw_case['vsc_dc'] = vsc_dc_lines

    mt_dc_lines = []
    raw_case['mt_dc'] = mt_dc_lines

    facts_lines = []
    raw_case['facts'] = facts_lines


    reading_buses = True
    reading_loads = False
    reading_fixed_shunts = False
    reading_gens = False
    reading_branches = False
    reading_transformers = False
    reading_switched_shunts = False
    reading_tt_dc = False
    reading_vsc_dc = False
    reading_mt_dc = False
    reading_facts = False


    line_index = 3
    while line_index < len(raw_lines):
        line = raw_lines[line_index]

        if 'END OF BUS DATA' in line:
            reading_buses = False

        if 'END OF LOAD DATA' in line:
            reading_loads = False

        if 'END OF FIXED SHUNT DATA' in line:
            reading_fixed_shunts = False

        if 'END OF GENERATOR DATA' in line:
            reading_gens = False

        if 'END OF BRANCH DATA' in line:
            reading_branches = False

        if 'END OF TRANSFORMER DATA' in line:
            reading_transformers = False

        if 'END OF TWO-TERMINAL DC DATA' in line:
            reading_tt_dc = False

        if 'END OF VSC DC LINE DATA' in line:
            reading_vsc_dc = False

        if 'END OF MULTI-TERMINAL DC DATA' in line:
            reading_mt_dc = False

        if 'END OF FACTS DEVICE DATA' in line:
            reading_facts = False

        if 'END OF SWITCHED SHUNT DATA' in line:
            reading_switched_shunts = False


        if 'BEGIN LOAD DATA' in line:
            reading_loads = True
            line_index += 1
            #line = raw_lines[line_index]
            continue

        if 'BEGIN FIXED SHUNT DATA' in line:
            reading_fixed_shunts = True
            line_index += 1
            #line = raw_lines[line_index]
            continue

        if 'BEGIN GENERATOR DATA' in line:
            reading_gens = True
            line_index += 1
            #line = raw_lines[line_index]
            continue

        if 'BEGIN BRANCH DATA' in line:
            reading_branches = True
            line_index += 1
            #line = raw_lines[line_index]
            continue

        if 'BEGIN TRANSFORMER DATA' in line:
            reading_transformers = True
            line_index += 1
            #line = raw_lines[line_index]
            continue

        if 'BEGIN TWO-TERMINAL DC DATA' in line:
            reading_tt_dc = True
            line_index += 1
            #line = raw_lines[line_index]
            continue

        if 'BEGIN VSC DC LINE DATA' in line:
            reading_vsc_dc = True
            line_index += 1
            #line = raw_lines[line_index]
            continue

        if 'BEGIN MULTI-TERMINAL DC DATA' in line:
            reading_mt_dc = True
            line_index += 1
            #line = raw_lines[line_index]
            continue

        if 'BEGIN FACTS DEVICE DATA' in line:
            reading_facts = True
            line_index += 1
            #line = raw_lines[line_index]
            continue

        if 'BEGIN SWITCHED SHUNT DATA' in line:
            reading_switched_shunts = True
            line_index += 1
            #line = raw_lines[line_index]
            continue


        if reading_buses:
            bus_lines.append(line.strip().split(','))

        if reading_gens:
            gen_lines.append(line.strip().split(','))

        if reading_loads:
            load_lines.append(line.strip().split(','))

        if reading_fixed_shunts:
            fixed_shunt_lines.append(line.strip().split(','))

        if reading_branches:
            branch_lines.append(line.strip().split(','))

        if reading_transformers:
            tr_parts = line.strip().split(',')
            transformer_lines.append(tr_parts)
            two_winding = int(tr_parts[2]) == 0
            if two_winding:
                line_index += 3
            else:
                line_index += 4

        if reading_tt_dc:
            two_terminal_dc_lines.append([
                raw_lines[line_index+0].strip().split(','),
                raw_lines[line_index+1].strip().split(','),
                raw_lines[line_index+2].strip().split(','),
            ])
            line_index += 2

        if reading_vsc_dc:
            vsc_dc_lines.append([
                raw_lines[line_index+0].strip().split(','),
                raw_lines[line_index+1].strip().split(','),
                raw_lines[line_index+2].strip().split(','),
            ])
            line_index += 2

        if reading_mt_dc:
            assert(False) # this is not supported yet
            pass # mt_dc_lines.append(line.strip().split(','))

        if reading_facts:
            facts_lines.append(line.strip().split(','))

        if reading_switched_shunts:
            switched_shunt_lines.append(line.strip().split(','))

        line_index += 1

    return raw_case


def build_cli_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('raw_file', help='the psse file to operate on (.raw)')

    return parser

if __name__ == '__main__':
    parser = build_cli_parser()
    main(parser.parse_args())