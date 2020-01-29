PyVPC - CIDR free ranger resolver
=================================

[![](https://github.com/arielevs/pyvpc/workflows/Python%20package/badge.svg)](https://pypi.org/project/pyvpc/)
[![](https://img.shields.io/pypi/v/pyvpc.svg)](https://pypi.org/project/pyvpc/)
[![](https://img.shields.io/pypi/l/pyvpc.svg?colorB=blue)](https://pypi.org/project/pyvpc/)
[![](https://img.shields.io/pypi/pyversions/pyvpc.svg)](https://pypi.org/project/pyvpc/)

Current version supports only AWS VPCs.  
CIDR available range finder with sub networks

## Install
```bash
pip install pyvpc
```

## Usage
#### aws:
```bash
pyvpc aws [-h] --cidr-range CIDR_RANGE [--region REGION] [--all-regions]
```

## Examples
Assuming there are two AWS VPCs with CIDRs: `10.20.0.0/16` and `10.30.0.0/16`,
executing command: 
```bash
pyvpc aws --cidr-range 10.0.0.0/8
```
will return:
```
{'lower_ip': IPv4Address('10.0.0.0'), 'upper_ip': IPv4Address('10.19.255.255'), 'available': True}
{'lower_ip': IPv4Address('10.20.0.0'), 'upper_ip': IPv4Address('10.20.255.255'), 'available': False}
{'lower_ip': IPv4Address('10.21.0.0'), 'upper_ip': IPv4Address('10.29.255.255'), 'available': True}
{'lower_ip': IPv4Address('10.30.0.0'), 'upper_ip': IPv4Address('10.30.255.255'), 'available': False}
{'lower_ip': IPv4Address('10.31.0.0'), 'upper_ip': IPv4Address('10.255.255.255'), 'available': True}
```
