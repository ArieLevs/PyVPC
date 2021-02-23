import unittest
from argparse import ArgumentTypeError
from ipaddress import IPv4Network, IPv4Address

from pyvpc.pyvpc import get_available_networks, check_valid_ip_int, check_valid_ip_prefix, calculate_suggested_cidr
from pyvpc.pyvpc_cidr_block import PyVPCBlock, return_pyvpc_objects_json


class IPv4Test(unittest.TestCase):
    def setUp(self):
        self.reserved_pyvpc_block = PyVPCBlock(network=IPv4Network('10.90.0.0/16'),
                                               start_address=None,
                                               end_address=None,
                                               resource_id='vpc-some-vpc-id-here',
                                               name='arie-test-vpc',
                                               block_available=False)
        self.available_pyvpc_block = PyVPCBlock(network=None,
                                                start_address=IPv4Address('10.80.5.24'),
                                                end_address=IPv4Address('10.80.255.255'),
                                                resource_id=None,
                                                name=None,
                                                block_available=True)

        self.cidr_requested = IPv4Network('10.0.0.0/8')

        self.reserved_networks = [
            PyVPCBlock(network=IPv4Network('10.10.0.0/16')),
            PyVPCBlock(network=IPv4Network('10.8.0.0/14')),
            PyVPCBlock(network=IPv4Network('10.50.0.0/16'))
        ]

        self.not_overlapping_cidr = IPv4Network('10.80.0.0/24')
        self.not_overlapping_networks = [
            PyVPCBlock(network=IPv4Network('10.90.0.0/16')),
            PyVPCBlock(network=IPv4Network('10.170.18.0/24'))
        ]

    def test_pyvpc_block_object(self):
        self.assertEqual(self.reserved_pyvpc_block.get_id(), 'vpc-some-vpc-id-here')
        self.assertEqual(self.reserved_pyvpc_block.get_name(), 'arie-test-vpc')
        self.assertEqual(self.reserved_pyvpc_block.get_network(), IPv4Network('10.90.0.0/16'))
        self.assertEqual(self.reserved_pyvpc_block.get_start_address(), IPv4Address('10.90.0.0'))
        self.assertEqual(self.reserved_pyvpc_block.get_end_address(), IPv4Address('10.90.255.255'))
        self.assertEqual(self.reserved_pyvpc_block.get_num_addresses(), 65536)

    def test_get_available_network_empty(self):
        # Tests passing empty list (no reserved networks)

        # Return with an empty list, should return a list with single network which is cidr_requested itself
        self.assertEqual(get_available_networks(self.cidr_requested, [])[0].network, self.cidr_requested)
        # Since no reserved networks passed, the tested cidr should be available
        self.assertTrue(get_available_networks(self.cidr_requested, [])[0].block_available, True)

    def test_get_available_network(self):
        # Test passing overlapping networks, view documentation of get_available_network function for graphic details
        cidr_calc_ranges = get_available_networks(self.cidr_requested, self.reserved_networks)

        self.assertEqual(cidr_calc_ranges[0].get_start_address(), IPv4Address('10.0.0.0'))
        self.assertEqual(cidr_calc_ranges[0].get_end_address(), IPv4Address('10.7.255.255'))
        self.assertEqual(cidr_calc_ranges[0].get_name(), None)
        self.assertEqual(cidr_calc_ranges[0].get_num_addresses(), 524288)
        self.assertEqual(cidr_calc_ranges[0].block_available, True)

        self.assertEqual(cidr_calc_ranges[1].get_start_address(), IPv4Address('10.8.0.0'))
        self.assertEqual(cidr_calc_ranges[1].get_end_address(), IPv4Address('10.11.255.255'))
        self.assertEqual(cidr_calc_ranges[1].get_num_addresses(), 262144)
        self.assertEqual(cidr_calc_ranges[1].block_available, False)

        self.assertEqual(cidr_calc_ranges[2].get_start_address(), IPv4Address('10.10.0.0'))
        self.assertEqual(cidr_calc_ranges[2].get_end_address(), IPv4Address('10.10.255.255'))
        self.assertEqual(cidr_calc_ranges[2].get_num_addresses(), 65536)
        self.assertEqual(cidr_calc_ranges[2].block_available, False)

        self.assertEqual(cidr_calc_ranges[3].get_start_address(), IPv4Address('10.12.0.0'))
        self.assertEqual(cidr_calc_ranges[3].get_end_address(), IPv4Address('10.49.255.255'))
        self.assertEqual(cidr_calc_ranges[3].get_num_addresses(), 2490368)
        self.assertEqual(cidr_calc_ranges[3].get_name(), None)
        self.assertEqual(cidr_calc_ranges[3].block_available, True)

        self.assertEqual(cidr_calc_ranges[4].get_start_address(), IPv4Address('10.50.0.0'))
        self.assertEqual(cidr_calc_ranges[4].get_end_address(), IPv4Address('10.50.255.255'))
        self.assertEqual(cidr_calc_ranges[4].get_num_addresses(), 65536)
        self.assertEqual(cidr_calc_ranges[4].block_available, False)

        self.assertEqual(cidr_calc_ranges[5].get_start_address(), IPv4Address('10.51.0.0'))
        self.assertEqual(cidr_calc_ranges[5].get_end_address(), IPv4Address('10.255.255.255'))
        self.assertEqual(cidr_calc_ranges[5].get_num_addresses(), 13434880)
        self.assertEqual(cidr_calc_ranges[5].get_name(), None)
        self.assertEqual(cidr_calc_ranges[5].block_available, True)

    def test_get_available_network_non_overlapping(self):
        # Test passing non overlapping networks,
        # If passing IPv4Network with non overlapping networks, a single PyVPCBlock block should returned (in a list)
        cidr_calc_ranges = get_available_networks(self.not_overlapping_cidr, self.not_overlapping_networks)

        self.assertEqual(len(cidr_calc_ranges), 1)

        self.assertEqual(cidr_calc_ranges[0].network, self.not_overlapping_cidr)
        self.assertEqual(cidr_calc_ranges[0].get_num_addresses(), 256)

    def test_check_valid_ip_int(self):
        self.assertEqual(check_valid_ip_int(0), 0)
        self.assertTrue(check_valid_ip_int(1))
        self.assertTrue(check_valid_ip_int(4294967295))
        self.assertTrue(check_valid_ip_int(340282366920938463463374607431768211455))

        self.assertRaises(ArgumentTypeError, check_valid_ip_int, 'string')
        self.assertRaises(TypeError, check_valid_ip_int, None)

        self.assertRaises(ArgumentTypeError, check_valid_ip_int, 340282366920938463463374607431768211456)
        self.assertRaises(ArgumentTypeError, check_valid_ip_int, -1)

    def test_check_valid_ip_prefix(self):
        self.assertEqual(check_valid_ip_prefix(0), 0)
        self.assertTrue(check_valid_ip_prefix(1))
        self.assertTrue(check_valid_ip_prefix(32))

        self.assertRaises(ArgumentTypeError, check_valid_ip_prefix, -1)
        self.assertRaises(ArgumentTypeError, check_valid_ip_prefix, 33)
        self.assertRaises(ValueError, check_valid_ip_prefix, 'string')
        self.assertRaises(TypeError, check_valid_ip_prefix, None)

    def test_calculate_suggested_cidr(self):
        # Declare new small network so there are less return for tests
        cidr_requested = IPv4Network('10.10.10.0/24')
        reserved_networks = [PyVPCBlock(network=IPv4Network('10.10.10.0/26'))]

        # get all block (available or not) from reserved_networks
        # view documentation of get_available_network function for graphic details
        cidr_calc_ranges = get_available_networks(cidr_requested, reserved_networks)

        # test for all available sub networks, should return
        # | Lowest IP    | Upper IP     |   Num of Addr | Available   | ID   | Name   |
        # |--------------|--------------|---------------|-------------|------|--------|
        # | 10.10.10.64  | 10.10.10.127 |            64 | True        |      |        |
        # | 10.10.10.128 | 10.10.10.255 |           128 | True        |      |        |

        all_available_subnets = calculate_suggested_cidr(cidr_calc_ranges, None, None)

        self.assertEqual([all_available_subnets[0].get_network(),
                          all_available_subnets[1].get_network()],
                         [IPv4Network('10.10.10.64/26'),
                          IPv4Network('10.10.10.128/25')])

        # should raise "new prefix must be longer, lowest ip examined range is 10.10.10.64/26, but prefix was 8"
        self.assertRaises(ValueError, calculate_suggested_cidr, cidr_calc_ranges, 8, None)

        # test for all available networks with prefix of /26, should return
        # | Lowest IP    | Upper IP     |   Num of Addr | Available   | ID   | Name   |
        # |--------------|--------------|---------------|-------------|------|--------|
        # | 10.10.10.64  | 10.10.10.127 |            64 | True        |      |        |
        # | 10.10.10.128 | 10.10.10.191 |            64 | True        |      |        |
        # | 10.10.10.192 | 10.10.10.255 |            64 | True        |      |        |
        all_available_subnets = calculate_suggested_cidr(cidr_calc_ranges, 26, None)

        self.assertEqual([all_available_subnets[0].get_network(),
                          all_available_subnets[1].get_network(),
                          all_available_subnets[2].get_network()],
                         [IPv4Network('10.10.10.64/26'),
                          IPv4Network('10.10.10.128/26'),
                          IPv4Network('10.10.10.192/26')])

        # test for networks with at least 100 addresses, should return
        # | Lowest IP    | Upper IP     |   Num of Addr | Available   | ID   | Name   |
        # |--------------|--------------|---------------|-------------|------|--------|
        # | 10.10.10.128 | 10.10.10.255 |           128 | True        |      |        |
        all_available_subnets = calculate_suggested_cidr(cidr_calc_ranges, None, 100)
        self.assertEqual([all_available_subnets[0].get_network()], [IPv4Network('10.10.10.128/25')])

        # test for network with at least 200 addresses, should return empty list as these are no possible networks
        all_available_subnets = calculate_suggested_cidr(cidr_calc_ranges, None, 200)
        self.assertEqual(all_available_subnets, [])

    def test_return_pyvpc_objects_json(self):
        # Prepare list with single block so test response will not be long
        single_list_range_block = [self.reserved_pyvpc_block]
        self.assertEqual(return_pyvpc_objects_json(single_list_range_block),
                         '{"ranges": [{"start_address": "10.90.0.0", '
                         '"end_address": "10.90.255.255", '
                         '"num_of_addresses": 65536, '
                         '"prefix": 16, '
                         '"available": false, '
                         '"id": "vpc-some-vpc-id-here", '
                         '"name": "arie-test-vpc"}]}')


if __name__ == '__main__':
    unittest.main()
