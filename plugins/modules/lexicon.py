#!/usr/bin/python
# -*- coding: utf-8 -*-
# Copyright (c) 2022 Ansible Project
# GNU General Public License v3.0+ (see COPYING or https://www.gnu.org/licenses/gpl-3.0.txt)

from __future__ import absolute_import, division, print_function
__metaclass__ = type

DOCUMENTATION = """
---
module:
author:
    - Sam Doran (@samdoran)
version_added: '2.12'
short_description: Configure DNS records using dns-lexicon
notes:
    - Requires dns-lexicon to be installed.

description:
    - Manage DNS records using DNS lexicon. Supports many DNS providers.
    - See U(https://dns-lexicon.readthedocs.io) for configuration and usage.
options:
    config_file:
      description:
        - >
          Configuration file used by C(lexicon). See
          U(https://dns-lexicon.readthedocs.io/en/latest/configuration_reference.html)
          for provider options.
        - Configuration options can also be set using environment variables formatted
          as C(LEXICON_{DNS Provider Name}_{Auth Type}).
        - The path to the configuration file must be on managed host, not the controle node.
      type: path

    provider:
      description: DNS provider.
      type: str
      required: yes

    domain:
      description: Domain to modify.
      type: str
      required: yes

    type:
      description: DNS record type.
      type: str
      choices: [A, AAAA, CNAME, MX, PTR, SRV, TXT]
      default: A

    name:
      description: DNS record.
      type: str
      required: yes

    content:
      description: DNS record value
      type: str
      required: yes
"""

EXAMPLES = """
"""

RETURN = """
"""

import pkgutil

from ansible.module_utils.basic import AnsibleModule

HAS_LEXICON = True
try:
    import lexicon.client
    import lexicon.config
    import lexicon.providers
except ImportError:
    HAS_LEXICON = False


def get_config(params):
    config = lexicon.config.ConfigResolver().with_env()
    if params.get("config_file"):
        config = config.with_config_file(params["config_file"])

    return config

def do_record(params):
    config = get_config(params)

    action_config = {
        "provider_name" : params["provider"],
        "action": params["action"],
        "domain": params["domain"],
        "type": params["type"],
        "name": params["name"],
        "content": params["content"],
    }

    optional = ["ttl", "priority", "identifier"]
    for item in optional:
        if params.get(item):
            action_config[item] = params[item]

    config.with_dict(action_config)
    try:
        result = lexicon.client.Client(config).execute()
    except Exception as e:
        result = f"Failed to update DNS: {e}"

    return result

def list_all_records(params):
    config = get_config(params)
    action_config = {
        "provider_name" : params["provider"],
        "action": "list",
        "domain": params["domain"],
        "type": params["type"],
    }
    config.with_dict(action_config)
    try:
        result = lexicon.client.Client(config).execute()
    except Exception as e:
        result = f"Failed to list DNS records: {e}"

    return result

def main():
    # In case lexicon fails to import, this needs to be set to something so the module
    # object can be created in order to report a failure gracefully.
    #
    # This has the potential to fail arg spec validation in the case of a missing import,
    # hiding the underlying issue.
    providers = ["azure", "cloudflare", "easydns", "route53"]
    if HAS_LEXICON:
        providers = [p.name for p in pkgutil.iter_modules(lexicon.providers.__path__)]

    module = AnsibleModule(
        argument_spec={
            "provider": {
                "required": True,
                "choices": providers,
            },
            "action": {
                "default": "create",
                "choices": ["create", "delete", "update"],
            },
            "domain": {
                "required": True,
            },
            "type": {
                "default": "A",
                "choices": [
                    "A",
                    "AAAA",
                    "CNAME",
                    "MX",
                    "PTR",
                    "SRV",
                    "TXT",
                ]
            },
            "config_file": {
                "type": "path",
            },
            "name": {
                "required": True,
            },
            "content": {
                "required": True,
            },
            "ttl": {
                "type": "int"
            },
            "identifier": {},
        },
    )

    if not HAS_LEXICON:
        module.fail_json("Missing required library 'dns-lexicon'.")

    dns_result = do_record(module.params)
    records = list_all_records(module.params)

    results = {}
    if isinstance(dns_result, str) and "Failed" in dns_result:
        results["failed"] = True

    results = {
        "dns_records": records,
        "changed": True,
    }

    module.exit_json(**results)

if __name__ == '__main__':
    main()
