# Name: Hans Saint-Preux
# Student ID: 041138403
# NET2008 Practical Assessment 2 - Fleet Compliance Auditor

import sys
import json
import xml.etree.ElementTree as ET
from pathlib import Path

def read_inventory(xml_file):
    """Read the XML inventory and return its root element."""
    tree = ET.parse(xml_file)
    return tree.getroot()

def main():
    """Read the inventory and print the IDs of kept devices."""
    if len(sys.argv) != 3:
        print("usage: python pa2.py DEVICES.xml POLICY.yaml")
        return 2

    xml_file = Path(sys.argv[1])

    try:
        root = read_inventory(xml_file)
    except (OSError, ET.ParseError) as error:
        print (f"Error reading {xml_file.name}: {error}")
        return 1

    print("Site:", root.get("site"))

    kept = 0
    skipped = 0
    roles = {}
    interfaces = {"up": 0, "down": 0, "other": 0}

    for device in root.findall("device"):
        device_id = device.get("id")

        if not device_id:
            skipped += 1
            continue
        kept += 1
        print(device_id)

        role = device.get("role", "unknown")
        roles[role] = roles.get(role, 0) + 1

        for interface in device.findall("interface"):
            status = interface.get("status")

            if status == "up":
                interfaces["up"] += 1
            elif status == "down":
                interfaces["down"] += 1
            else: 
                interfaces["other"] += 1

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
        "violations": [],
        "compliant": [],
    }

    with open("audit.json", "w", encoding="utf-8") as report_file:
        json.dump(report, report_file, indent=2)

    return 0

if __name__ == "__main__":
    sys.exit(main())