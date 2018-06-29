# dns-facts

This role generates facts for the [pdns-authoritative-api](https://github.com/stuvusIT/pdns-authoritative-api) role.
While this role is not required for the pdns-authoritative-api, it makes some things a lot easier.
It needs to be applied to the same host as the one pdns-authoritative-api is run before that.

### Secondary provisioning

When this role is applied to a server that should be secondary to another server, this role can automatically generate the Slave zones.
Each zone of the primary server is checked whether this server is found in the NS records of the zone, and if so, the Slave zone is created.
The name that is searched in the zone can be set, as well as the hosts which should be checked for Master (or Native) zones.

## Requirements

None

## Role Variables

All variables are optional.
If you don't want to use any features, you don't need to set any variables.

| Name                        | Description                                                                                                                                                                                                                         |
|-----------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `dns_facts_primary_servers` | Servers that should be checked for zones this server should be secondary for                                                                                                                                                        |
| `dns_facts_secondary_name`  | This host is selected as a secondary when this name is found as a NS of the primary                                                                                                                                                 |
| `dns_facts_zone_clones`     | This is a dict that specifies which zone attributes should be copied to a new zone. During this process each apperence of the old zone name is replaced with the new zone name. More information below.                             |
| `dns_facts_prefix`          | This is a dict that contains IP address as key and a list of prefixes as value. Those prefixes will lead to new records beeing gernerated for every record that has his A Record set to the key IP address. More information below. |

## `dns_facts_zone_clones`

| Name              | Required/Default   | Description                                                                                                      |
|-------------------|--------------------|------------------------------------------------------------------------------------------------------------------|
| `zone`            | :heavy_check_mark: | Servers that should be checked for zones this server should be secondary for                                     |
| `exclude_records` | `[]`               | List of records that should be excluded. If a subdomain is given every record of that subdomain will be excluded |

## `dns_facts_prefix`

The best explanation for the `dns_facts_prefix` is an example.


```yml
dns_facts_prefix:
  1.1.1.1:
    - www
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
  - pdns-auth-api-zones:
    ...
```

## License

This work is licensed under a [Creative Commons Attribution-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-sa/4.0/).

## Author Information

- [Janne Heß](https://github.com/dasJ)
