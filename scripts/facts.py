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

def handleCnamesOfHost(primaryName, cnameConfig):
    '''
    Recursively builds a list of all CNAME records for the given host

    :param primaryName str: The main name of this host
    :param cnameConfig object: The CNAME configuration of the host
    '''

    # Simple CNAMEs
    if type(cnameConfig) is str:
        return { cnameConfig: { 'CNAME': [ primaryName + '.' ] } }
    # Custom Name/CNAMEs
    ret = {}
    name = cnameConfig['name']
    target = primaryName
    # Different target
    if 'target' in cnameConfig:
        target = cnameConfig['target']
    # CNAMEs
    if 'cnames' in cnameConfig:
        for cname in cnameConfig['cnames']:
            # Merge in this sub-CNAME
            ret = mergeDict(ret, handleCnamesOfHost(name, cname))
    # Merge in this CNAME
    ret = mergeDict(ret, { name: { 'CNAME': [ target + '.' ] } })
    return ret

if __name__ == "__main__":
    myHostname = argv[1]
    hostvars = json.loads(open(argv[2]).read())
    sshfp_directory = argv[3]
    localhost = hostvars[myHostname]
    ret = {}
    if 'pdns_auth_api_zones' in localhost:
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
                # Exclude 'records' and everything that is already set
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
    if 'dns_facts_generate_from_hostvars' in localhost and localhost['dns_facts_generate_from_hostvars']:
        new_records = {}
        for hostname,hostcontents in hostvars.items():
            if 'dns_facts_my_records' not in hostcontents:
                continue
            for nameOrConfig in hostcontents['dns_facts_my_records']:
                if type(nameOrConfig) is str:
                    # Simple name
                    name = nameOrConfig
                    ip = hostcontents['ansible_host']
                else:
                    # Dict with custom IP/CNAMEs
                    name = nameOrConfig['name']
                    # Custom IP
                    if 'ip' in nameOrConfig:
                        ip = nameOrConfig['ip']
                    else:
                        ip = hostcontents['ansible_host']
                    # CNAMEs
                    if 'cnames' in nameOrConfig:
                        for cname in nameOrConfig['cnames']:
                            # Add this CNAME
                            new_records = mergeDict(new_records, handleCnamesOfHost(name, cname))
                # Add the new A record
                new_records = mergeDict(new_records, { name: { 'A': [ ip ] } })
        # Add the new records
        for name, contents in new_records.items():
            # Try to find the proper zone
            zone = ''
            for zonename in ret.keys():
                # We need the zone with the longest common suffix
                if name.endswith(zonename) and len(zonename) > len(zone):
                    zone = zonename
            # Nothing found :/
            if zone == '':
                continue
            zone = ret[zone]
            if 'records' not in zone:
                zone['records'] = {}
            if name not in zone['records']:
                zone['records'][name] = {}
            name_in_zone = zone['records'][name]
            # Try to insert the records
            for rec_type, contents in contents.items():
                for content in contents:
                    if rec_type in name_in_zone:
                        found = False
                        for record in name_in_zone[rec_type]:
                            if 'c' in record and record['c'] == content:
                                found = True
                                break
                        if not found:
                            name_in_zone[rec_type].append({ 'c': content })
                    else:
                        name_in_zone[rec_type] = [{ 'c': content }]

    # Values from MX servers
    if 'dns_facts_mx_servers' in localhost:
        new_records = {}
        for server in localhost['dns_facts_mx_servers']:
            # Is this server valid?
            if 'dns_facts_mx_my_name' not in hostvars[server] or 'dns_facts_mx_names' not in hostvars[server]:
                continue
            # Default priority
            default_prio = 0
            if 'dns_facts_mx_prio' in hostvars[server]:
                default_prio = hostvars[server]['dns_facts_mx_prio']
            # Names
            for nameOrConfig in hostvars[server]['dns_facts_mx_names']:
                if type(nameOrConfig) is str:
                    name = nameOrConfig
                    prio = default_prio
                else:
                    name = nameOrConfig['name']
                    prio = nameOrConfig['prio']
                new_records[name] = str(prio) + ' ' + hostvars[server]['dns_facts_mx_my_name'] + '.'
        # Try to insert the new records
        for name,content in new_records.items():
            # Try to find the proper zone
            zone = ''
            for zonename in ret.keys():
                # We need the zone with the longest common suffix
                if name.endswith(zonename) and len(zonename) > len(zone):
                    zone = zonename
            # Nothing found :/
            if zone == '':
                continue
            # Can we insert the record?
            zone = ret[zone]
            if 'records' not in zone:
                zone['records'] = {
                    name: {
                        'MX': [
                            {
                                'c': content
                            }
                        ]
                    }
                }
            else:
                if name in zone['records'] and 'MX' in zone['records'][name]:
                    zone['records'][name]['MX'].append({ 'c': content })
                elif name in zone['records']:
                    zone['records'][name].update({
                        'MX': [
                            {
                                'c': content
                            }
                        ]
                    })
                else:
                    zone['records'][name] = {
                        'MX': [
                            {
                                'c': content
                            }
                        ]
                    }


    # Values from served domains
    if 'dns_facts_reverse_proxies' in localhost:
        new_records = {}
        for proxy in localhost['dns_facts_reverse_proxies']:
            prefixes = []
            suffixes = []
            ignoredHosts = []
            if 'domain_prefixes' in hostvars[proxy]:
                prefixes = hostvars[proxy]['domain_prefixes']
            if 'domain_suffixes' in hostvars[proxy]:
                suffixes = hostvars[proxy]['domain_suffixes']
            if 'ignore_hosts' in hostvars[proxy]:
                ignoredHosts = hostvars[proxy]['ignore_hosts']
            # Iterate over hosts
            for hostname,hostcontent in hostvars.items():
                if hostname in ignoredHosts or 'served_domains' not in hostcontent:
                    continue
                for domainblock in hostcontent['served_domains']:
                    # Skip this served domain
                    if 'reverse_proxy_skip' in domainblock and domainblock['reverse_proxy_skip']:
                        continue
                    if 'domains' not in domainblock:
                        continue
                    for domainname in domainblock['domains']:
                        if domainname.endswith('.'):
                            new_records[domainname] = hostvars[proxy]['ansible_host']
                        else:
                            for prefix in prefixes:
                                if prefix != '':
                                    prefix += '.'
                                for suffix in suffixes:
                                    if suffix != '':
                                        suffix = '.' + suffix
                                    new_records[prefix + domainname + suffix] = hostvars[proxy]['ansible_host']
        # Try to insert the new records
        for name,content in new_records.items():
            # Try to find the proper zone
            zone = ''
            for zonename in ret.keys():
                # We need the zone with the longest common suffix
                if name.endswith(zonename) and len(zonename) > len(zone):
                    zone = zonename
            # Nothing found :/
            if zone == '':
                continue
            # Can we insert the record?
            zone = ret[zone]
            if 'records' not in zone:
                zone['records'] = {
                    name: {
                        'A': [
                            {
                                'c': content
                            }
                        ]
                    }
                }
            else:
                if name in zone['records'] and 'A' in zone['records'][name]:
                    continue
                zone['records'][name] = {
                    'A': [
                        {
                            'c': content
                        }
                    ]
                }

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
                        records[record_name].update(process_sshfp_records(sshfp_directory, host, subdomain, zone, sshfp_algos, sshfp_fp_types))

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

    print(json.dumps(ret))

