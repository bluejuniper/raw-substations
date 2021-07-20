#!/usr/bin/env python3

import argparse, json, csv, itertools, math, shlex, grg_pssedata
from grg_pssedata.io import parse_psse_case_file

from collections import namedtuple
Location = namedtuple('Location', ['id', 'bus_name', 'zone', 'location_id', 'max_kv', 'longitude', 'latitude', 'raw_bus_name'])

LocationCanditate = namedtuple('LocationCanditate', ['bus_id', 'bus_name', 'match_name', 'score', 'location'])

def typed_location(item_id, bus_name, zone, location_id, max_kv, longitude, latitude, raw_bus_name):
    item_id = int(item_id)
    bus_name = bus_name.strip()
    zone = int(zone)
    location_id = int(location_id)
    max_kv = float(max_kv)
    longitude = float(longitude)
    latitude = float(latitude)
    raw_bus_name = raw_bus_name.strip()

    return Location(item_id, bus_name, zone, location_id, max_kv, longitude, latitude, raw_bus_name)


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


def contract_transformers(metabus_lookup, buses, transformers):
    contraction_count = 0

    for trans in transformers:
        pr_bus = int(trans.p1.i)
        sn_bus = int(trans.p1.j)
        tr_bus = int(trans.p1.k)

        if tr_bus == 0:
            bus_id_set = metabus_lookup[pr_bus] | metabus_lookup[sn_bus]
            contraction_count += 1
        else:
            bus_id_set = metabus_lookup[pr_bus] | metabus_lookup[sn_bus] | metabus_lookup[tr_bus]
            contraction_count += 2

        for bus_id in bus_id_set:
            metabus_lookup[bus_id] = bus_id_set

    metabuses_list = []
    for bus_set in metabus_lookup.values():
        if bus_set not in metabuses_list:
            metabuses_list.append(bus_set)

    print('transformer contraction joined {} buses'.format(contraction_count))

    metabus_lookup = {}
    for metabus_id, bus_set in enumerate(metabuses_list):
        for bus in bus_set:
            metabus_lookup[bus] = metabus_id

    return metabus_lookup


def contract_voltage_level(metabus_lookup, bus_lookup, branches, kv_threshold):
    metabuses_ids = {}
    for bus, set_id in metabus_lookup.items():
        if set_id not in metabuses_ids:
            metabuses_ids[set_id] = set()
        metabuses_ids[set_id].add(bus)

    metabus_max_kv = {}
    for i,v in metabuses_ids.items():
        metabus_max_kv[i] = max(float(bus_lookup[bus_id].basekv) for bus_id in v)

    bus_to_metabus = {}
    for metabus_id, metabus in metabuses_ids.items():
        for bus_id in metabus:
            bus_to_metabus[bus_id] = metabus_id

    #print(bus_to_metabus)
    #incident = {}
    neighbors = {}
    for k in metabuses_ids:
        neighbors[k] = set()
    for branch in branches:
        from_bus = int(branch.i)
        to_bus = int(branch.j)

        from_metabus = bus_to_metabus[from_bus]
        to_metabus = bus_to_metabus[to_bus]

        neighbors[from_metabus].add(to_metabus)
        neighbors[to_metabus].add(from_metabus)

    high_voltage_metabus_ids = { idx for idx in metabuses_ids if metabus_max_kv[idx] >= kv_threshold }
    #print(high_voltage_metabus_ids)

    metabus_unions = {i:set([i]) for i in high_voltage_metabus_ids}
    merged = set()

    contraction_count = 0
    contracted = True
    while contracted:
        contracted = False
        for metabus_id in high_voltage_metabus_ids:
            for metabus_neighbor_id in [i for i in neighbors[metabus_id]]:
                if metabus_max_kv[metabus_neighbor_id] < kv_threshold and metabus_neighbor_id not in merged:
                    metabus_unions[metabus_id].add(metabus_neighbor_id)
                    metabus_unions[metabus_neighbor_id] = metabus_unions[metabus_id]
                    merged.add(metabus_neighbor_id)

                    for metabus_neighbor_neighbor_id in neighbors[metabus_neighbor_id]:
                        neighbors[metabus_id].add(metabus_neighbor_neighbor_id)

                    contraction_count += 1
                    contracted = True

    metabuses_union_list = []
    for metabus_set in metabus_unions.values():
        if metabus_set not in metabuses_union_list:
            metabuses_union_list.append(metabus_set)

    # for value in metabuses_union_list:
    #     print(value)

    print('high voltage metabuses {}, number of metabus sets found {}'.format(len(high_voltage_metabus_ids), len(metabuses_union_list)))
    print('voltage level contraction joined {} metabuses'.format(contraction_count))

    metabus_lookup_two = {}
    for metabus_id, metabus_set in enumerate(metabuses_union_list):
        for metabus in metabus_set:
            for bus in metabuses_ids[metabus]:
                metabus_lookup_two[bus] = metabus_id

    #print(metabus_lookup_two)
    return metabus_lookup_two


def load_gic_file(file_name):
    with open(file_name, 'r') as gic_file:
        gic_lines = gic_file.readlines()

    line_idx = 1
    line = gic_lines[line_idx]

    sub_data = {}
    while not line.strip().startswith('0'):
        line_parts = shlex.split(line)
        data = {
            'id': int(line_parts[0]),
            'name': line_parts[1].strip(),
            'tbd_1': line_parts[2],
            'lat': float(line_parts[3]),
            'lon': float(line_parts[4]),
            'tbd_2': line_parts[5],
        }
        sub_data[data['id']] = data

        line_idx += 1
        line = gic_lines[line_idx]

    line_idx += 1
    line = gic_lines[line_idx]

    bus_to_sub = {}

    sub_buses = {}
    while not line.strip().startswith('0'):
        line_parts = line.split()
        bus_id = int(line_parts[0])
        sub_id = int(line_parts[1])

        bus_to_sub[bus_id] = sub_id

        if not sub_id in sub_buses:
            sub_buses[sub_id] = set([bus_id])
        else:
            bus_id_set = sub_buses[sub_id] | set([bus_id])
            for bus_id in bus_id_set:
                sub_buses[bus_to_sub[bus_id]] = bus_id_set

        line_idx += 1
        line = gic_lines[line_idx]

    metabus_lookup = {}
    for sub, bus_set in sub_buses.items():
        for bus_id in bus_set:
            metabus_lookup[bus_id] = bus_set

    return metabus_lookup, bus_to_sub, sub_data


def load_lanl_geo_file(file_name):
    with open(file_name, 'r') as jsonfile:
        lanl_geo = json.load(jsonfile)

    bus_to_sub = {}
    sub_buses = {}
    sub_data = {}

    for sub_id, data in lanl_geo.items():
        sub_buses[sub_id] = set(data['buses'])
        for bus_id in data['buses']:
            bus_to_sub[bus_id] = sub_id

        data = {
            'id': sub_id,
            'name': data['name'],
            'lon': data['coordinates'][0],
            'lat': data['coordinates'][1]
        }
        sub_data[sub_id] = data

    metabus_lookup = {}
    for sub, bus_set in sub_buses.items():
        for bus_id in bus_set:
            metabus_lookup[bus_id] = bus_set

    return metabus_lookup, bus_to_sub, sub_data



def main(args):
    raw_case = parse_psse_case_file(args.raw_file)

    # print('raw , %d, %d, %d' % (len(raw_case.buses), len(raw_case.branches), len(raw_case.transformers)))

    # for k,v in raw_case.items():
    #     print('{} - {}'.format(k, len(v)))
    # print('')

    bus_lookup = { int(bus.i):bus for bus in raw_case.buses }
    load_lookup = { i+1:load for i, load in enumerate(raw_case.loads) }
    owner_lookup = { int(owner.i):owner for i, owner in enumerate(raw_case.owners) }
    fixed_shunt_lookup = { i+1:fs for i, fs in enumerate(raw_case.fixed_shunts) }
    switched_shunt_lookup = { i+1:ss for i, ss in enumerate(raw_case.switched_shunts) }
    generator_lookup = { i+1:g for i, g in enumerate(raw_case.generators) }

    transformer_lookup = { i+1:tr for i, tr in enumerate(raw_case.transformers) }
    branch_lookup = { i+1:branch for i, branch in enumerate(raw_case.branches) }
    facts_lookup = { i+1:facts for i, facts in enumerate(raw_case.facts) }
    tt_dc_lookup = { i+1:tt_dc for i, tt_dc in enumerate(raw_case.tt_dc_lines) }
    vsc_dc_lookup = { i+1:vsc_dc for i, vsc_dc in enumerate(raw_case.vsc_dc_lines) }

    metabus_lookup = {}
    for bus in raw_case.buses:
        bus_id = int(bus.i)
        #print(bus_id)
        metabus_lookup[bus_id] = set([bus_id])

    metabus_data = None
    bus_to_sub = None

    metabus_lookup = contract_transformers(metabus_lookup, raw_case.buses, raw_case.transformers)
    metabus_lookup = contract_voltage_level(metabus_lookup, bus_lookup, raw_case.branches, args.kv_threshold)

    substation_buses = {}
    for bus, set_id in metabus_lookup.items():
        if set_id not in substation_buses:
            substation_buses[set_id] = set()
        substation_buses[set_id].add(bus)


    bus_data_lookup = {}
    for bus in raw_case.buses:
        bus_id = int(bus.i)
        bus_data = {
            'id':bus_id,
            'type':'physical',
            'name':'{}'.format(bus.name),
            'loads':[],
            'generators':[],
            'fixed_shunts':[],
            'switched_shunts':[],
            'facts':[]
        }
        bus_data_lookup[bus_id] = bus_data

    for i, load in enumerate(raw_case.loads):
        load_id = i+1
        bus_id = int(load.i)
        load_data = {
            'id':load_id,
            'name':'{} {}'.format(load.i, load.id),
        }
        bus_data_lookup[bus_id]['loads'].append(load_data)

    for i, generator in enumerate(raw_case.generators):
        gen_id = i+1
        bus_id = int(generator.i)
        generator_data = {
            'id':gen_id,
            'name':'{} {}'.format(generator.i, generator.id),
        }
        bus_data_lookup[bus_id]['generators'].append(generator_data)

    for i, fixed_shunt in enumerate(raw_case.fixed_shunts):
        f_shunt_id = i+1
        bus_id = int(fixed_shunt.i)
        fixed_shunt_data = {
            'id':f_shunt_id,
            'name':'{} {}'.format(fixed_shunt.i, fixed_shunt.id),
        }
        bus_data_lookup[bus_id]['fixed_shunts'].append(fixed_shunt_data)

    for i, switched_shunt in enumerate(raw_case.switched_shunts):
        s_shunt_id = i+1
        bus_id = int(switched_shunt.i)
        switched_shunt_data = {
            'id':s_shunt_id,
            'name':'{}'.format(switched_shunt.i),
        }
        bus_data_lookup[bus_id]['switched_shunts'].append(switched_shunt_data)

    for i, facts in enumerate(raw_case.facts):
        facts_id = i+1
        from_bus = facts.i
        to_bus = facts.j
        if to_bus == 0:
            facts_data = {
                'id':facts_id,
                'name':'{} {}'.format(facts.i, facts.name),
            }
            bus_data_lookup[from_bus]['facts'].append(facts_data)


    # for k,v in bus_data_lookup.items():
    #     print('{} - {}'.format(k, v))
    # print('')


    bus_sub_lookup = {}
    substations = []
    for i, sub_buses in substation_buses.items():
        sub_id = i+1
        substation = {
            'id': sub_id,
            'type':'physical',
            'name': 'substation {}'.format(sub_id),
            'transformer_groups': [],
            'branch_groups': []
        }

        if metabus_data != None and bus_to_sub != None:
            sub_id = bus_to_sub[next(iter(sub_buses))]
            substation['latitude'] = metabus_data[sub_id]['lat']
            substation['longitude'] = metabus_data[sub_id]['lon']
            substation['name'] = metabus_data[sub_id]['name']

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

    substation_lookup = { sub['id'] : sub for sub in substations }

    if args.bus_geolocations != None:
        geolocation_lookup = {}

        if args.bus_geolocations.lower().endswith('.geojson'):
            with open(args.bus_geolocations, 'r') as jsonfile:
                geojson = json.load(jsonfile)
            #print(geojson)
            for feature in geojson['features']:
                bus_id = feature['properties'][args.bus_geolocations_index]
                geolocation_lookup[bus_id] = {
                    'longitude':feature['geometry']['coordinates'][0],
                    'latitude':feature['geometry']['coordinates'][1]
                }
        elif args.bus_geolocations.lower().endswith('csv'):
            with open(args.bus_geolocations, 'r') as csvfile:
                csvfile.readline() # discard header row

                for row in csvfile:
                    elems = row.split(',')
                    bus_id = int(elems[0])
                    x = float(elems[1])
                    y = float(elems[2])
                    geolocation_lookup[bus_id] = {'longitude': x, 'latitude': y}
        else:
            raise ValueError("Invalid file extension")




        # import ipdb; ipdb.set_trace()


        for substation in substations:
            sub_location = None

            for bus in substation['buses']:
                if bus['id'] in geolocation_lookup:
                    bus_location = geolocation_lookup[bus['id']]
                    if sub_location != None:
                        if sub_location['longitude'] != bus_location['longitude'] \
                            or sub_location['latitude'] != bus_location['latitude']:
                            print('WARNING: sub location {} and bus location differ {}'.format(sub_location, bus_location))
                    else:
                        sub_location = bus_location
                # omit becouse there are a lot of these
                else:
                    print('WARNING: no location for bus id {} in substation {}'.format(bus['id'], substation['id']))

            if sub_location != None:
                substation['longitude'] = sub_location['longitude']
                substation['latitude'] = sub_location['latitude']
                #print(substation)
            else:
                print('WARNING: no location for substation {} {}'.format(substation['id'], substation['name']))


    trans_group_id = 1
    transformer_tuple_lookup = {}
    for i, trans in enumerate(raw_case.transformers):
        trans_id = i+1
        pr_bus = int(trans.p1.i)
        sn_bus = int(trans.p1.j)
        tr_bus = int(trans.p1.k)
        ckt = str(trans.p1.ckt).strip()

        if tr_bus == 0:
            key = (pr_bus, sn_bus)
        else:
            key = (pr_bus, sn_bus, tr_bus)

        comp_type = 'physical'
        if ckt in ['\'99\'', "'EQ'", "99", "EQ"]:
            comp_type = 'virtual'
            print('marking transformer {} - {} {} {} {} as virtual'.format(trans_id, pr_bus, sn_bus, tr_bus, ckt))

        trans_data = {
            'id':trans_id,
            'type':comp_type,
            'name':'{} {} {} {}'.format(trans.p1.i, trans.p1.j, trans.p1.k, trans.p1.ckt)
        }

        if not key in transformer_tuple_lookup:
            transformer_tuple_lookup[key] = {
                'id':trans_group_id,
                'transformers':[]
            }
            trans_group_id += 1

        transformer_tuple_lookup[key]['transformers'].append(trans_data)

    for k, v in transformer_tuple_lookup.items():
        bus_sub = bus_sub_lookup[k[0]]
        assert(all([ bus_sub == bus_sub_lookup[bus_id] for bus_id in k]))
        bus_sub['transformer_groups'].append(v)


    branch_bp_id = 1
    branch_bp_lookup = {}
    for i, branch in enumerate(raw_case.branches):
        branch_id = i+1
        from_bus = int(branch.i)
        to_bus = int(branch.j)
        ckt = str(branch.ckt).strip()

        #print(from_bus, to_bus)
        #assert(bus_sub_lookup[from_bus] != bus_sub_lookup[to_bus])

        comp_type = 'physical'
        if ckt in ['\'99\'', "'EQ'", "99", "EQ"]:
            comp_type = 'virtual'
            print('marking branch {} - {} {} {} as virtual'.format(branch_id, from_bus, to_bus, ckt))

        branch_data = {
            'id':branch_id,
            'type':comp_type,
            'name': '{} {} {}'.format(branch.i, branch.j, branch.ckt)
        }

        key = (from_bus, to_bus)
        if not key in branch_bp_lookup:
            branch_bp_lookup[key] = {
                'id':branch_bp_id,
                'branches':[]
            }
            branch_bp_id += 1

        branch_bp_lookup[key]['branches'].append(branch_data)


    facts_bp_id = 1
    facts_bp_lookup = {}
    for i, facts in enumerate(raw_case.facts):
        facts_id = i+1
        from_bus = int(facts.i)
        to_bus = int(facts.j)

        if to_bus != 0:
            assert(bus_sub_lookup[from_bus] != bus_sub_lookup[to_bus])

            facts_data = {
                'id':facts_id,
                'type':'physical',
                'name': '{} {} {}'.format(branch.i, branch.j, branch.ckt)
            }

            key = (from_bus, to_bus)
            if not key in facts_bp_lookup:
                facts_bp_lookup[key] = {
                    'id':facts_bp_id,
                    'facts':[]
                }
                facts_bp_id += 1
            facts_bp_lookup[key]['facts'].append(facts_data)


    tt_dc_bp_id = 1
    tt_dc_bp_lookup = {}
    for i, tt_dc in enumerate(raw_case.tt_dc_lines):
        tt_dc_id = i+1
        from_bus = int(tt_dc.rectifier.ipr)
        to_bus = int(tt_dc.inverter.ipi)
        if bus_sub_lookup[from_bus] != bus_sub_lookup[to_bus]:
            tt_dc_data = {
                'id':tt_dc_id,
                'type':'physical',
                'name': '{} {} {}'.format(from_bus, to_bus, tt_dc.params.name)
            }

            key = (from_bus, to_bus)
            if not key in tt_dc_bp_lookup:
                tt_dc_bp_lookup[key] = {
                    'id':tt_dc_bp_id,
                    'tt_dcs':[]
                }
                tt_dc_bp_id += 1
            tt_dc_bp_lookup[key]['tt_dcs'].append(tt_dc_data)

    vsc_dc_bp_id = 1
    vsc_dc_bp_lookup = {}
    for i, vsc_dc in enumerate(raw_case.vsc_dc_lines):
        vsc_dc_id = i+1
        from_bus = int(vsc_dc.c1.ibus)
        to_bus = int(vsc_dc.c2.ibus)
        if bus_sub_lookup[from_bus] != bus_sub_lookup[to_bus]:
            vsc_dc_data = {
                'id':vsc_dc_id,
                'type':'physical',
                'name': '{} {} {}'.format(from_bus, to_bus, vsc_dc.params.name)
            }

            key = (from_bus, to_bus)
            if not key in vsc_dc_bp_lookup:
                vsc_dc_bp_lookup[key] = {
                    'id':tt_dc_bp_id,
                    'vsc_dcs':[]
                }
                vsc_dc_bp_id += 1
            vsc_dc_bp_lookup[key]['vsc_dcs'].append(vsc_dc_data)


    corridor_branch_lookup = {}
    for (from_bus, to_bus), branch_group in branch_bp_lookup.items():
        #print('{} {} {}'.format(from_bus, to_bus, v))
        sub_from = bus_sub_lookup[from_bus]
        sub_to = bus_sub_lookup[to_bus]
        if sub_from == sub_to:
            sub_from['branch_groups'].append(branch_group)
        else:
            if sub_from['id'] > sub_to['id']:
                sub_from = bus_sub_lookup[to_bus]
                sub_to = bus_sub_lookup[from_bus]
            corridor_key = (sub_from['id'], sub_to['id'])
            if not corridor_key in corridor_branch_lookup:
                corridor_branch_lookup[corridor_key] = []
            corridor_branch_lookup[corridor_key].append(branch_group)


    corridor_facts_lookup = {}
    for (from_bus, to_bus), facts_group in facts_bp_lookup.items():
        sub_from = bus_sub_lookup[from_bus]
        sub_to = bus_sub_lookup[to_bus]

        if sub_from['id'] > sub_to['id']:
            sub_from = bus_sub_lookup[to_bus]
            sub_to = bus_sub_lookup[from_bus]
        corridor_key = (sub_from['id'], sub_to['id'])
        if not corridor_key in corridor_facts_lookup:
            corridor_facts_lookup[corridor_key] = []
        corridor_facts_lookup[corridor_key].append(facts_group)


    corridor_tt_dc_lookup = {}
    for (from_bus, to_bus), tt_dc_group in tt_dc_bp_lookup.items():
        sub_from = bus_sub_lookup[from_bus]
        sub_to = bus_sub_lookup[to_bus]

        if sub_from['id'] > sub_to['id']:
            sub_from = bus_sub_lookup[to_bus]
            sub_to = bus_sub_lookup[from_bus]
        corridor_key = (sub_from['id'], sub_to['id'])
        if not corridor_key in corridor_tt_dc_lookup:
            corridor_tt_dc_lookup[corridor_key] = []
        corridor_tt_dc_lookup[corridor_key].append(tt_dc_group)


    corridor_vsc_dc_lookup = {}
    for (from_bus, to_bus), vsc_dc_group in vsc_dc_bp_lookup.items():
        sub_from = bus_sub_lookup[from_bus]
        sub_to = bus_sub_lookup[to_bus]

        if sub_from['id'] > sub_to['id']:
            sub_from = bus_sub_lookup[to_bus]
            sub_to = bus_sub_lookup[from_bus]
        corridor_key = (sub_from['id'], sub_to['id'])
        if not corridor_key in corridor_vsc_dc_lookup:
            corridor_vsc_dc_lookup[corridor_key] = []
        corridor_vsc_dc_lookup[corridor_key].append(vsc_dc_group)


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
            'type':'physical',
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

        physical_branch = any(branch['type']=='physical' for branch_group in corridor['branch_groups'] for branch in branch_group['branches'])
        physical_facts = any(facts['type']=='physical' for facts_group in corridor['facts_groups'] for facts in facts_group['facts'])
        physical_tt_dc = any(tt_dc['type']=='physical' for tt_dc_group in corridor['tt_dc_groups'] for tt_dc in tt_dc_group['tt_dcs'])
        physical_vsc_dc = any(vsc_dc['type']=='physical' for vsc_dc_group in corridor['vsc_dc_groups'] for vsc_dc in vsc_dc_group['vsc_dcs'])

        if not (physical_branch or physical_facts or physical_tt_dc or physical_vsc_dc):
            corridor['type'] = 'virtual'
            print('marking corridor {} as virtual'.format(corr_id))

        corridors.append(corridor)


        for substation in substations:
            physical_bus = any(bus['type']=='physical' for bus in substation['buses'])
            physical_branch = any(branch['type']=='physical' for branch_group in substation['branch_groups'] for branch in branch_group['branches'])
            physical_transformer = any(transformer['type']=='physical' for transformer_group in substation['transformer_groups'] for transformer in transformer_group['transformers'])

            if not (physical_bus or physical_branch or physical_transformer):
                substation['type'] = 'virtual'
                print('marking substation {} as virtual'.format(substation['id']))


    connectivity = {
        'case': args.raw_file,
        'substations': substations,
        'corridors': corridors
    }
    print('Nodes: %d' % len(raw_case.buses))
    print('Edges: %d' % (len(raw_case.branches)+len(raw_case.transformers)+len(raw_case.tt_dc_lines)+len(raw_case.vsc_dc_lines)))
    print('')
    print('Substations: %d' % len(substations))
    print('Corridors: %d' % len(corridors))

    with open(args.output, 'w') as outfile:
        json.dump(connectivity, outfile, sort_keys=True, indent=2, separators=(',', ': '))


def get_base_kv(from_bus_id, to_bus_id, bus_lookup, comp_id):
    from_base_kv = float(bus_lookup[from_bus_id].basekv)
    to_base_kv = float(bus_lookup[to_bus_id].basekv)

    #print(from_base_kv, to_base_kv)
    if from_base_kv != to_base_kv:
        print('WARNING: different base kv values on component id {} {}:{} {}:{}'.format(comp_id, from_bus_id, from_base_kv, to_bus_id, to_base_kv))
    #assert(from_base_kv == to_base_kv)
    return max(from_base_kv, to_base_kv)


def connectivity_range(lb, ub, value, watch, threshold):
    assert(watch in ['lb','ub','both','none'])
    assert(threshold >= 0.0 and threshold <= 1.0)
    return {
        'display_type':'range',
        'lb':lb,
        'ub':ub,
        'value':value,
        'watch':watch,
        'threshold':threshold
    }


def build_cli_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('raw_file', help='the psse file to operate on (.raw)')
    parser.add_argument('-o', '--output', help='the place to send the output (.json)', default='connectivity.json')
    parser.add_argument('-k', '--kv-threshold' , help='the minimum voltage to be represented in the network connectivity', type=float, default=0.0)
    parser.add_argument('-g', '--bus-geolocations' , help='bus geolocation data (.geojson/csv)')
    parser.add_argument('-n', '--bus-geolocations-index', default='id', help='index field name for bus geolocations .geojson')

    return parser


if __name__ == '__main__':
    parser = build_cli_parser()
    main(parser.parse_args())
