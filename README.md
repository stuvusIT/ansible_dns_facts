# dns_facts

This role generates facts for the [pdns-authoritative-api](https://github.com/stuvusIT/pdns-authoritative-api) role.
While this role is not required for the pdns-authoritative-api, it makes some things a lot easier.
It needs to be applied to the same host as the one pdns-authoritative-api is run before that.

### Secondary provisioning

When this role is applied to a server that should be secondary to another server, this role can automatically generate the Slave zones.
Each zone of the primary server is checked whether this server is found in the NS records of the zone, and if so, the Slave zone is created.
The name that is searched in the zone can be set, as well as the hosts which should be checked for Master (or Native) zones.

### Internal records

The internal records feature use the add records for every host in the inventory using the `inventory_name` as hostname and the `ansible_host` attribute for the ip address

### A/CNAME records

Each host can define a list of A records and CNAME records.
This keeps all host-relevant data at the same place (in its hostvars).

Just enable `dns_facts_generate_from_hostvars` on your DNS server and set `dns_facts_my_records` on servers that need A/CNAME records.
In the most simple case, this is just a list of A names.
If you want something more complex, you can use dicts with a `name` key (required) and an optional `ip` key (overriding the default IP which is `ansible_host`).
Another possible dict key is `cnames` which is supposed to point to a list of strings or dicts.
Each dict element must (again) have a `name` key and may optionally specify a `target` key to override the CNAME target (the trailing dot is automatically appended).
CNAME processing is recursive, so if you decide to have CNAMEs pointing to this CNAME, just specify `cnames` inside your CNAME.
This recursion can go to an abitrary depth.

### `reverseproxy`-compatibility

This role is fully compatible with the [reverse_proxy](https://github.com/stuvusIT/reverse_proxy) and [reverse_proxy_mklist](https://github.com/stuvusIT/reverse_proxy_mklist) roles.
This is accomplished by parsing the `served_domain` fact of all hosts.

Just set `dns_facts_reverse_proxies` to a list of hosts running the the two roles and the proper A records are automatically generated into the proper zones (if they exist).
Longer zone names are preferred over shorter ones.

### Reverse records

Reverse records are automatically generated from `ansible_host` addresses and [network_management](https://github.com/stuvusIT/network_management) compatible IPs and bridges.
The reverse zones must exist with proper SOA and NS records.

### Internal records

Records are automatically generated from the hostvars.
We call them internal records.
They are usually used in a subdomain where the search domain of your hosts point to.
This gives convenience, because you can use unqualified hostnames in your internal network (hence the name).

### MX record generation

The role can automatically generate MX records.
This is done by specifying a list of MX servers.
Each server specifies its own name and a list of names pointing to this name.

### SPF record generation
Sets a spf record on all domains with MX record.

### TXT autoquote

Just don't quote your TXT records, we'll take care of that.
Or do quote them.
We don't care.

## Requirements

None

## Role Variables

All variables are optional.
If you don't want to use any features, you don't need to set any variables.

| Name                               | Description                                                                                                                                                                                             |
|------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `dns_facts_dns_ipv4`               | The IPv4 address where this DNS server is reachable via TCP/UDP ports 53. This variable is required to set on primary servers that have at least one secondary.                                         |
| `dns_facts_primary_servers`        | Servers that should be checked for zones this server should be secondary for                                                                                                                            |
| `dns_facts_secondary_name`         | This host is selected as a secondary when this name is found as a NS of the primary                                                                                                                     |
| `dns_facts_zone_clones`            | This is a dict that specifies which zone attributes should be copied to a new zone. During this process each apperence of the old zone name is replaced with the new zone name. More information below. |
| `dns_facts_internal_records`       | This is a dict that specifies settings for generating internal records from your ansible inventory. More information below.                                                                             |
| `dns_facts_generate_from_hostvars` | Whether to enable the automatic `A`/`CNAME` generation from hostvars                                                                                                                                    |
| `dns_facts_reverse_suffix`         | Suffix to append to all reverse record PTR values.                                                                                                                                                      |
| `dns_facts_generate`               | Dict that specifies bind-like `$GENERATE` instructions. See below                                                                                                                                       |
| `dns_facts_reverse_proxies`        | List of reverseproxy hosts                                                                                                                                                                              |
| `dns_facts_mx_servers`             | List of MX hosts                                                                                                                                                                                        |

Non-DNS servers may also set these variables:

| Name                   | Default/Required | Description                                                                                                                |
|------------------------|:----------------:|----------------------------------------------------------------------------------------------------------------------------|
| `dns_facts_mx_my_name` |                  | Name of this server that is added to all MX records pointing to it                                                         |
| `dns_facts_mx_prio`    | `0`              | Default priority of MX records pointing to this server                                                                     |
| `dns_facts_mx_names`   | `[]`             | List of names pointing to this server. Each name may be a string or a dict consisting of a `name` field and a `prio` field |
| `dns_facts_my_records` | `[]`             | List of names or CNAMES pointing to this server. See the above section for more information                                |
| `dns_facts_spf_record` |                  | SPF record to be set on all domains with MX record                                                                         |


## `dns_facts_zone_clones`

| Name               | Required/Default   | Description                                                                                                      |
|--------------------|--------------------|------------------------------------------------------------------------------------------------------------------|
| `zone`             | :heavy_check_mark: | Servers that should be checked for zones this server should be secondary for                                     |
| `exclude_records`  | `[]`               | List of records that should be excluded. If a subdomain is given every record of that subdomain will be excluded |

All extra values (such as `dnssec`, or `soaEdit`) is copied, too.
If `kind` is set to `Master-Template`, `Slave-Template`, or `Native-Template`, the kind of the new zone is set accordingly and the source zone is removed during generation to allow definig template to clone.


## `dns_facts_internal_records`

| Name        | Required/Default   | Description                                                      |
|-------------|:------------------:|------------------------------------------------------------------|
| `zone`      | :heavy_check_mark: | Zone where the internal records are inserted in                  |
| `subdomain` |                    | Subdomain that is inserted between the hostname and the zonename |

## `dns_facts_generate`

`dns_facts_generate` is a dict where the key is the name of the zone (which has to exist prior to record generation), and the value is another dict.
This nested dict has the range as key (e.g. `0-63` or `5-22`) and `pdns_auth_api_zones`-like contents (beginning with the type).
That means the content of the dict begins with e.g. `CNAME` and has `c` and `t` children.
`$` in `c` is replaced by the current number.

## Example Playbook

The following example playbook assumes that you cloned this role to
`roles/dns_facts`
(i.e. the name of the role is `dns_facts` instead of `ansible_dns_facts`).

```yml
- hosts: dns
  roles:
  - dns_facts:
     dns_facts_zone_clones:
       example.com:
         zone: example.de
     dns_facts_primary_servers:
       - dns01
     dns_facts_secondary_name: dns02.example.com.
     dns_facts_internal_records:
       subdomain: int
       zone: example.de
     dns_facts_reverse_suffix: int.example.com.
     dns_facts_generate_from_hostvars: true
     dns_facts_generate:
       0.168.192.in-addr.arpa:
         0-63:
           CNAME:
             - c: $.0-63.0.168.192.in-addr.arpa.
     dns_facts_reverse_proxies:
       - reverseproxy01

  - pdns-auth-api-zones:
    ...
```

## License

This work is licensed under a [Creative Commons Attribution-ShareAlike 4.0 International License](https://creativecommons.org/licenses/by-sa/4.0/).

## Author Information

- [Janne Heß](https://github.com/dasJ)
- [Fritz Otlinghaus](https://github.com/scriptkiddi)
