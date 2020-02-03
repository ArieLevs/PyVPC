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
    | Lowest IP   | Upper IP       |   Num of Addr | Available   | ID                    | Name         |
    |-------------|----------------|---------------|-------------|-----------------------|--------------|
    | 10.0.0.0    | 10.19.255.255  |       1310720 | True        |                       |              |
    | 10.20.0.0   | 10.20.255.255  |         65536 | False       | vpc-Ec9hQfmjk4sPCH65c | lev-test-vpc |
    | 10.21.0.0   | 10.29.255.255  |        589824 | True        |                       |              |
    | 10.30.0.0   | 10.30.255.255  |         65536 | False       | vpc-4WNpVY5wCLmdqfJLy | dev-k8s      |
    | 10.31.0.0   | 10.255.255.255 |      14745600 | True        |                       |              |
    ```

*   For example, a VPC with `10.50.0.0/16` cidr, executing command:
    ```bash
    pyvpc aws --vpc vpc-3w5cymcdnwjm389gq
    ```
  
    will return:
    ```
    | Lowest IP   | Upper IP      |   Num of Addr | Available   | ID                       | Name               |
    |-------------|---------------|---------------|-------------|--------------------------|--------------------|
    | 10.50.0.0   | 10.50.0.255   |           256 | True        |                          |                    |
    | 10.50.1.0   | 10.50.1.255   |           256 | False       | subnet-p7s6f7rsgrgtvr5fe | private-arie-test  |
    | 10.50.2.0   | 10.50.2.255   |           256 | False       | subnet-2nw28z822kcr9x726 | private-arie-test  |
    | 10.50.3.0   | 10.50.10.255  |          2048 | True        |                          |                    |
    | 10.50.11.0  | 10.50.11.255  |           256 | False       | subnet-3j744kpzmcg55qtza | public-arie-test   |
    | 10.50.12.0  | 10.50.12.255  |           256 | False       | subnet-6vjape4vfk4jhajg8 | public-arie-test   |
    | 10.50.13.0  | 10.50.20.255  |          2048 | True        |                          |                    |
    | 10.50.21.0  | 10.50.21.255  |           256 | False       | subnet-j8wv89u4u3v4kyqs7 | database-arie-test |
    | 10.50.22.0  | 10.50.22.255  |           256 | False       | subnet-7p4djeetkkkgmqqqk | database-arie-test |
    | 10.50.23.0  | 10.50.255.255 |         59648 | True        |                          |                    |
    ```

### Suggest available networks:

For example we pass the `--cidr-range 10.0.0.0/12 --suggest-range 14` value,
on the first example (`10.20.0.0/16` and `10.30.0.0/16` are reserved).

the result will be:
```
| Lowest IP   | Upper IP      |   Num of Addr | Available   | ID   | Name   |
|-------------|---------------|---------------|-------------|------|--------|
| 10.0.0.0    | 10.3.255.255  |        262144 | True        |      |        |
| 10.4.0.0    | 10.7.255.255  |        262144 | True        |      |        |
| 10.8.0.0    | 10.11.255.255 |        262144 | True        |      |        |
| 10.12.0.0   | 10.15.255.255 |        262144 | True        |      |        |
```
  
Or if adding ` --cidr-range 10.0.0.0/10 --num-of-addr 100000`
(we need all available network that have at least hundred thousand addresses),
the result will be :
```
| Lowest IP   | Upper IP      |   Num of Addr | Available   | ID   | Name   |
|-------------|---------------|---------------|-------------|------|--------|
| 10.0.0.0    | 10.15.255.255 |       1048576 | True        |      |        |
| 10.16.0.0   | 10.19.255.255 |        262144 | True        |      |        |
| 10.22.0.0   | 10.23.255.255 |        131072 | True        |      |        |
| 10.24.0.0   | 10.27.255.255 |        262144 | True        |      |        |
| 10.28.0.0   | 10.29.255.255 |        131072 | True        |      |        |
| 10.32.0.0   | 10.63.255.255 |       2097152 | True        |      |        |
```
