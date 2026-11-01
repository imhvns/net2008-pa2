# Name: Hans Saint-Preux
# Student ID: 041138403
# NET2008 Practical Assessment 2 - Fleet Compliance Auditor

# ---------- Imports ----------
import sys
import json
import yaml
import xml.etree.ElementTree as ET
from pathlib import Path


# ---------- Input-reading functions ----------
def read_inventory(xml_file):
    """Read the XML inventory and return its root element."""
    tree = ET.parse(xml_file)
    return tree.getroot()


def read_policy(policy_file):
    """Read the YAML policy and return its contents."""
    with open(policy_file, encoding="utf-8") as policy_stream:
        return yaml.safe_load(policy_stream)


# ---------- Version comparison ----------
def version_is_outdated(found, required):
    """Return True when found is numerically lower than required."""
    found_parts = [int(part) for part in found.split(".")]
    required_parts = [int(part) for part in required.split(".")]

    width = max(len(found_parts), len(required_parts))
    found_parts += [0] * (width - len(found_parts))
    required_parts += [0] * (width - len(required_parts))

    return tuple(found_parts) < tuple(required_parts)


# ---------- Main program ----------
def main():
    """Read the input files, check devices, and write the audit report."""

    # ---------- Command-line arguments ----------
    if len(sys.argv) != 3:
        print("usage: python pa2.py DEVICES.xml POLICY.yaml")
        return 2

    xml_file = Path(sys.argv[1])
    policy_file = Path(sys.argv[2])

    # ---------- Read and validate the XML inventory ----------
    try:
        root = read_inventory(xml_file)
    except (OSError, ET.ParseError) as error:
        print(f"Error reading {xml_file.name}: {error}")
        return 1

    # ---------- Read and validate the YAML policy ----------
    try:
        policy = read_policy(policy_file)
    except (OSError, yaml.YAMLError) as error:
        print(f"Error reading {policy_file.name}: {error}")
        return 1

    # Treat an empty YAML file as an empty policy.
    if policy is None:
        policy = {}

    if not isinstance(policy, dict):
        print(f"Error reading {policy_file.name}: policy must be a YAML mapping")
        return 1

    # ---------- Initialize report counts ----------
    print("Site:", root.get("site"))

    kept = 0
    skipped = 0
    roles = {}
    interfaces = {"up": 0, "down": 0, "other": 0}
    violations = []

    # ---------- Check each device ----------
    for device in root.findall("device"):
        device_id = device.get("id")

        # Skip devices that do not have an ID.
        if not device_id:
            skipped += 1
            continue

        kept += 1
        print(device_id)

        # Check whether the device has an owner.
        if policy.get("require_owner", False):
            owner = device.findtext("owner")

            if not owner or not owner.strip():
                violations.append({
                    "device": device_id,
                    "type": "missing_owner",
                })

        # Count the device's role.
        role = device.get("role", "unknown")
        roles[role] = roles.get(role, 0) + 1

        # Check whether the role is allowed by the policy.
        min_os = policy.get("min_os", {})

        if "min_os" in policy and role not in min_os:
            violations.append({
                "device": device_id,
                "type": "unknown_role",
                "role": role,
            })

        # Check the OS version for roles listed in min_os.
        if role in min_os:
            found = device.get("os")
            required = min_os[role]

            if version_is_outdated(found, required):
                violations.append({
                    "device": device_id,
                    "type": "os_outdated",
                    "found": found,
                    "required": required,
                })

        # Count interface statuses and this device's down interfaces.
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

        # Check whether this device exceeds the down-interface limit.
        if (
            "max_down_interfaces" in policy
            and down_count > policy["max_down_interfaces"]
        ):
            violations.append({
                "device": device_id,
                "type": "too_many_down",
                "down": down_count,
            })

    # ---------- Find compliant devices ----------
    violating_ids = {violation["device"] for violation in violations}
    compliant = sorted(
        device.get("id")
        for device in root.findall("device")
        if device.get("id") and device.get("id") not in violating_ids
    )

    # ---------- Print summary ----------
    print("Kept devices:", kept)
    print("Skipped devices:", skipped)
    print("Roles:", roles)
    print("Interfaces:", interfaces)

    # ---------- Build and write JSON report ----------
    report = {
        "site": root.get("site"),
        "total_devices": kept,
        "skipped_devices": skipped,
        "roles": roles,
        "interfaces": interfaces,
        "violations": violations,
        "compliant": compliant,
    }

    with open("audit.json", "w", encoding="utf-8") as report_file:
        json.dump(report, report_file, indent=2)

    return 0


# ---------- Start the program ----------
if __name__ == "__main__":
    sys.exit(main())