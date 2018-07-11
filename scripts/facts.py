#!/usr/bin/env python3

import json
import re
import os
import ipaddress
from copy import deepcopy
from sys import argv

def process_sshfp_records(path, filename, subdomain, domain):
    with open("{}/{}".format(path, filename), 'r') as fp:
        lines = fp.readlines()
        sshfp_records = []
        for line in lines:
            sshfp_records.append({"c": " ".join(line.split(" ")[3:])})


    records = {"{}.{}.{}".format(filename, subdomain, domain):  {"SSHFP": sshfp_records}}
    return records

def bindGenerate(record_type, start, stop, lhs, rhs, step=1):
    '''
    Generates records for hostvars.
    See http://www.zytrax.com/books/dns/ch8/generate.html for a explenation
    This function does not support ttl or formating.

    :param str record_type: The record type to for the generated records
    :param int start: Start of the range that should be generated
    :param int stop: Stop of the range that should be generated. Causion should be used since this range includes the stop value instead of the python default of excluding it.
    :param str lhs: The left side of the record where $ in the string will be replaced by the current iteration number
    :param str rhs: The right side of the record where $ in the string will be replaced by the current iteration number
    :param int step: Step size for the range, default is 1
    '''
    records_bind_format = []
    records= []
    for i in range(start, stop + 1, step):
        lhs = lhs.replace("$", i)
        rhs = rhs.replace("$", i)
        #records_bind_format.append("{lhs} {record_type} {rhs}".format(lhs=lhs,record_type=record_type, rhs=rhs))
        records.append({ "c": rhs})
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
                mergeDict(a[key], b[key])
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
    ret = []
    if 'pdns_auth_api_zones' in hostvars[myHostname]:
        ret = hostvars[myHostname]['pdns_auth_api_zones']

# WWW prefix

    if 'dns_facts_prefix' in hostvars[myHostname]:
        localhost = hostvars[myHostname]
        hosts = localhost['dns_facts_prefix']
        processed_zones = {}
        for zone in localhost['pdns_auth_api_zones']:
            processed_zones[zone] = {"records": {}}
            if 'records' in localhost['pdns_auth_api_zones'][zone]:
                for record in localhost['pdns_auth_api_zones'][zone]['records']:
                    try:
                        for A in localhost['pdns_auth_api_zones'][zone]['records'][record]['A']:
                            if "c" in A:
                                for entry in hosts:
                                    prefixes = hosts[entry]

                                    if entry == A['c']:
                                        for prefix in prefixes:
                                            record_name = prefix + '.' + record
                                            if record_name not in localhost['pdns_auth_api_zones'][zone]['records'] \
                                                    and record[0:len(prefix)] != prefix:
                                                processed_zones[zone]['records'][prefix + '.' + record] = {"A": [{"c": entry}]}
                    except:
                        continue
        for zone in processed_zones:
            for key, value in processed_zones[zone]['records'].items():
                localhost['pdns_auth_api_zones'][zone]['records'][key] = value

    # Internal Records generation
    if 'dns_facts_internal_records' in hostvars[myHostname]:
        localhost = hostvars[myHostname]
        subdomain = localhost['dns_facts_internal_records']['subdomain_to_insert']
        domain = localhost['dns_facts_internal_records']['domain_append']
        sshfp_records = {}
        path_to_records = "/tmp/sshfp_records"
        for filename in os.listdir(path_to_records):
            sshfp_records.update(process_sshfp_records(path_to_records, filename, subdomain, domain))
        if 'pdns_auth_api_zones' in localhost and \
                domain in localhost['pdns_auth_api_zones'] and \
                localhost['pdns_auth_api_zones'][domain]['kind'] in\
                ['Master', 'Native']:
                    records = localhost['pdns_auth_api_zones'][domain]['records']
                    for host in hostvars:
                        record_name = "{}.{}.{}".format(hostvars[host]['inventory_hostname'], subdomain, domain)
                        if record_name not in records:
                            records[record_name] = {"A": [{"c": hostvars[host]['ansible_host']}]}
                            if record_name in sshfp_records:
                                records[record_name].update(sshfp_records[record_name])

    # Reading values from hostvars
    if 'pdns_auth_api_zones' in hostvars[myHostname] and 'dns_facts_forward_records' in hostvars[myHostname]:
        for attr_item in hostvars[myHostname]['dns_facts_forward_records']['attrs']:
            attr = hostvars[myHostname]['dns_facts_forward_records']['attrs'][attr_item]['name']
            if 'ip' in hostvars[myHostname]['dns_facts_forward_records']['attrs'][attr_item]:
                ip = hostvars[myHostname]['dns_facts_forward_records']['attrs'][attr_item]['ip']
            else:
                ip = hostvars[host]['ansible_host']
            suffixes = hostvars[myHostname]['dns_facts_forward_records']['suffix']
            for zone in ret:
                if ret[zone]['kind'] in ['Master', 'Native'] and zone in suffixes:
                    for host in hostvars:
                        if attr in hostvars[host]:
                            for record in attr:
                                if not record.endswith("."):
                                    ret[zone]['records'][record+"."+zone] = {"A": [{"c": ip}]}
    # Generate statments
    if 'pdns_auth_api_zones' in hostvars[myHostname]:
        for zone in ret:
            if 'records' not in ret[zone]:
                continue
            for record in ret[zone]['records']:
                for record_type in ret[zone]['records'][record]:
                    records_to_add = []
                    for entry in ret[zone]['records'][record][record_type]:
                        if "$GENERATE" in entry['c']:
                            start_stop, lhs, record_type_gen, rhs = entry['c'].split(" ")
                            start, stop = start_stop.split("-")
                            records_to_add += bind_generate(record_type, start, stop, record, rhs)
                    ret[zone]['records'][record][record_type] += records_to_add

    # Reverse records
    if 'dns_facts_reverse_records' in hostvars[myHostname]:
        internal_zone = hostvars[myHostname]['dns_facts_reverse_records']['zone']
        default_reverse_zone = hostvars[myHostname]['dns_facts_reverse_records']['default_zone']
        reverse_records = {}
        for host in hostvars:
            host_ip = ipaddress.IPv4Address(hostvars[host]['ansible_host'])
            host_ip_reverse = host_ip.reverse_pointer
            network_reverse = ".".join(str(host_ip.reverse_pointer).split(".")[1:])
            tmp_zone = deepcopy(default_reverse_zone)
            if network_reverse not in reverse_records:
                reverse_records[network_reverse] = tmp_zone
            reverse_records[network_reverse]['records'][host_ip_reverse] = { "CNAME": [ {"c": "{}.{}".format(hostvars[host]['inventory_hostname'], internal_zone)} ] }
        ret.update(reverse_records)

    # Zone Clones
    if 'dns_facts_zone_clones' in hostvars[myHostname]:
        for clone, origin in hostvars[myHostname]['dns_facts_zone_clones'].items():
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
            new_zone = mergeDict(origin_zone, clone_zone)
            new_zone = removeStringFromObject(new_zone, origin['zone'] + '$', clone)
            new_zone['kind'] = ['Master']
            ret[clone] = new_zone


    # DNS Templates
    if 'pdns_auth_api_zones' in hostvars[myHostname]:
        to_remove = []
        for zone in ret:
            if 'kind' in ret[zone] and ret[zone]['kind'] in ['Template']:
                to_remove.append(zone)
        for entry in to_remove:
            try:
                del(ret[zone])
            except KeyError:
                continue

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

