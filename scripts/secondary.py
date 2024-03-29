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
            if 'kind' in contents and contents['kind'] == 'Slave':
                ret[name] = {
                    'kind': 'Slave',
                    'masters': contents['masters']
                    }
            else:
                for ns in contents['records'][name]['NS']:
                    if 'c' in ns and ns['c'] == localhost['dns_facts_secondary_name']:
                        ret[name] = {
                            'kind': 'Slave',
                            'masters': [hostvars[hostname]['dns_facts_dns_ipv4']]
                        }
                        break

    print(json.dumps(ret))
