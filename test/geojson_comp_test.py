import sys, os, json

from common_test import data_dir

sys.path.append('.')
import geojson_comp


def test_rts(capfd):
    geojson_comp.create_geojson(
        data_dir+'/nesta_case73_ieee_rts/connectivity.json',
        data_dir+'/nesta_case73_ieee_rts/tmp.json'
    )

    #rtdout, rtderr = capfd.readouterr()

    #print(rtdout)
    #print(rtderr)

    with open(data_dir+'/nesta_case73_ieee_rts/tmp.json') as file:
        result_data = json.load(file)

    os.remove(data_dir+'/nesta_case73_ieee_rts/tmp.json')

    with open(data_dir+'/nesta_case73_ieee_rts/geo.json') as file:
        expected_data = json.load(file)

    #del result_data['case']
    #del expected_data['case']

    #print(expected_data)
    #print(result_data)
    assert(expected_data == result_data)


def test_fraken(capfd):
    geojson_comp.create_geojson(
        data_dir+'/frankenstein/connectivity.json',
        data_dir+'/frankenstein/tmp.json'
    )

    #rtdout, rtderr = capfd.readouterr()

    #print(rtdout)
    #print(rtderr)

    with open(data_dir+'/frankenstein/tmp.json') as file:
        result_data = json.load(file)

    os.remove(data_dir+'/frankenstein/tmp.json')

    with open(data_dir+'/frankenstein/geo.json') as file:
        expected_data = json.load(file)

    #del result_data['case']
    #del expected_data['case']

    assert(expected_data == result_data)

