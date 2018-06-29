#!/usr/bin/env python3

import json
import re
from copy import deepcopy
from sys import argv


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
                mergeDict(a[key], b[key])
            elif isinstance(a[key], list) and isinstance(b[key], list):
                a[key] = a[key] + b[key]
            else:
                a[key] = b[key]
        else:
            a[key] = b[key]


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
    ret = []
    if 'pdns_auth_api_zones' in hostvars[myHostname]:
        ret = hostvars[myHostname]['pdns_auth_api_zones']

    # Zone Clones
    if 'dns_facts_zone_clones' in hostvars[myHostname]:
        for clone, origin in hostvars[myHostname]['dns_facts_zone_clones'].items():
            origin_zone = deepcopy(hostvars[myHostname]['pdns_auth_api_zones'][origin['zone']])
            if 'exclude_records' in origin:
                records_to_exclude = []
                for exclude_record in origin['exclude_records']:
                    for record in origin_zone['records'].keys():
                        if exclude_record in record:
                            records_to_exclude.append(record)
                for record in records_to_exclude:
                    del(origin_zone['records'][record])
            # Check if clone is already defined
            if clone not in hostvars[myHostname]['pdns_auth_api_zones']:
                clone_zone = {}
            else:
                clone_zone = hostvars[myHostname]['pdns_auth_api_zones'][clone]
            new_zone = mergeDict(origin_zone, clone_zone)
            new_zone = removeStringFromObject(new_zone, origin['zone'] + '$', clone)
            hostvars[myHostname]['pdns_auth_api_zones'][clone] = new_zone

    # Internal Records generation
    if 'dns_facts_internal_records' in hostvars[myHostname]:
        localhost = hostvars[myHostname]
        subdomain = localhost['dns_facts_internal_records']['subdomain_to_insert']
        domain = localhost['dns_facts_internal_records']['domain_append']
        if 'pdns_auth_api_zones' in localhost and \
                domain in localhost['pdns_auth_api_zones'] and \
                localhost['pdns_auth_api_zones'][domain]['kind'] in\
                ['Master', 'Native']:
                    records = localhost['pdns_auth_api_zones'][domain]['records']
                    #print(records)
                    for host in hostvars:
                        record_name = hostvars[host]['inventory_hostname'] + subdomain + domain
                        if record_name not in records:
                            records[record_name] = {"A": [{"c": hostvars[host]['ansible_host']}]}

    # Secondaries
    if 'dns_facts_primary_servers' in hostvars[myHostname] and 'dns_facts_secondary_name' in hostvars[myHostname]:
        for hostname in hostvars[myHostname]['dns_facts_primary_servers']:
            if hostname not in hostvars or 'pdns_auth_api_zones' not in hostvars[hostname]:
                continue
            for zone in hostvars[hostname]['pdns_auth_api_zones']:
                if zone['kind'] in ['Master', 'Native']:
                    for ns in zone['records'][zone['name']]['NS']:
                        if 'c' in ns and ns['c'] == hostvars[myHostname]['dns_facts_secondary_name']:
                            ret.append({
                                'name': zone['name'],
                                'kind': 'Slave',
                                'masters': [hostvars[hostname]['ansible_host']]
                            })
                            break

    print(json.dumps(ret))

