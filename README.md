# dns-facts

This role generates facts for the [pdns-authoritative-api](https://github.com/stuvusIT/pdns-authoritative-api) role.
While this role is not required for the pdns-authoritative-api, it makes some things a lot easier.
It needs to be applied to the same host as the one pdns-authoritative-api is run before that.

### Secondary provisioning

When this role is applied to a server that should be secondary to another server, this role can automatically generate the Slave zones.
Each zone of the primary server is checked whether this server is found in the NS records of the zone, and if so, the Slave zone is created.
The name that is searched in the zone can be set, as well as the hosts which should be checked for Master (or Native) zones.

### Internal records

The internal records feature use the add records for every host in the inventory using the `inventory_name` as hostname and the `ansible_host` attribute for the ip address

### Forward records

Forward records are used to extract record generation from host vars

### Reverse records

Reverse records are automatically generated from `ansible_host` addresses and [network_management](https://github.com/stuvusIT/network_management) compatible IPs and bridges.
The reverse zones must exist with proper SOA and NS records.

## Requirements

None

## Role Variables

All variables are optional.
If you don't want to use any features, you don't need to set any variables.

| Name                         | Description                                                                                                                                                                                                                         |
|------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `dns_facts_primary_servers`  | Servers that should be checked for zones this server should be secondary for                                                                                                                                                        |
| `dns_facts_secondary_name`   | This host is selected as a secondary when this name is found as a NS of the primary                                                                                                                                                 |
| `dns_facts_zone_clones`      | This is a dict that specifies which zone attributes should be copied to a new zone. During this process each apperence of the old zone name is replaced with the new zone name. More information below.                             |
| `dns_facts_prefix`           | This is a dict that contains IP address as key and a list of prefixes as value. Those prefixes will lead to new records beeing gernerated for every record that has his A Record set to the key IP address. More information below. |
| `dns_facts_internal_records` | This is a dict that specifies settings for generating internal records from your ansible inventory. More information below.                                                                                                         |
| `dns_facts_forward_records`  | This is a dict that specifies settings for generating forward records from your ansible inventory. More information below.                                                                                                          |
| `dns_facts_reverse_suffix`   | Suffix to append to all reverse record PTR values.                                                                                                                                                                                  |
| `dns_facts_generate`         | Dict that specifies bind-like `$GENERATE` instructions. See below                                                                                                                                                                   |

There is one variable that contains a default value. Its listed below and is only effective when `dns_facts_internal_records` is in use.

| Name                       | Required/Default | Description                                                                       |
|----------------------------|------------------|-----------------------------------------------------------------------------------|
| `dns_facts_generate_sshfp` | `true`           | Enable sshfp record collection from hosts and adding them to the internal records |

## `dns_facts_zone_clones`

| Name              | Required/Default   | Description                                                                                                      |
|-------------------|--------------------|------------------------------------------------------------------------------------------------------------------|
| `zone`            | :heavy_check_mark: | Servers that should be checked for zones this server should be secondary for                                     |
| `exclude_records` | `[]`               | List of records that should be excluded. If a subdomain is given every record of that subdomain will be excluded |

All extra values (such as `dnssec`, or `soaEdit`) is copied, too.
If `kind` is set to `Master-Template`, `Slave-Template`, or `Native-Template`, the kind of the new zone is set accordingly and the source zone is removed during generation to allow definig template to clone.

## `dns_facts_prefix`

The best explanation for the `dns_facts_prefix` is an example.


```yml
dns_facts_prefix:
  1.1.1.1:
    - www
```

## `dns_facts_internal_records`

| Name                  | Required/Default   | Description                                                                       |
|-----------------------|--------------------|-----------------------------------------------------------------------------------|
| `subdomain_to_insert` | :heavy_check_mark: | Subdomain where the internal records should be added.                             |
| `domain`              | :heavy_check_mark: | Domain where the internal records belong to.                                      |

## `dns_facts_forward_records`

| Name     | Required/Default     | Description                                                    |
|----------|----------------------|----------------------------------------------------------------|
| `name`   | :heavy_check_mark:   | Name of the top level attribute to search for in the host vars |
| `ip`     | `{{ ansible_host }}` | Value of the ip address to set the record to.                  |
| `suffix` | :heavy_check_mark:   | List of domains where the record should be inserted            |

## `dns_facts_generate`

`dns_facts_generate` is a dict where the key is the name of the zone (which has to exist prior to record generation), and the value is another dict.
This nested dict has the range as key (e.g. `0-63` or `5-22`) and `pdns_auth_api_zones`-like contents (beginning with the type).
That means the content of the dict begins with e.g. `CNAME` and has `c` and `t` children.
`$` in `c` is replaced by the current number.

## Example Playbook

```yml
- hosts: dns
  roles:
  - dns-facts:
     dns_facts_zone_clones:
       example.com: 
         zone: example.de
     dns_facts_primary_servers:
       - dns01
     dns_facts_secondary_name: dns02.example.com.
     dns_facts_prefix:
       1.1.1.1:
         - www
     dns_facts_internal_records:
       subdomain_to_insert: int
       domain: example.de
     dns_facts_reverse_suffix: int.example.com.
     dns_facts_generate:
       0.168.192.in-addr.arpa:
         0-63:
           CNAME:
             - c: $.0-63.0.168.192.in-addr.arpa.

  - pdns-auth-api-zones:
    ...
```

## License

This work is licensed under a [Creative Commons Attribution-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-sa/4.0/).

## Author Information

- [Janne Heß](https://github.com/dasJ)
- [Fritz Otlinghaus](https://github.com/scriptkiddi)
