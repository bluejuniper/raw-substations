import json
from argparse import ArgumentParser


def create_geojson(conn_file, out_substations, out_corridors):
    with open(conn_file) as f:
        conn_data = json.load(f)

    crs = {"properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}, "type": "name"}

    substations = {'type': 'FeatureCollection', 'features': [], 'crs': crs}
    corridors = {'type': 'FeatureCollection', 'features': [], 'crs': crs}

    sub_coordinates = {sub['id']: [sub['longitude'], sub['latitude']] 
                       for sub in conn_data['substations']}

    for sub in conn_data['substations']:
        feature = {'type': 'Feature', 
                   'geometry': {'type': 'Point', 
                                'coordinates': sub_coordinates[sub['id']]},
                   'properties': sub}
        substations['features'].append(feature)

    for corridor in conn_data['corridors']:
        feature = {'type': 'Feature', 
                   'geometry': {'type': 'LineString', 
                                'coordinates': [sub_coordinates[corridor['from_substation']],
                                                sub_coordinates[corridor['to_substation']]]},
                   'properties': corridor}
        corridors['features'].append(feature)

    with open(out_substations, 'w') as f:
        f.write(json.dumps(substations))

    with open(out_corridors, 'w') as f:
        f.write(json.dumps(corridors))


if __name__ == '__main__':
    parser = ArgumentParser()
    parser.add_argument('connectivity', help='Connectivity json file')
    parser.add_argument('output_substations', help='Output substation geojson file')
    parser.add_argument('output_corridors', help='Output corridor geojson file')
    args = parser.parse_args()
    create_geojson(args.connectivity, args.output_substations, args.output_corridors)
