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

### Generate statments
This role supports generation statments like bind. The keyword is $GENERATE which is expanded everytime its encounterd.
The syntax is equal to the documented bind syntax but lhs and record_type are ignored since they are already known when a $GENERATE statment is encountered.

### Reverse records

Forward records are used to extract record generation from host vars

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
| `dns_facts_forward_records` | This is a dict that specifies settings for generating forward records from your ansible inventory. More information below.                                                                                                         |
| `dns_facts_reverse_records` | This is a dict that specifies settings for generating reverse records from your ansible inventory. More information below.                                                                                                         |

There is one variable that contains a default value. Its listed below and is only effective when `dns_facts_internal_records` is in use.

| Name                       | Required/Default | Description                                                                       |
|----------------------------|------------------|-----------------------------------------------------------------------------------|
| `dns_facts_generate_sshfp` | `true`           | Enable sshfp record collection from hosts and adding them to the internal records |

## `dns_facts_zone_clones`

| Name              | Required/Default   | Description                                                                                                      |
|-------------------|--------------------|------------------------------------------------------------------------------------------------------------------|
| `zone`            | :heavy_check_mark: | Servers that should be checked for zones this server should be secondary for                                     |
| `exclude_records` | `[]`               | List of records that should be excluded. If a subdomain is given every record of that subdomain will be excluded |

If a zone record `kind` is set to `Template` it will be removed during generation to allow definig template to clone.

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

## `dns_facts_reverse_records`

| Name           | Required/Default   | Description                                                           |
|----------------|--------------------|-----------------------------------------------------------------------|
| `zone`         | :heavy_check_mark: | Which zone should be used in the reverse zone. The zone hast to exist |
| `default_zone` | See below          | The default values to be used to generate a new zone.                 |

default for `default_zone`
```yml
{
kind: Master
soaEdit: INCEPTION-INCREMENT
defaultTTL: 3600
records: {}
}
```

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
  - pdns-auth-api-zones:
    ...
```

## License

This work is licensed under a [Creative Commons Attribution-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-sa/4.0/).

## Author Information

- [Janne Heß](https://github.com/dasJ)
- [Fritz Otlinghaus](https://github.com/scriptkiddi)
