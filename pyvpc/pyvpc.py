import argparse
import ipaddress
from sys import stderr

import boto3
from pkg_resources import get_distribution, DistributionNotFound

try:
    from pyvpc_cidr_block import PyVPCBlock, return_pyvpc_objects_string, return_pyvpc_objects_json
except ModuleNotFoundError:
    from .pyvpc_cidr_block import PyVPCBlock, return_pyvpc_objects_string, return_pyvpc_objects_json


def get_aws_resource_name(resource):
    if 'Tags' in resource:
        for tag in resource['Tags']:
            if tag['Key'] == 'Name':
                return tag['Value']
    return None


def get_aws_regions_list():
    """
    Get a list of AWS regions, uses:
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_regions
    Return a list of strings with all available regions
    :return: list
    """
    regions = boto3.client('ec2').describe_regions()['Regions']
    regions_list = []
    for region in regions:
        regions_list.append(region['RegionName'])
    return regions_list


def get_aws_vpc_if_exists(vpc_id_name, aws_region=None):
    """
    Return reserved subnets, in input vpc

    if first response successful, using vpc-id filter return the vpc-id found,
    if vpc not found by its id, make second call using name filter,
    return error if more then one vpc has same name

    :param vpc_id_name: string
    :param aws_region: string
    :return: PyVPCBlock object
    """
    response = boto3.client('ec2', region_name=aws_region).describe_vpcs(
        Filters=[
            {
                'Name': 'vpc-id',
                'Values': [
                    vpc_id_name,
                ]
            },
        ],
    )['Vpcs']

    if response:
        vpc_cidr = ipaddress.ip_network(response[0]['CidrBlock'])
        vpc_id = response[0]['VpcId']
        vpc_name = get_aws_resource_name(response[0])
        return PyVPCBlock(network=vpc_cidr, resource_id=vpc_id, name=vpc_name, resource_type='vpc')

    # In case no VPC found using vpc-id filter, try using input as name filter
    response = boto3.client('ec2', region_name=aws_region).describe_vpcs(
        Filters=[
            {
                'Name': 'tag:Name',
                'Values': [
                    vpc_id_name,
                ]
            },
        ],
    )['Vpcs']

    # There is a single vpc with 'vpc_id_name'
    if len(response) == 1:
        vpc_cidr = ipaddress.ip_network(response[0]['CidrBlock'])
        vpc_id = response[0]['VpcId']
        vpc_name = get_aws_resource_name(response[0])
        return PyVPCBlock(network=vpc_cidr, resource_id=vpc_id, name=vpc_name, resource_type='vpc')
    # Is case there are multiple VPCs with the same name, raise exception
    elif len(response) > 1:
        found = []
        for x in response:
            found.append(x['VpcId'])
        raise ValueError("more then one vpc found with name {} - {}".format(vpc_id_name, str(found)))

    # Nothing found
    return None


def get_aws_reserved_subnets(vpc_id, aws_region=None):
    """
    Get a list of AWS subnets of a given VPC
    :param vpc_id: string
    :param aws_region: string
    :return: list of PyVPCBlock objects
    """
    response = boto3.client('ec2', region_name=aws_region).describe_subnets(
        Filters=[
            {
                'Name': 'vpc-id',
                'Values': [
                    vpc_id,
                ]
            }
        ])['Subnets']

    reserved_subnets = []
    for subnet in response:
        reserved_subnets.append(PyVPCBlock(network=ipaddress.ip_network(subnet['CidrBlock']),
                                           resource_id=subnet['SubnetId'],
                                           name=get_aws_resource_name(subnet),
                                           resource_type='subnet'))
    return reserved_subnets


def get_aws_reserved_networks(region=None, all_regions=False):
    """
    Get a list of AWS cidr networks that are already used in input region,
    or get all vpc(s) from all available regions if all_regions is True, uses:
    https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/ec2.html#EC2.Client.describe_vpcs
    :param region: string
    :param all_regions: boolean
    :return: list of PyVPCBlock objects
    """
    result = []
    if all_regions:
        for aws_region in get_aws_regions_list():
            for vpc in boto3.client('ec2', region_name=aws_region).describe_vpcs()['Vpcs']:
                result.append(vpc)
    else:
        result = boto3.client('ec2', region_name=region).describe_vpcs()['Vpcs']

    vpc_used_cidr_list = []
    for vpc in result:
        vpc_used_cidr_list.append(PyVPCBlock(network=ipaddress.ip_network(vpc['CidrBlock']),
                                             resource_id=vpc['VpcId'],
                                             name=get_aws_resource_name(vpc),
                                             resource_type='vpc'))
    return vpc_used_cidr_list


def calculate_overlap_ranges(network, reserved_network):
    """
    Function will calculate all available ranges of over lapping network,  all possible scenarios demonstrates below.
    There are exactly 4 possible scenarios:

                                                     10.10.0.0
                                    10.8.0.0/14          |                10.11.255.255
                                        |                |                     |
    network      ->                     *--------------------------------------*
                                        |################|
    reserved     ->        |------------|----------------|
    network                |           ^                 |
                       10.5.0.0        |            10.9.255.255
                                  10.7.255.255



                      10.10.0.0/16                                                10.10.255.255
                           |                                                             |
    network      ->        *---------------|-----------------------------|---------------|
                                           |#############################|
    reserved     ->                        |-----------------------------|
    network                                |                             |
                                      10.10.50.0/24                  10.10.50.255

                      10.10.50.0/24           10.10.255.255
                            |                       |
    network      ->         *-----------|-----------|
                                        |###########|
    reserved     ->                     |-----------|-----------------------|
    network                             |                                   |
                                  10.10.0.0/16                         10.10.50.255

    :param network:
    :param reserved_network:
    :return:
    """
    if network.overlaps(reserved_network):
        ranges = []

        # If the lower boundary of current head is smaller than the lower boundary of reserved_network
        # It means the 'reserved_network' network is necessarily from 'the right' of head, and its available
        if network[0] < reserved_network[0]:
            ranges.append({'lower_ip': network[0], 'upper_ip': reserved_network[0] - 1, 'available': True})

        # Append the overlapping network as NOT available
        ranges.append({'lower_ip': reserved_network[0], 'upper_ip': reserved_network[-1], 'available': False})

        if reserved_network[-1] < network[-1]:
            ranges.append({'lower_ip': reserved_network[-1] + 1, 'upper_ip': network[-1], 'available': True})
        return ranges
    else:
        return [{'lower_ip': network[0], 'upper_ip': network[-1], 'available': True}]


def get_available_networks(desired_cidr, reserved_networks):
    """
    This function can be complex to understand without debugging,
    an example with
        'desired_cidr=10.0.0.0/8' and
        'reserved_networks=[IPv4Network('10.8.0.0/1'), IPv4Network('10.10.0.0/16'), IPv4Network('10.50.0.0/16')]'
        will be shown as comments

                                     (head)     10.10.0.0/16                                                 (tail)
                                   10.0.0.0/8        |     10.10.255.255/16                             10.255.255.255
                                       |             |            |                                             |
    (1) desired_cidr (10.0.0.0/8) ->   *----|--------|------------|---------|--------|------------|-------------|
                                            |#######^|############|^########|        |############|
    (2) reserved_net (10.10.0.0/16) ->      |#######||------------||########|        |############|
                                            |#######|##############|########|        |############|
    (3) reserved_net (10.50.0.0/16) ->      |#######|##############|########|        |------------|
                                            |#######|##############|########|        |            |
    (4) reserved_net (10.10.0.0/14) ->      |-------|--------------|--------|        |            |
                                      10.8.0.0/14   |              |   10.11.255.255 |            |
                                                    |              |                 |            |
                                            10.9.255.255/16   10.11.0.0/16           |            |
                                                                               10.50.0.0/16  10.50.255.255
    So in this example there should be 3 available ranges, and 3 reserved ranges (marked with #)
    Printed output should be:

    | Lowest IP   | Upper IP       |   Num of Addr | Available   | ID                    | Name          |
    |-------------|----------------|---------------|-------------|-----------------------|---------------|
    | 10.0.0.0    | 10.7.255.255   |        524288 | True        |                       |               |
    | 10.8.0.0    | 10.11.255.255  |        262144 | False       | vpc-vxx3X5hzPNk9Jws9G | alpha         |
    | 10.10.0.0   | 10.10.255.255  |         65536 | False       | vpc-npGac6CHRJE2JakNZ | dev-k8s       |
    | 10.12.0.0   | 10.49.255.255  |       2490368 | True        |                       |               |
    | 10.50.0.0   | 10.50.255.255  |         65536 | False       | vpc-f8Sbkd2jSLQF6x9Qd | arie-test-vpc |
    | 10.51.0.0   | 10.255.255.255 |      13434880 | True        |                       |               |

    :param desired_cidr: IPv4Network
    :param reserved_networks: list of PyVPCBlock objects
    :return: list of PyVPCBlock objects
    """
    # If there are no reserved networks, then return that all 'desired_cidr' (Network Object) range is available
    if not reserved_networks:
        # Since there are no reserved network, the lower, and upper boundary of the 'desired_cidr' can be used
        return [PyVPCBlock(network=desired_cidr,
                           block_available=True)]

    # Sort PyVPCBlock objects (reserved networks) by the 'network' field, so it will be easier to calculate
    reserved_networks = sorted(reserved_networks, key=lambda x: x.network, reverse=False)

    networks_result = []
    range_head = desired_cidr[0]  # Mark the start of calculation at the HEAD (view details above) point
    range_tail = desired_cidr[-1]  # Mark the end of calculation at the TAIL (view details above) point

    # Iterate over the reserved networks
    for reserved_net in reserved_networks:
        # If there is an overlap, we need to figure out how the reserved network is 'blocking' the desired cidr
        if desired_cidr.overlaps(reserved_net.get_network()):
            # If the lower boundary of current range_head is smaller than the lower boundary of reserved_net
            # It means the 'reserved_net' network is necessarily from 'the right' of range_head, and its available
            if range_head < reserved_net.get_start_address():
                networks_result.append(PyVPCBlock(start_address=range_head,
                                                  end_address=reserved_net.get_start_address() - 1,
                                                  block_available=True,
                                                  resource_type='available block'))

            # Append the overlapping network as NOT available
            networks_result.append(PyVPCBlock(network=reserved_net.get_network(), resource_id=reserved_net.get_id(),
                                              name=reserved_net.get_name()))

            # If the most upper address of current reserved_net (that is overlapping the desired_cidr),
            # is larger/equal than the most upper address of desired_cidr, then there is no point perform calculations
            if reserved_net.get_end_address() >= range_tail:
                break
            else:  # Else there might be other overlapping networks,
                # head should always point to the next lower available address
                # so only if current head is "from the left" of most upper overlapping network, set it as new head,
                # As there might be a case of an inner network, see reserved_net (2) for details
                if range_head < reserved_net.get_end_address():
                    # Set the new range_head value, to one ip address above the upper boundary of reserved_net
                    range_head = reserved_net.get_end_address() + 1

            # If last iteration (here are no more overlapping networks, until the 'range_tail' address)
            if reserved_networks.index(reserved_net) == len(reserved_networks) - 1:
                networks_result.append(PyVPCBlock(start_address=range_head,
                                                  end_address=range_tail,
                                                  block_available=True))

    # If result is empty, then there where reserved networks, but the did not overlapped
    if not networks_result:
        networks_result.append(PyVPCBlock(network=desired_cidr, block_available=True))
        return networks_result
    return networks_result


def calculate_suggested_cidr(ranges, prefix, minimal_num_of_addr):
    """
    Get available CIDR (network object), among input ip ranges, according requirements
    Example:
    Input ranges are:
    | Lowest IP   | Upper IP       |   Num of Addr | Available   | ID                    | Name          |
    |-------------|----------------|---------------|-------------|-----------------------|---------------|
    | 10.0.0.0    | 10.7.255.255   |        524288 | True        |                       |               |
    | 10.8.0.0    | 10.11.255.255  |        262144 | False       | vpc-vxx3X5hzPNk9Jws9G | alpha         |
    | 10.10.0.0   | 10.10.255.255  |         65536 | False       | vpc-npGac6CHRJE2JakNZ | dev-k8s       |
    | 10.12.0.0   | 10.49.255.255  |       2490368 | True        |                       |               |
    | 10.50.0.0   | 10.50.255.255  |         65536 | False       | vpc-f8Sbkd2jSLQF6x9Qd | arie-test-vpc |
    | 10.51.0.0   | 10.255.255.255 |      13434880 | True        |                       |               |

    function will iterate over all these ranges (lower - upper ip),
    and inspect only those that have the Available: True value,
    if minimal_num_of_addr param passed, return the first network that has enough addresses
    if prefix param passed, return first available network with input prefix
    if non of the above passed, return the first available network found

    :param ranges: list of PyVPCBlock objects
    :param prefix: int
    :param minimal_num_of_addr: int
    :return: IPv4Network object
    """
    possible_subnets = []

    # For each PyVPCBlock object (available or not)
    for net_range in ranges:
        # Only if available block found, there is logic to continue
        if net_range.block_available:
            possible_networks = []
            # The summarize_address_range function will return a list of IPv4Network objects,
            # Docs at https://docs.python.org/3/library/ipaddress.html#ipaddress.summarize_address_range
            net_cidr = ipaddress.summarize_address_range(net_range.get_start_address(), net_range.get_end_address())
            try:  # Convert start/end IPs to possible CIDRs,
                for net in net_cidr:
                    possible_networks.append(net)  # appending IPv4Network objects
            except TypeError as exc:
                raise TypeError('error converting {} and {} to cidr, '.format(net_range.get_start_address(),
                                                                              net_range.get_end_address()) + str(exc))
            except ValueError as exc:
                raise TypeError('error converting {} and {} to cidr, '.format(net_range.get_start_address(),
                                                                              net_range.get_end_address()) + str(exc))

            for network in possible_networks:
                # In case a minimal number of addresses requested
                if minimal_num_of_addr:
                    if minimal_num_of_addr <= network.num_addresses:
                        possible_subnets.append(PyVPCBlock(network=network, block_available=True))
                # Return first available network with input suffix
                elif prefix:
                    try:
                        network_subnets = network.subnets(new_prefix=prefix)
                        for sub in network_subnets:
                            possible_subnets.append(PyVPCBlock(network=sub, block_available=True))
                    except ValueError as exc:
                        raise ValueError(str(exc) + ', lowest ip examined range is {}, but prefix was {}'
                                         .format(network, prefix))
                # No prefix or minimal num of addresses requested
                else:
                    possible_subnets.append(PyVPCBlock(network=network, block_available=True))

    # If empty, then no suitable range found (or all are overlapping, or there are not enough ip addresses requested)
    # return list of PyVPCBlock objects
    return possible_subnets


def check_valid_ip_int(value):
    """
    Validate that value is an integer between 0 to 340,282,366,920,938,463,463,374,607,431,768,211,455
    IPv4 0 to 4,294,967,295
    IPv6 4,294,967,296 to 340,282,366,920,938,463,463,374,607,431,768,211,455

    :param value: int
    :return: int
    """
    try:
        address = int(value)
    except ValueError:
        raise argparse.ArgumentTypeError('value is not a positive number: {}'.format(value))
    try:
        ipaddress.ip_address(address)
    except ValueError:
        raise argparse.ArgumentTypeError('is out of IPv4/IPv6 boundaries')
    return address


def check_valid_ip_prefix(value):
    """
    Validate that value is an integer between 0 to 32

    :param value: int
    :return: int
    """
    prefix = int(value)
    if prefix < 0 or prefix > 32:
        raise argparse.ArgumentTypeError('{} is an invalid IPv4 prefix'.format(prefix))
    return prefix


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
    subparsers = parser.add_subparsers(dest='sub_command')

    parser.add_argument('--version', action='version', version='%(prog)s {}'.format(get_self_version('pyvpc')),
                        help='Print version and exit')

    # Define parses that is shared, and will be used as 'parent' parser to all others
    base_sub_parser = argparse.ArgumentParser(add_help=False)
    base_sub_parser.add_argument('--cidr-range', help='Check free ranges for current cidr', required=False)
    base_sub_parser.add_argument('--suggest-range', type=check_valid_ip_prefix, required=False,
                                 help='Return all available networks with input prefix (0-32)')
    base_sub_parser.add_argument('--num-of-addr', type=check_valid_ip_int, required=False,
                                 help='Return all available networks that contain at least addresses of num passed')
    base_sub_parser.add_argument('--output', choices=['json'], help='Return output as json', required=False)

    # Sub-parser for aws
    parser_aws = subparsers.add_parser('aws', parents=[base_sub_parser])
    parser_aws.add_argument('--region', required=False,
                            help='valid AWS region, if not selected will use default region configured')
    parser_aws.add_argument('--all-regions', action='store_true',
                            help='Run PyVPC on all AWS regions (app will run much longer)', required=False)
    parser_aws.add_argument('--vpc', required=False,
                            help='AWS VPC id or name, return available ranges is specific VPC')
    args = vars(parser.parse_args())

    if args['sub_command'] is None:
        parser.print_help()
        exit(0)

    if not args['cidr_range'] and not args['vpc']:
        print('--cidr-range or --vpc flags must be provided', file=stderr)
        exit(1)

    network = None
    try:
        if args['cidr_range']:
            network = PyVPCBlock(network=ipaddress.ip_network(args['cidr_range']))
        elif args['vpc']:
            network = get_aws_vpc_if_exists(args['vpc'], args['region'])
            if not network:  # In case no vpc found with input id/name
                print('no vpc found with id/name "{}" '.format(args['vpc']), file=stderr)
                exit(1)
    except ValueError as exc:
        print(exc, file=stderr)
        exit(1)

    if args['cidr_range']:
        # Get all not available (used) CIDRs
        reserved_cidrs = get_aws_reserved_networks(args['region'], args['all_regions'])
    # Case --vpc passed
    else:
        reserved_cidrs = get_aws_reserved_subnets(network.get_id())

    # Calculate available CIDRs based or input request
    pyvpc_objects = get_available_networks(network.get_network(), reserved_cidrs)

    # Case valid suggest-range OR num-of-addr passed
    if args['suggest_range'] is not None or args['num_of_addr'] is not None:
        suggested_net = []
        try:
            suggested_net = calculate_suggested_cidr(pyvpc_objects, args['suggest_range'], args['num_of_addr'])
        except ValueError as exc:
            print(exc)
            exit(1)
        if suggested_net:
            if args['output'] == 'json':
                print(return_pyvpc_objects_json(suggested_net))
            else:
                print(return_pyvpc_objects_string(suggested_net))
        else:
            print('no possible available ranges found for input values')
            exit(1)

    else:
        if args['output'] == 'json':
            print(return_pyvpc_objects_json(pyvpc_objects))
        else:
            print(return_pyvpc_objects_string(pyvpc_objects))


if __name__ == "__main__":
    main()
