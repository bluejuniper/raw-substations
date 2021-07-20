import json
import pandas as pd

with open("wecc_hill_connectivity0_no_fdl.json") as f:
    conn = json.load(f)

locs_df = pd.read_csv("wecc_hill_subs_fdl.csv")

locs = {}


for i,loc in locs_df.iterrows():
    locs[loc['substation_id']] = loc['x'], loc['y']

cx = locs_df['x'].mean()
cy = locs_df['y'].mean()

for sub in conn['substations']:
    if sub['id'] not in locs:
        print('Could not find sub {}'.format(sub['id']))
        sub['longitude'] = cx
        sub['latitude'] = cy
        continue

    p = locs[sub['id']] 
    # sub['longitude'], sub['latitude'] = p
    sub['longitude'] = p[0]
    sub['latitude'] = p[1]


with open("wecc_hill_connectivity_fdl.json", 'w') as f:
    json.dump(conn, f, indent=4)

