
class PyVPCBlock(object):
    network = None
    start_address = None
    end_address = None
    resource_id = None
    name = None
    resource_type = None
    num_of_addresses = 0
    block_available = False

    def __init__(self, network=None, start_address=None, end_address=None, resource_id=None,
                 name=None, resource_type=None, block_available=False):
        if network is None and (start_address is None or end_address is None):
            raise ValueError("network or start-end addresses should be provided")

        if network:
            self.network = network
            self.start_address = network.network_address
            self.end_address = network.broadcast_address
            self.num_of_addresses = network.num_addresses
        else:
            self.start_address = start_address
            self.end_address = end_address
            self.num_of_addresses = int(end_address) - int(start_address) + 1

        self.resource_id = resource_id
        self.name = name
        self.resource_type = resource_type
        self.block_available = block_available

    def get_id(self):
        return self.resource_id

    def get_name(self):
        return self.name

    def get_type(self):
        return self.resource_type

    def get_network(self):
        return self.network

    def get_start_address(self):
        return self.start_address

    def get_end_address(self):
        return self.end_address

    def get_num_addresses(self):
        return self.num_of_addresses


def print_pyvpc_objects_list(pyvpc_objects):
    """
    Documentation https://github.com/astanin/python-tabulate
    :param pyvpc_objects: list of PyVPCBlock
    :return: None
    """
    from tabulate import tabulate

    table = []
    # Prepare the table list, that contains lists of values
    for pyvpc_object in pyvpc_objects:
        table.append([pyvpc_object.get_start_address(), pyvpc_object.get_end_address(),
                      pyvpc_object.get_num_addresses(), pyvpc_object.block_available,
                      pyvpc_object.get_id(), pyvpc_object.get_name()])

    # Make sure headers are aligned with number of values is 'table'
    headers = ["Lowest IP", "Upper IP", "Num of Addr", "Available", "ID", "Name"]

    print(tabulate(table, headers, tablefmt="github"))
