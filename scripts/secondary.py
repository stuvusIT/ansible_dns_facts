#!/usr/bin/env python3

import json
from sys import argv

if __name__ == "__main__":
    myHostname = argv[1]
    hostvars = json.loads(open(argv[2]).read())
    localhost = hostvars[myHostname]
    ret = {}
    if 'pdns_auth_api_zones' in localhost:
        ret = hostvars[myHostname]['pdns_auth_api_zones']

    for hostname in localhost['dns_facts_primary_servers']:
        if hostname not in hostvars or 'pdns_auth_api_zones' not in hostvars[hostname]:
            continue
        for name,contents in hostvars[hostname]['pdns_auth_api_zones'].items():
            if ('kind' not in contents or contents['kind'] in ['Master', 'Native']) and name in contents['records']:
                for ns in contents['records'][name]['NS']:
                    if 'c' in ns and ns['c'] == localhost['dns_facts_secondary_name']:
                        ret[name] = {
                            'kind': 'Slave',
                            'masters': [hostvars[hostname]['ansible_host']]
                        }
                        break

    print(json.dumps(ret))
