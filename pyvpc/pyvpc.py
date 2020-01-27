
from pkg_resources import get_distribution, DistributionNotFound
import argparse
import re
from sys import stderr


def is_valid_cidr(cidr):
    """
    Check if input ipv4 cidr is valid,
    if string is as 10.0.0.124/30 will return True, else false
    :param cidr: string
    :return: boolean
    """
    ipv4_cidr_regex = re.compile(r'^([0-9]{1,3}\.){3}[0-9]{1,3}(/([0-9]|[1-2][0-9]|3[0-2]))?$')
    if ipv4_cidr_regex.match(cidr):
        return True
    return False


def get_self_version(dist_name):
    """
    Return version number of input distribution name,
    If distribution not found return not found indication
    :param dist_name: string
    :return: version as string
    """
    try:
        return get_distribution(dist_name).version
    except DistributionNotFound:
        return 'version not found'


def main():
    parser = argparse.ArgumentParser(description='Python AWS VPC CIDR available range finder with sub networks')

    parser.add_argument('--version', action='version',
                        version='%(prog)s {}'.format(get_self_version('pyvpc')),
                        help='Print version and exit')

    parser.add_argument('--cidr-range', help='Check free ranges in current cidr', required=True)
    args = vars(parser.parse_args())

    ipv4_cidr = args['cidr_range']

    if not is_valid_cidr(ipv4_cidr):
        print("Invalid IPv4 CIDR: {}".format(ipv4_cidr), file=stderr)
        exit(1)


if __name__ == "__main__":
    main()
