#!/usr/bin/env python3

import argparse, json, csv, itertools

def main(args):
    with open(args.connectivity_file, 'r') as file:
        data = json.load(file)

    ids = set()
    branch_count =  check_group_ids(data['corridors'], 'branch_groups', 'branches', ids)
    branch_count += check_group_ids(data['substations'], 'branch_groups', 'branches', ids)
    print('CHECK: found {} unqiue branch_group ids for {} branches'.format(len(ids), branch_count))

    ids = set()
    branch_count = check_group_ids(data['substations'], 'transformer_groups', 'transformers', ids)
    print('CHECK: found {} unqiue branch_group ids for {} branches'.format(len(ids), branch_count))

    other_components_groups = [
        ('facts_groups', 'facts'), 
        ('tt_dc_groups', 'tt_dcs'),
        ('vsc_dc_groups', 'vsc_dcs'),
    ]
    for group_name, comp_name in other_components_groups:
        ids = set()
        comp_count = check_group_ids(data['corridors'], group_name, comp_name, ids)
        print('CHECK: found {} unqiue {} ids for {} {}'.format(len(ids), group_name, comp_count, comp_name))


def check_group_ids(data, group_name, component_name, group_ids):
    component_count = 0
    for item in data:
        for group in item[group_name]:
            group_id = group['id']
            assert(group_id not in group_ids)
            group_ids.add(group_id)
            component_count += len(group[component_name])
    return component_count


def build_cli_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument('connectivity_file', help='the connectivty file to operate on (.json)')
    return parser

if __name__ == '__main__':
    parser = build_cli_parser()
    main(parser.parse_args())
