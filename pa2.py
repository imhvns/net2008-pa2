# Name: Hans Saint-Preux
# Student ID: 041138403
# NET2008 Practical Assessment 2 - Fleet Compliance Auditor

import sys
import json
import yaml
import xml.etree.ElementTree as ET
from pathlib import Path

def read_inventory(xml_file):
    """Read the XML inventory and return its root element."""
    tree = ET.parse(xml_file)
    return tree.getroot()

def read_policy(policy_file):
    """Read the YAML policy and return its contents."""
    with open(policy_file, encoding="utf-8") as policy_stream:
        return yaml.safe_load(policy_stream)
    
def main():
    """Read the inventory and print the IDs of kept devices."""
    if len(sys.argv) != 3:
        print("usage: python pa2.py DEVICES.xml POLICY.yaml")
        return 2

    xml_file = Path(sys.argv[1])
    policy_file = Path(sys.argv[2])

    try:
        root = read_inventory(xml_file)
        policy = read_policy(policy_file)
    except (OSError, ET.ParseError, yaml.YAMLError) as error:
        print (f"Error reading an input file: {error}")
        return 1

    print("Site:", root.get("site"))

    kept = 0
    skipped = 0
    roles = {}
    interfaces = {"up": 0, "down": 0, "other": 0}
    violations = []

    for device in root.findall("device"):
        device_id = device.get("id")

        if not device_id:
            skipped += 1
            continue
        kept += 1
        print(device_id)

        if policy.get("require_owner", False):
            owner = device.findtext("owner")

            if not owner or not owner.strip():
                violations.append({
                    "device": device_id,
                    "type": "missing_owner",
                })

        role = device.get("role", "unknown")
        roles[role] = roles.get(role, 0) + 1
        
        if "min_os" in policy and role not in policy["min_os"]:
            violations.append({
                "device": device_id,
                "type": "unknown_role",
                "role": role,
            })

        down_count = 0

        for interface in device.findall("interface"):
            status = interface.get("status")

            if status == "up":
                interfaces["up"] += 1
            elif status == "down":
                interfaces["down"] += 1
                down_count += 1
            else: 
                interfaces["other"] += 1
        
        if (
            "max_down_interfaces" in policy
            and down_count > policy["max_down_interfaces"]
        ):
            violations.append({
                "device": device_id,
                "type": "too_many_down",
                "down":  down_count,
            })

    print("Kept devices:", kept)
    print("Skipped devices:", skipped)
    print("Roles:", roles)
    print("Interfaces:", interfaces)

    report = {
        "site": root.get("site"),
        "total_devices": kept,
        "skipped_devices": skipped,
        "roles": roles,
        "interfaces": interfaces,
        "violations": violations,
        "compliant": [],
    }

    with open("audit.json", "w", encoding="utf-8") as report_file:
        json.dump(report, report_file, indent=2)

    return 0

if __name__ == "__main__":
    sys.exit(main())