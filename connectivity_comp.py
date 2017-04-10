#!/usr/bin/env python3

import argparse, json, csv, itertools

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


def main(args):
    raw_case = parse_raw(args.raw_file)

    print('raw , %d, %d, %d' % (len(raw_case['buses']), len(raw_case['branches']), len(raw_case['transformers'])))

    for k,v in raw_case.items():
        print('{} - {}'.format(k, len(v)))
    print('')

    bus_lookup = { int(bus[0]):bus for bus in raw_case['buses'] }
    load_lookup = { i+1:load for i, load in enumerate(raw_case['loads']) }
    owner_lookup = { int(owner[0]):owner for i, owner in enumerate(raw_case['owners']) }
    fixed_shunt_lookup = { i+1:fs for i, fs in enumerate(raw_case['f_shunts']) }
    switched_shunt_lookup = { i+1:ss for i, ss in enumerate(raw_case['s_shunts']) }
    generator_lookup = { i+1:g for i, g in enumerate(raw_case['gens']) }

    transformer_lookup = { i+1:tr for i, tr in enumerate(raw_case['transformers']) }
    branch_lookup = { i+1:branch for i, branch in enumerate(raw_case['branches']) }
    facts_lookup = { i+1:facts for i, facts in enumerate(raw_case['facts']) }
    tt_dc_lookup = { i+1:tt_dc for i, tt_dc in enumerate(raw_case['tt_dc']) }
    vsc_dc_lookup = { i+1:vsc_dc for i, vsc_dc in enumerate(raw_case['vsc_dc']) }


    bus_sub_lookup = {}
    for bus in raw_case['buses']:
        bus_id = int(bus[0])
        #print(bus_id)
        bus_sub_lookup[bus_id] = set([bus_id])

    for trans in raw_case['transformers']:
        pr_bus = int(trans[0][0])
        sn_bus = int(trans[0][1])
        tr_bus = int(trans[0][2])

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
            #'name':'{} - {}'.format(bus_id, bus[1]),
            'name':'{}'.format(bus[1]),
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
            'name':'{} {}'.format(load[0], load[1]),
        }
        bus_data_lookup[bus_id]['loads'].append(load_data)

    for i, generator in enumerate(raw_case['gens']):
        gen_id = i+1
        bus_id = int(generator[0])
        generator_data = {
            'id':gen_id,
            'name':'{} {}'.format(generator[0], generator[1]),
        }
        bus_data_lookup[bus_id]['generators'].append(generator_data)

    for i, fixed_shunt in enumerate(raw_case['f_shunts']):
        f_shunt_id = i+1
        bus_id = int(fixed_shunt[0])
        fixed_shunt_data = {
            'id':f_shunt_id,
            'name':'{} {}'.format(fixed_shunt[0], fixed_shunt[1]),
        }
        bus_data_lookup[bus_id]['fixed_shunts'].append(fixed_shunt_data)

    for i, switched_shunt in enumerate(raw_case['s_shunts']):
        s_shunt_id = i+1
        bus_id = int(switched_shunt[0])
        switched_shunt_data = {
            'id':s_shunt_id,
            'name':'{}'.format(switched_shunt[0]),
        }
        bus_data_lookup[bus_id]['switched_shunts'].append(switched_shunt_data)

    for i, facts in enumerate(raw_case['facts']):
        facts_id = i+1
        from_bus = int(facts[1])
        to_bus = int(facts[2])
        if to_bus == 0:
            facts_data = {
                'id':facts_id,
                'name':'{} {}'.format(facts[1], facts[0]),
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

    if args.geolocations != None:
        geolocation_lookup = {}
        all_locations = set()
        with open(args.geolocations, 'r') as csvfile:
        #for substation in substations:
            geolocation_csv = csv.reader(csvfile, delimiter=',', quotechar='"')
            next(geolocation_csv, None)  # skip the header
            for row in geolocation_csv:
                location = typed_location(*row)
                if location.zone not in geolocation_lookup:
                    geolocation_lookup[location.zone] = {}
                geolocation_lookup[location.zone][location.raw_bus_name] = location
                all_locations.add(location)
        unmatched_locations = set(all_locations)

        max_lat = float('-Inf')
        max_lon = float('-Inf')

        min_lat = float('Inf')
        min_lon = float('Inf')
        
        for loc in all_locations:
            max_lat = max(max_lat, loc.latitude)
            max_lon = max(max_lon, loc.longitude)

            min_lat = min(min_lat, loc.latitude)
            min_lon = min(min_lon, loc.longitude)

        print('latitude extent: {} - {}'.format(min_lat, max_lat))
        print('longitude extent: {} - {}'.format(min_lon, max_lon))

        substation_location = {}
        for substation in substations:
            location_canditates = []
            for bus in substation['buses']:
                bus_data = bus_lookup[bus['id']]
                bus_name = bus_data[1].strip('\'').strip()
                bus_zone = int(bus_data[5])

                zone_locations = geolocation_lookup[bus_zone]

                #mataches = {}
                #scaling_factor = float(max(*[len(name) for name in zone_locations], len(bus_name)))
                for location_bus_name in zone_locations:
                    #mataches[location_bus_names] = prefix_size(bus_name, location_bus_names)
                    #score = edit_distance(bus_name, location_bus_names)/scaling_factor
                    score = edit_distance(bus_name, location_bus_name)
                    match_name = location_bus_name
                    for name_part in location_bus_name.split():
                        part_score = edit_distance(bus_name, name_part)
                        if part_score < score:
                            score = part_score
                            match_name = name_part

                    location_canditates.append(LocationCanditate(bus['id'], bus_name, match_name, score, zone_locations[location_bus_name]))
            
            location_canditates = sorted(location_canditates, key=lambda x: x.score)
            print('')
            print(substation['name'])
            print([bus['name'] for bus in substation['buses']])
            for lc in location_canditates:
                print('  {} - {} {} - {} : {}'.format(lc.score, lc.bus_id, lc.bus_name, lc.location.raw_bus_name, lc.match_name))

            if location_canditates[0].score <= 4: # strong match
                min_score = location_canditates[0].score

                best_matches = set()
                for location_canditate in location_canditates:
                    if min_score < location_canditate.score:
                        break
                    loc = location_canditate.location
                    best_matches.add(loc)
                    if loc in unmatched_locations:
                        unmatched_locations.remove(loc)


                if len(best_matches) > 1:
                    print('WARNING: multiple matches, picking one at random' )
                    print([loc.bus_name for loc in best_matches])
                    max_lat_delta = float('-Inf')
                    max_lon_delta = float('-Inf')

                    for loc_i, loc_j in itertools.combinations(best_matches, 2):
                        max_lat_delta = max(max_lat_delta, abs(loc_i.latitude - loc_j.latitude))
                        max_lon_delta = max(max_lon_delta, abs(loc_i.longitude - loc_j.longitude))

                    print('max latitude delta: {}'.format(max_lat_delta))
                    print('max longitude delta: {}'.format(max_lon_delta))

                # Sort these matches, so that the selection is deterministic
                sorted_best_matches = sorted(best_matches, key=lambda x: x.id)
                sub_loc = sorted_best_matches[0]
                substation_location[substation['id']] = sub_loc

                substation['latitude'] = sub_loc.latitude
                substation['longitude'] = sub_loc.longitude

            # print(substation['name'])
            # print([bus['name'] for bus in substation['buses']])
            # print(location_canditates)
            # print('')

        print('matched substations: {} of {}'.format(len(substation_location), len(substations)))
        print('un-matched locations: {} of {}'.format(len(unmatched_locations), len(all_locations)))

        print('')
        for loc in unmatched_locations:
            print(loc)



    transformer_tuple_lookup = {}
    for i, trans in enumerate(raw_case['transformers']):
        trans_id = i+1
        pr_bus = int(trans[0][0])
        sn_bus = int(trans[0][1])
        tr_bus = int(trans[0][2])

        if tr_bus == 0:
            key = (pr_bus, sn_bus)
        else:
            key = (pr_bus, sn_bus, tr_bus)
        if not key in transformer_tuple_lookup:
            transformer_tuple_lookup[key] = []
        transformer_tuple_lookup[key].append((trans_id, trans))


    for k, v in transformer_tuple_lookup.items():
        bus_sub = bus_sub_lookup[k[0]]
        assert(all([ bus_sub == bus_sub_lookup[bus_id] for bus_id in k]))
        transformer_list = []
        for trans_id, trans in v:
            trans_data = {'id':trans_id}
            trans_data['name'] = '{} {} {} {}'.format(trans[0][0], trans[0][1], trans[0][2], trans[0][3])
            # if len(k) == 2:
            #     trans_data['name'] = '{} - {} {} {}'.format(trans_id, k[0], k[1], trans[0][3])
            # else:
            #     trans_data['name'] = '{} - {} {} {} {}'.format(trans_id, k[0], k[1], k[2], trans[0][3])
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
                'name': '{} {} {}'.format(branch[0], branch[1], branch[2])
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
                'name': '{} {} {}'.format(branch[0], branch[1], branch[2])
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
                'name': '{} {} {}'.format(from_bus, to_bus, tt_dc[0])
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
                'name': '{} {} {}'.format(from_bus, to_bus, tt_vsc[0])
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

    if args.scs:
        print('Adding SCS Data')

        # setup component info
        for sub in substations:
            for bus in sub['buses']:
                bus_id = bus['id']
                bus_data = bus_lookup[bus_id]

                bus['status'] = 1 if int(bus_data[3]) != 4 else 0

                bus_owner = int(bus_data[6])
                bus_owner_name = owner_lookup[bus_owner][1]

                base_kv = float(bus_data[2])
                bus['base_kv'] = base_kv
                bus['owner'] = bus_owner_name

                vm_val = float(bus_data[7])
                va_val = float(bus_data[8])
                vm_ub = float(bus_data[9])
                vm_lb = float(bus_data[10])
                bus['voltage'] = connectivity_range(vm_lb*base_kv, vm_ub*base_kv, vm_val*base_kv)
                bus['angle'] = va_val

                for generator in bus['generators']:
                    gen_id = generator['id']
                    generator_data = generator_lookup[gen_id]

                    generator['status'] = int(generator_data[14])

                    pg = float(generator_data[2])
                    qg = float(generator_data[3])

                    qg_ub = float(generator_data[4])
                    qg_lb = float(generator_data[5])

                    pg_ub = float(generator_data[16])
                    pg_lb = float(generator_data[17])

                    generator['active'] = connectivity_range(pg_lb, pg_ub, pg)
                    generator['reactive'] = connectivity_range(qg_lb, qg_ub, qg)

                for load in bus['loads']:
                    load_id = load['id']
                    load_data = load_lookup[load_id]

                    load['status'] = int(load_data[2])

                    pl = float(load_data[5])
                    ql = float(load_data[6])
                    load['active'] = connectivity_range(0, pl, pl) if pl >= 0 else connectivity_range(pl, 0, pl)
                    load['reactive'] = connectivity_range(0, ql, ql) if ql >= 0 else connectivity_range(ql, 0, ql)

                    if float(load_data[7]) != 0.0 or float(load_data[8]) != 0.0 or float(load_data[9]) != 0.0 or float(load_data[10]) != 0.0:
                        print('WARNING: non-constant power load!')

                for fixed_shunt in bus['fixed_shunts']:
                    fixed_shunt_id = fixed_shunt['id']
                    fixed_shunt_data = fixed_shunt_lookup[fixed_shunt_id]

                    fixed_shunt['status'] = int(fixed_shunt_data[2])

                    gl = float(fixed_shunt_data[3])
                    bl = float(fixed_shunt_data[4])

                    fixed_shunt['conductance'] = connectivity_range(0, gl, gl) if gl >= 0 else connectivity_range(gl, 0, gl)
                    fixed_shunt['susceptance'] = connectivity_range(0, bl, bl) if bl >= 0 else connectivity_range(bl, 0, bl)

                for switched_shunt in bus['switched_shunts']:
                    switched_shunt_id = switched_shunt['id']
                    switched_shunt_data = switched_shunt_lookup[switched_shunt_id]

                    switched_shunt['status'] = int(switched_shunt_data[3])

                for facts in bus['facts']:
                    facts_id = facts['id']
                    facts_data = facts_lookup[facts_id]

                    facts['status'] = int(facts_data[3])

            for transformer_group in sub['transformer_groups']:
                for transformer in transformer_group:
                    transformer_id = transformer['id']
                    transformer_data = transformer_lookup[transformer_id]

                    assert('status' not in transformer)
                    transformer['status'] = int(transformer_data[0][11])

                    transformer['cod_1'] = int(transformer_data[2][6])

                    rate_a_1 = float(transformer_data[2][3])
                    transformer['rate_a_1'] = connectivity_range(0, rate_a_1, 0)

                    transformer['active_tail_1'] = connectivity_range(-rate_a_1, rate_a_1, 0)
                    transformer['reactive_tail_1'] = connectivity_range(-rate_a_1, rate_a_1, 0)


        all_branch_groups = []
        for sub in substations:
            all_branch_groups.append(sub['branch_groups'])
        for cor in corridors:
            all_branch_groups.append(cor['branch_groups'])


        for branch_groups in all_branch_groups:
            for branch_group in branch_groups:
                for banch in branch_group:
                    #print(banch)
                    branch_id = banch['id']
                    branch_data = branch_lookup[branch_id]
                    from_bus_id = int(branch_data[0])
                    to_bus_id = int(branch_data[1])
                    
                    from_base_kv = float(bus_lookup[from_bus_id][2])
                    to_base_kv = float(bus_lookup[to_bus_id][2])

                    #print(from_base_kv, to_base_kv)
                    if from_base_kv != to_base_kv:
                        print('WARNING: different base kv values on branch {} {}:{} {}:{}'.format(branch_id, from_bus_id, from_base_kv, to_bus_id, to_base_kv))
                    #assert(from_base_kv == to_base_kv)
                    banch['base_kv'] = max(from_base_kv, to_base_kv)

                    banch['status'] = int(branch_data[13])

                    rate_a = float(branch_data[6])
                    banch['rate_a'] = connectivity_range(0, rate_a, 0)

                    banch['active_tail'] = connectivity_range(-rate_a, rate_a, 0)
                    banch['reactive_tail'] = connectivity_range(-rate_a, rate_a, 0)

                    banch['active_head'] = connectivity_range(-rate_a, rate_a, 0)
                    banch['reactive_head'] = connectivity_range(-rate_a, rate_a, 0)



        for cor in corridors:
            for facts_group in cor['facts_groups']:
                for facts in facts_group:
                    facts_id = facts['id']
                    facts_data = facts_lookup[facts_id]

                    facts['status'] = int(facts_data[3])

            for tt_dc_group in cor['tt_dc_groups']:
                for tt_dc in tt_dc_group:
                    tt_dc_id = tt_dc['id']
                    tt_dc_data = tt_dc_lookup[tt_dc_id]

                    tt_dc['status'] = int(tt_dc_data[1])

            for vsc_dc_group in cor['vsc_dc_groups']:
                for vsc_dc in vsc_dc_group:
                    vsc_dc_id = vsc_dc['id']
                    vsc_dc_data = vsc_dc_lookup[vsc_dc_id]

                    vsc_dc['status'] = int(vsc_dc_data[1])


        # setup derived component info
        for sub in substations:
            sub['base_kv_max'] = max(bus['base_kv'] for bus in sub['buses'])

        for cor in corridors:
            base_kv_levels = set(branch['base_kv'] for branch_group in cor['branch_groups'] for branch in branch_group)
            cor['base_kv_max'] = max(base_kv_levels)
            
            if len(base_kv_levels) > 1:
                print('WARNING: corridor {} has multiple base_kv levels {}'.format(cor['id'], base_kv_levels))

                for branch_group in cor['branch_groups']:
                    for banch in branch_group:
                        branch_data = branch_lookup[branch_id]
                        from_bus_id = int(branch_data[0])
                        to_bus_id = int(branch_data[1])
                        print('  branch {} ({}, {}) - base_kv {}'.format(banch['id'], from_bus_id, to_bus_id, banch['base_kv']))

        print('')


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

    with open(args.output, 'w') as outfile:
        json.dump(connectivity, outfile, sort_keys=True, indent=2, separators=(',', ': '))


def connectivity_range(lb, ub, value):
    return {
        'display_type':'range',
        'lb':lb,
        'ub':ub,
        'value':value
    }


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

    owner_lines = []
    raw_case['owners'] = owner_lines

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
    reading_owners = False
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

        if 'END OF SWITCHED SHUNT DATA' in line:
            reading_switched_shunts = False

        if 'END OF OWNER DATA' in line:
            reading_owners = False

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

        if 'BEGIN OWNER DATA' in line:
            reading_owners = True
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

        if reading_owners:
            owner_lines.append(line.strip().split(','))

        if reading_transformers:
            tr_parts = line.strip().split(',')
            two_winding = int(tr_parts[2]) == 0
            if two_winding:
                transformer_lines.append([
                    tr_parts,
                    raw_lines[line_index+1].strip().split(','),
                    raw_lines[line_index+2].strip().split(','),
                    raw_lines[line_index+3].strip().split(','),
                ])
                line_index += 3
            else:
                transformer_lines.append([
                    tr_parts,
                    raw_lines[line_index+1].strip().split(','),
                    raw_lines[line_index+2].strip().split(','),
                    raw_lines[line_index+3].strip().split(','),
                    raw_lines[line_index+4].strip().split(','),
                ])
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
    parser.add_argument('-o', '--output', help='the place to send the output (.json)', default='connectivity.json')
    parser.add_argument('-g', '--geolocations', help='the available geolocation data (.csv)')
    parser.add_argument('-scs', help='adds extra data to the json document for SCS', action='store_true', default=False)

    return parser

if __name__ == '__main__':
    parser = build_cli_parser()
    main(parser.parse_args())
