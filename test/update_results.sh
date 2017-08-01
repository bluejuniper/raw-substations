#!/bin/bash

# updates baseline results

../connectivity_comp.py data/nesta_case73_ieee_rts/network.raw -g data/nesta_case73_ieee_rts/coordinates.csv -o data/nesta_case73_ieee_rts/connectivity.json
../geojson_comp.py  data/nesta_case73_ieee_rts/connectivity.json data/nesta_case73_ieee_rts/geo.json


../connectivity_comp.py data/frankenstein/network.raw -g data/frankenstein/coordinates.csv -o data/frankenstein/connectivity.json
../geojson_comp.py  data/frankenstein/connectivity.json data/frankenstein/geo.json
