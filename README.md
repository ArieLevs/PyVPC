PyVPC - CIDR free range resolver
=================================

[![](https://github.com/arielevs/pyvpc/workflows/Python%20package/badge.svg)](https://pypi.org/project/pyvpc/)
[![](https://img.shields.io/pypi/v/pyvpc.svg)](https://pypi.org/project/pyvpc/)
[![](https://img.shields.io/pypi/l/pyvpc.svg?colorB=blue)](https://pypi.org/project/pyvpc/)
[![](https://img.shields.io/pypi/pyversions/pyvpc.svg)](https://pypi.org/project/pyvpc/)

Get available CIDR/sub networks ranges from your cloud network,
This app will return all available networks that are not is use by a vpc, 
or sub network that are not is use inside a specific VPC. 

It can also suggest networks, according to flags passed to this app, 
view examples below.

* Current version supports only AWS VPCs.  


## Install
```bash
pip install pyvpc
```

## Usage
#### aws:
```
pyvpc aws [-h] [--cidr-range CIDR_RANGE]
          [--suggest-range {0-32}]
          [--num-of-addr NUM_OF_ADDR] [--output {json}]
          [--region REGION] [--all-regions] [--vpc VPC]
```

## Examples
*   Assuming there are two AWS VPCs with CIDRs: `10.20.0.0/16` and `10.30.0.0/16`,
    executing command: 
    ```bash
    pyvpc aws --cidr-range 10.0.0.0/8
    ```
    will return:
    ```
    | Lowest IP   | Upper IP       |   Num of Addr |   Prefix | Available   | ID                    | Name         |
    |-------------|----------------|---------------|----------|-------------|-----------------------|--------------|
    | 10.0.0.0    | 10.19.255.255  |       1310720 |          | True        |                       |              |
    | 10.20.0.0   | 10.20.255.255  |         65536 |       16 | False       | vpc-Ec9hQfmjk4sPCH65c | lev-test-vpc |
    | 10.21.0.0   | 10.29.255.255  |        589824 |          | True        |                       |              |
    | 10.30.0.0   | 10.30.255.255  |         65536 |       16 | False       | vpc-4WNpVY5wCLmdqfJLy | dev-k8s      |
    | 10.31.0.0   | 10.255.255.255 |      14745600 |          | True        |                       |              |
    ```

*   For example, a VPC with `10.50.0.0/16` cidr, executing command:
    ```bash
    pyvpc aws --vpc vpc-3w5cymcdnwjm389gq
    ```
  
    will return:
    ```
    | Lowest IP   | Upper IP      |   Num of Addr |   Prefix | Available   | ID                       | Name               |
    |-------------|---------------|---------------|----------|-------------|--------------------------|--------------------|
    | 10.50.0.0   | 10.50.63.255  |         16384 |          | True        |                          |                    |
    | 10.50.64.0  | 10.50.95.255  |          8192 |       19 | False       | subnet-0905d925dd4d240fb | private-arie-test  |
    | 10.50.96.0  | 10.50.127.255 |          8192 |       19 | False       | subnet-031a7b06bb1fbf991 | private-arie-test  |
    | 10.50.128.0 | 10.50.200.255 |         18688 |          | True        |                          |                    |
    | 10.50.201.0 | 10.50.201.255 |           256 |       24 | False       | subnet-09adedd87bec861e8 | public-arie-test   |
    | 10.50.202.0 | 10.50.202.255 |           256 |       24 | False       | subnet-0fcceff21a973dda2 | public-arie-test   |
    | 10.50.203.0 | 10.50.210.255 |          2048 |          | True        |                          |                    |
    | 10.50.211.0 | 10.50.211.255 |           256 |       24 | False       | subnet-0da43f86bc6f4c42f | database-arie-test |
    | 10.50.212.0 | 10.50.212.255 |           256 |       24 | False       | subnet-0a4c14480eb8189c5 | database-arie-test |
    | 10.50.213.0 | 10.50.255.255 |         11008 |          | True        |                          |                    |
    ```

### Suggest available networks:

For example we pass the `--cidr-range 10.0.0.0/12 --suggest-range 14` value,
on the first example (`10.20.0.0/16` and `10.30.0.0/16` are reserved).

the result will be:
```
| Lowest IP   | Upper IP      |   Num of Addr |   Prefix | Available   | ID   | Name   |
|-------------|---------------|---------------|----------|-------------|------|--------|
| 10.0.0.0    | 10.3.255.255  |        262144 |       14 | True        |      |        |
| 10.4.0.0    | 10.7.255.255  |        262144 |       14 | True        |      |        |
| 10.8.0.0    | 10.11.255.255 |        262144 |       14 | True        |      |        |
| 10.12.0.0   | 10.15.255.255 |        262144 |       14 | True        |      |        |
```
  
Or if adding ` --cidr-range 10.0.0.0/10 --num-of-addr 100000`
(we need all available network that have at least hundred thousand addresses),
the result will be :
```
| Lowest IP   | Upper IP      |   Num of Addr |   Prefix | Available   | ID   | Name   |
|-------------|---------------|---------------|----------|-------------|------|--------|
| 10.0.0.0    | 10.15.255.255 |       1048576 |       12 | True        |      |        |
| 10.16.0.0   | 10.19.255.255 |        262144 |       14 | True        |      |        |
| 10.22.0.0   | 10.23.255.255 |        131072 |       15 | True        |      |        |
| 10.24.0.0   | 10.27.255.255 |        262144 |       14 | True        |      |        |
| 10.28.0.0   | 10.29.255.255 |        131072 |       15 | True        |      |        |
| 10.32.0.0   | 10.63.255.255 |       2097152 |       11 | True        |      |        |
```
