import unittest
from ipaddress import IPv4Network, IPv4Address

from pyvpc.pyvpc import get_available_network


class IPv4Test(unittest.TestCase):
    def setUp(self):
        self.cidr_requested = IPv4Network('10.0.0.0/8')
        self.reserved_networks = [
            IPv4Network('10.10.0.0/16'), IPv4Network('10.8.0.0/14'), IPv4Network('10.50.0.0/16')
        ]

        self.not_overlapping_cidr = IPv4Network('10.80.0.0/16')
        self.not_overlapping_networks = [
            IPv4Network('10.90.0.0/16'), IPv4Network('10.170.18.0/24')
        ]

    def test_get_available_network(self):
        # Tests passing empty list (no reserved networks)
        self.assertEqual(
            get_available_network(self.cidr_requested, []),
            [
                {'lower_ip': IPv4Address('10.0.0.0'), 'upper_ip': IPv4Address('10.255.255.255'), 'available': True}
            ]
        )

        # Test passing overlapping networks, view documentation of get_available_network function for graphic details
        self.assertEqual(
            get_available_network(self.cidr_requested, self.reserved_networks),
            [
                {'lower_ip': IPv4Address('10.0.0.0'), 'upper_ip': IPv4Address('10.7.255.255'), 'available': True},
                {'lower_ip': IPv4Address('10.8.0.0'), 'upper_ip': IPv4Address('10.11.255.255'), 'available': False},
                {'lower_ip': IPv4Address('10.10.0.0'), 'upper_ip': IPv4Address('10.10.255.255'), 'available': False},
                {'lower_ip': IPv4Address('10.12.0.0'), 'upper_ip': IPv4Address('10.49.255.255'), 'available': True},
                {'lower_ip': IPv4Address('10.50.0.0'), 'upper_ip': IPv4Address('10.50.255.255'), 'available': False},
                {'lower_ip': IPv4Address('10.51.0.0'), 'upper_ip': IPv4Address('10.255.255.255'), 'available': True}]
        )

        # Test passing non overlapping networks
        self.assertEqual(
            get_available_network(self.not_overlapping_cidr, self.not_overlapping_networks),
            [
                {'lower_ip': IPv4Address('10.80.0.0'), 'upper_ip': IPv4Address('10.80.255.255'), 'available': True}
            ]
        )


if __name__ == '__main__':
    unittest.main()
