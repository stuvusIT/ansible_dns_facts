#!/usr/bin/env python3

import json
import re
from sys import argv

if __name__ == "__main__":
    myHostname = argv[1]
    hostvars = json.loads(open(argv[2]).read())
    ret = []
    if 'pdns_auth_api_zones' in hostvars[myHostname]:
        ret = hostvars[myHostname]['pdns_auth_api_zones']

    # Secondaries
    if 'dns_facts_primary_servers' in hostvars[myHostname] and 'dns_facts_secondary_name' in hostvars[myHostname]:
        for hostname in hostvars[myHostname]['dns_facts_primary_servers']:
            if hostname not in hostvars or 'pdns_auth_api_zones' not in hostvars[hostname]:
                continue
            for zone in hostvars[hostname]['pdns_auth_api_zones']:
                if zone['kind'] in [ 'Master', 'Native' ]:
                    for ns in zone['records'][zone['name']]['NS']:
                        if 'c' in ns and ns['c'] == hostvars[myHostname]['dns_facts_secondary_name']:
                            ret.append({
                                'name': zone['name'],
                                'kind': 'Slave',
                                'masters': [ hostvars[hostname]['ansible_host'] ]
                            })
                            break

    print(json.dumps(ret))
