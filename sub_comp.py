#!/usr/bin/env python3

import argparse, json

power_equivelence_tolerence = 1e-2
voltage_equivelence_tolerence = 1e-1

def main(args):
    raw_case = parse_raw(args.raw_file)

    print('raw , %d, %d, %d' % (len(raw_case['buses']), len(raw_case['branches']), len(raw_case['transformers'])))

    bus_lookup = { int(bus[0]):bus for bus in raw_case['buses'] }

    bus_sub_lookup = {}
    for bus in raw_case['buses']:
        bus_id = int(bus[0])
        #print(bus_id)
        bus_sub_lookup[bus_id] = set([bus_id])

    if False:
        ed_dist = {}
        for i, bus_1 in enumerate(raw_case['buses']):
            bus_1_name = bus_1[1].strip('\'').strip()
            for j in range(i+1, len(raw_case['buses'])):
                bus_2 = raw_case['buses'][j]
                bus_2_name = bus_2[1].strip('\'').strip()
                ed = edit_distance(bus_1_name, bus_2_name)
                #print(ed)
                if not ed in ed_dist.keys():
                    ed_dist[ed] = 0
                ed_dist[ed] = ed_dist[ed] + 1

                if ed <= 2:
                    bus_1_id = int(bus_1[0])
                    bus_2_id = int(bus_2[0])
                    bus_id_set = bus_sub_lookup[bus_1_id] | bus_sub_lookup[bus_2_id]

                    for bus_id in bus_id_set:
                        bus_sub_lookup[bus_id] = bus_id_set

        for ed in sorted(ed_dist.keys()):
            print('%d - %d' % (ed, ed_dist[ed]))


    if False:
        for i, bus_1 in enumerate(raw_case['buses']):
            bus_1_name = bus_1[1].strip('\'').strip()
            for j in range(i+1, len(raw_case['buses'])):
                bus_2 = raw_case['buses'][j]
                bus_2_name = bus_2[1].strip('\'').strip()
                size_percent = prefix_size(bus_1_name, bus_2_name)

                #print(size_percent)

                # TODO, don't merge buses if they have a line between them
                if size_percent >= 0.75:
                    bus_1_id = int(bus_1[0])
                    bus_2_id = int(bus_2[0])

                    min_bus_delta = max(bus_lookup.keys()*10)
                    for bus_a in bus_sub_lookup[bus_1_id]:
                        for bus_b in bus_sub_lookup[bus_2_id]:
                            min_bus_delta = min(min_bus_delta, abs(bus_a - bus_b))
                    if min_bus_delta <= 100:
                        print('merging: {} {} - {}'.format(bus_1_name, bus_2_name, min_bus_delta))
                        
                        bus_id_set = bus_sub_lookup[bus_1_id] | bus_sub_lookup[bus_2_id]

                        for bus_id in bus_id_set:
                            bus_sub_lookup[bus_id] = bus_id_set


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

    over_one = 0
    substations = {}
    for i, sub in enumerate(substation_buses):
        sub_name = 'sub_%d' % i
        sub_data = {}
        sub_data['bus_ids'] = list(sub)
        sub_data['bus_names'] = [ bus_lookup[bid][1].strip('\'').strip() for bid in sub_data['bus_ids']]

        substations[sub_name] = sub_data

        if len(sub_data['bus_ids']) > 1:
            over_one += 1
            print(sub_name)
            print('  ' + str(sub_data['bus_ids']))
            print('  ' + str(sub_data['bus_names']))
            print('')

    print('Nodes: %d' % len(raw_case['buses']))
    print('Substations: %d' % len(substations))
    print('Over 1 Node Substations: %d' % over_one)

    with open('substation_test_1.json', 'w') as outfile:
        json.dump(substations, outfile, sort_keys=True, indent=2, separators=(',', ': '))


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


    reading_buses = True
    reading_loads = False
    reading_fixed_shunts = False
    reading_gens = False
    reading_branches = False
    reading_transformers = False
    reading_switched_shunts = False

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

        if 'END OF SWITCHED SHUNT DATA' in line:
            reading_switched_shunts = False


        if 'BEGIN LOAD DATA' in line:
            reading_loads = True
            line_index += 1
            line = raw_lines[line_index]

        if 'BEGIN FIXED SHUNT DATA' in line:
            reading_fixed_shunts = True
            line_index += 1
            line = raw_lines[line_index]

        if 'BEGIN GENERATOR DATA' in line:
            reading_gens = True
            line_index += 1
            line = raw_lines[line_index]

        if 'BEGIN BRANCH DATA' in line:
            reading_branches = True
            line_index += 1
            line = raw_lines[line_index]

        if 'BEGIN TRANSFORMER DATA' in line:
            reading_transformers = True
            line_index += 1
            line = raw_lines[line_index]

        if 'BEGIN SWITCHED SHUNT DATA' in line:
            reading_switched_shunts = True
            line_index += 1
            line = raw_lines[line_index]


        if reading_buses:
            bus_lines.append(line.strip().split(','))

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

        if reading_switched_shunts:
            switched_shunt_lines.append(line.strip().split(','))

        line_index += 1

    return raw_case


def edit_distance(s1, s2):
    m=len(s1)+1
    n=len(s2)+1

    tbl = {}
    for i in range(m): tbl[i,0]=i
    for j in range(n): tbl[0,j]=j
    for i in range(1, m):
        for j in range(1, n):
            cost = 0 if s1[i-1] == s2[j-1] else 1
            tbl[i,j] = min(tbl[i, j-1]+1, tbl[i-1, j]+1, tbl[i-1, j-1]+cost)

    return tbl[i,j]


def prefix_size(s1, s2):
    length = min(len(s1), len(s2))
    prefix_length = 0
    for i in range(length):
        if s1[i] == s2[i]:
            prefix_length = i+1
        else:
            break

    #print('{} {} {} {}'.format(s1, s2, length, prefix_length))
    return prefix_length/float(length)


def build_cli_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('raw_file', help='the psse file to operate on (.raw)')

    return parser

if __name__ == '__main__':
    parser = build_cli_parser()
    main(parser.parse_args())
