#!/usr/bin/env python3

import json
import re
import os
import ipaddress
from copy import deepcopy
from sys import argv

def process_sshfp_records(path, filename, subdomain, zone, sshfp_algos, sshfp_fp_types):
    '''
    Converts bind records read from a file to records fitting to the role

    :param str path: The path to the folder containg the file
    :param str filename: filename of the file
    :param str subdomain: subdomain to append
    :param str zone: zone to append
    :param str[] sshfp_algos: List of allowed sshfp algorithms
    :param str[] sshfp_fp_types: List of allowed sshfp fingerprint types
    '''
    records = {}
    try:
        with open("{}/{}".format(path, filename), 'r') as fp:
            lines = fp.readlines()
            sshfp_records = []
            for line in lines:
                parts = line.split(' ')
                if sshfp_algos != [] and int(parts[3]) not in sshfp_algos:
                    continue
                if sshfp_fp_types != [] and int(parts[4]) not in sshfp_fp_types:
                    continue
                sshfp_records.append({"c": " ".join(parts[3:]).strip()})


        if len(sshfp_records) > 0:
            records = {"SSHFP": sshfp_records}
    except FileNotFoundError:
        pass

    return records

def mergeDict(a, b):
    '''
    Merges two dicts.
    If the key is present in both dicts, the key from the second dict is used.
    This goes unless the key contains a list or a dict.
    For dicts, this function is called recursively.
    For lists, the lists are appended.

    :param dict a: The dict to merge into
    :param dict b: The dict to merge into a, overriding with the rules specified above
    '''
    a = deepcopy(a)
    if not b:
        return a
    for key in b:
        if key in a:
            if isinstance(a[key], dict) and isinstance(b[key], dict):
                a[key] = mergeDict(a[key], b[key])
            elif isinstance(a[key], list) and isinstance(b[key], list):
                a[key] = a[key] + b[key]
            else:
                a[key] = b[key]
        else:
            a[key] = b[key]
    return a


def removeStringFromObject(obj, string_to_search, replace_string):
    '''
    Search and replace string in object.
    The search string can be a regex expression.

    :param object obj: The object to search
    :param str string_to_search: The string to search for, can be regex
    :param str replace_string: The string to replace a
    '''
    if isinstance(obj, dict):
        for key, value in obj.items():
            del(obj[key])
            key = re.sub(string_to_search, replace_string, key)
            obj[key] = removeStringFromObject(value, string_to_search, replace_string)
    elif isinstance(obj, list):
        for idx, value in enumerate(obj):
            obj[idx] = removeStringFromObject(value, string_to_search, replace_string)
    elif isinstance(obj, str):
        obj = re.sub(string_to_search, replace_string, obj)
    else:
        return obj
    return obj

if __name__ == "__main__":
    myHostname = argv[1]
    hostvars = json.loads(open(argv[2]).read())
    localhost = hostvars[myHostname]
    ret = {}
    if 'pdns_auth_api_zones' in hostvars[myHostname]:
        ret = hostvars[myHostname]['pdns_auth_api_zones']

    # Zone Clones
    if 'dns_facts_zone_clones' in localhost:
        for clone, origin in localhost['dns_facts_zone_clones'].items():
            origin_zone = deepcopy(ret[origin['zone']])
            if 'exclude_records' in origin:
                records_to_exclude = []
                for exclude_record in origin['exclude_records']:
                    for record in origin_zone['records'].keys():
                        if exclude_record in record:
                            records_to_exclude.append(record)
                for record in records_to_exclude:
                    del(origin_zone['records'][record])
            # Check if clone is already defined
            if clone not in ret:
                clone_zone = {}
            else:
                clone_zone = ret[clone]
            origin_zone = removeStringFromObject(origin_zone, origin['zone'] + '$', clone)
            new_zone = mergeDict(origin_zone, clone_zone)
            # Clone additional data
            for key in origin_zone.keys():
                if key not in [ 'records' ] + list(clone_zone.keys()):
                    new_zone[key] = origin_zone[key]
            # Set kind
            if 'kind' in new_zone:
                if new_zone['kind'] == 'Master-Template':
                    new_zone['kind'] = 'Master'
                elif new_zone['kind'] == 'Slave-Template':
                    new_zone['kind'] = 'Slave'
                else:
                    new_zone['kind'] = 'Native'
            else:
                new_zone['kind'] = 'Master'
            ret[clone] = new_zone

    # Remove DNS Templates
    if 'pdns_auth_api_zones' in localhost:
        to_remove = []
        for name,zone in ret.items():
            if 'kind' in zone and zone['kind'] in [ 'Master-Template', 'Slave-Template', 'Native-Template' ]:
                to_remove.append(name)
        for entry in to_remove:
            ret.pop(entry, None)

    # Values from hostvars
    if 'pdns_auth_api_zones' in localhost and 'dns_facts_forward_records' in localhost:
        for attr_item in localhost['dns_facts_forward_records']:
            attr = localhost['dns_facts_forward_records'][attr_item]['name']
            if 'ip' in localhost['dns_facts_forward_records'][attr_item]:
                ip = localhost['dns_facts_forward_records'][attr_item]['ip']
            else:
                ip = hostvars[host]['ansible_host']
            suffixes = localhost['dns_facts_forward_records'][attr_item]['suffix']
            for zone in ret:
                if ret[zone]['kind'] in ['Master', 'Native'] and zone in suffixes:
                    for host in hostvars:
                        if attr in hostvars[host]:
                            for record in attr:
                                if not record.endswith("."):
                                    ret[zone]['records'][record+"."+zone] = {"A": [{"c": ip}]}

    # Prefixes
    if 'dns_facts_prefix' in localhost:
        hosts = localhost['dns_facts_prefix']
        processed_zones = {}
        for zone in ret:
            processed_zones[zone] = {"records": {}}
            if 'records' not in ret[zone]:
                continue
            for name,contents in ret[zone]['records'].items():
                if 'A' not in contents:
                    continue
                for A in contents['A']:
                    if "c" not in A:
                        continue
                    for entryname,entrycontent in hosts.items():
                        if entryname != A['c']:
                            continue
                        for prefix in entrycontent:
                            record_name = prefix + '.' + name
                            if record_name not in ret[zone]['records'] and name[0:len(prefix)] != prefix:
                                processed_zones[zone]['records'][prefix + '.' + name] = {"A": [{"c": entryname}]}
        for zone in processed_zones:
            for key, value in processed_zones[zone]['records'].items():
                localhost['pdns_auth_api_zones'][zone]['records'][key] = value

    # Internal Records generation
    if 'dns_facts_internal_records' in localhost:
        if 'subdomain' in localhost['dns_facts_internal_records']:
            subdomain = localhost['dns_facts_internal_records']['subdomain']
        else:
            subdomain = ''
        if 'sshfp_algorithms' in localhost['dns_facts_internal_records']:
            sshfp_algos = localhost['dns_facts_internal_records']['sshfp_algorithms']
        else:
            sshfp_algos = []
        if 'sshfp_fp_types' in localhost['dns_facts_internal_records']:
            sshfp_fp_types = localhost['dns_facts_internal_records']['sshfp_fp_types']
        else:
            sshfp_fp_types = []
        generateSshfp = 'generate_sshfp' in localhost['dns_facts_internal_records'] and localhost['dns_facts_internal_records']['generate_sshfp']
        zone = localhost['dns_facts_internal_records']['zone']
        if zone in ret and 'records' in ret[zone]:
            records = ret[zone]['records']
            for host in hostvars.keys():
                record_name = "{}.{}.{}".format(host, subdomain, zone)
                if record_name not in records:
                    records[record_name] = {"A": [{"c": hostvars[host]['ansible_host']}]}
                    if generateSshfp:
                        records[record_name].update(process_sshfp_records(argv[3], host, subdomain, zone, sshfp_algos, sshfp_fp_types))

    # Generate statments
    if 'dns_facts_generate' in localhost:
        for zonename,zonecontents in localhost['dns_facts_generate'].items():
            if zonename not in ret:
                continue
            for generate,contents in zonecontents.items():
                start,end = generate.split('-')
                for i in range(int(start), int(end) + 1, 1):
                    new = deepcopy(contents)
                    for name,t in new.items():
                        for record in t:
                            if 'c' in record:
                                record['c'] = record['c'].replace('$', str(i))
                    ret[zonename]['records'][str(i) + '.' + zonename] = new

    # Reverse records
    if 'dns_facts_reverse_suffix' in localhost:
        internal_zone = localhost['dns_facts_reverse_suffix']
        for host in hostvars:
            # Collect IPs from host
            ips = [ hostvars[host]['ansible_host'] ]
            for var in [ 'interfaces', 'bridges' ]:
                if var in hostvars[host]:
                    for interface in hostvars[host][var]:
                        if 'ip' in interface:
                            ips += [ interface['ip'].split('/')[0] ]
            ips = list(set(ips))
            # Add records
            for raw_ip in ips:
                ip = ipaddress.IPv4Address(raw_ip)
                reverse = ip.reverse_pointer
                network_reverse = ".".join(str(reverse).split(".")[1:])
                # Unknown reverse zone?
                if network_reverse not in ret:
                    continue
                target_zone = ret[network_reverse]
                if 'records' not in target_zone:
                    target_zone['records'] = {};
                if reverse not in target_zone['records']:
                    target_zone['records'][reverse] = { "PTR": [ {"c": "{}.{}".format(host, internal_zone)} ] }

    # Secondaries
    if 'dns_facts_primary_servers' in localhost and 'dns_facts_secondary_name' in localhost:
        for hostname in localhost['dns_facts_primary_servers']:
            if hostname not in hostvars or 'pdns_auth_api_zones' not in hostvars[hostname]:
                continue
            for name,contents in hostvars[hostname]['pdns_auth_api_zones'].items():
                if 'kind' not in contents or contents['kind'] in ['Master', 'Native']:
                    for ns in contents['records'][name]['NS']:
                        if 'c' in ns and ns['c'] == localhost['dns_facts_secondary_name']:
                            ret[name] = {
                                'kind': 'Slave',
                                'masters': [hostvars[hostname]['ansible_host']]
                            }
                            break

    print(json.dumps(ret))

