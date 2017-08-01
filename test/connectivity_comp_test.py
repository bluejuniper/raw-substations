import sys, os, json

from common_test import data_dir

sys.path.append('.')
import connectivity_comp

parser = connectivity_comp.build_cli_parser()


def test_rts(capfd):
    connectivity_comp.main(parser.parse_args([
        data_dir+'/nesta_case73_ieee_rts/network.raw',
        '-scs',
        '-g', data_dir+'/nesta_case73_ieee_rts/coordinates.csv',
        '-o', data_dir+'/nesta_case73_ieee_rts/tmp.json'
    ]))

    #rtdout, rtderr = capfd.readouterr()

    #print(rtdout)
    #print(rtderr)

    with open(data_dir+'/nesta_case73_ieee_rts/tmp.json') as file:
        result_data = json.load(file)

    os.remove(data_dir+'/nesta_case73_ieee_rts/tmp.json')

    with open(data_dir+'/nesta_case73_ieee_rts/connectivity.json') as file:
        expected_data = json.load(file)

    del result_data['case']
    del expected_data['case']

    #print(expected_data)
    #print(result_data)
    assert(expected_data == result_data)


def test_fraken(capfd):
    connectivity_comp.main(parser.parse_args([
        data_dir+'/frankenstein/network.raw',
        '-scs',
        '-g', data_dir+'/frankenstein/coordinates.csv',
        '-o', data_dir+'/frankenstein/tmp.json'
    ]))

    #rtdout, rtderr = capfd.readouterr()

    #print(rtdout)
    #print(rtderr)

    with open(data_dir+'/frankenstein/tmp.json') as file:
        result_data = json.load(file)

    os.remove(data_dir+'/frankenstein/tmp.json')

    with open(data_dir+'/frankenstein/connectivity.json') as file:
        expected_data = json.load(file)

    del result_data['case']
    del expected_data['case']

    assert(expected_data == result_data)

