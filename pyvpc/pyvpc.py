import argparse
import ipaddress
from sys import stderr

import boto3
from pkg_resources import get_distribution, DistributionNotFound

from pyvpc_cidr_block import PyVPCBlock, print_pyvpc_objects_list


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

    parser.add_argument('--version', action='version',
                        version='%(prog)s {}'.format(get_self_version('pyvpc')),
                        help='Print version and exit')

    # Define parses that is shared, and will be used as 'parent' parser to all others
    base_sub_parser = argparse.ArgumentParser(add_help=False)
    base_sub_parser.add_argument('--cidr-range', help='Check free ranges in current cidr', required=False)

    # Sub-parser for aws
    parser_aws = subparsers.add_parser('aws', parents=[base_sub_parser])
    parser_aws.add_argument('--region',
                            help='valid AWS region, if not selected will use default region configured',
                            required=False)
    parser_aws.add_argument('--all-regions', action='store_true',
                            help='Run PyVPC on all AWS regions (app will run much longer)', required=False)
    parser_aws.add_argument('--vpc',
                            help='AWS VPC id or name, return available ranges is specific VPC',
                            required=False)
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
    print_pyvpc_objects_list(pyvpc_objects)


if __name__ == "__main__":
    main()
