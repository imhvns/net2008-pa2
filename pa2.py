# Name: Hans Saint-Preux
# Student ID: 041138403
# NET2008 Practical Assessment 2 - Fleet Compliance Auditor

# ---------- Imports ----------
import sys
import json
import yaml
import xml.etree.ElementTree as ET
from pathlib import Path


# ---------- Custom exception ----------
class AuditInputError(Exception):
    """Represent an input-file or policy error the program can report."""


# ---------- Device class ----------
class Device:
    """Represent one device that has an ID in the inventory."""

    def __init__(self, element):
        """Read the device details from its XML element."""
        self.id = element.get("id")
        self.role = element.get("role", "unknown")
        self.os_version = element.get("os")
        self.owner = element.findtext("owner")
        self.interfaces = element.findall("interface")

    def has_owner(self):
        """Return True when the device has a non-empty owner."""
        return bool(self.owner and self.owner.strip())

    def interface_status_counts(self):
        """Count this device's interfaces by status."""
        counts = {"up": 0, "down": 0, "other": 0}

        for interface in self.interfaces:
            status = interface.get("status")

            if status == "up":
                counts["up"] += 1
            elif status == "down":
                counts["down"] += 1
            else:
                counts["other"] += 1

        return counts


# ---------- Input-reading functions ----------
def read_inventory(xml_file):
    """Read the XML inventory and return its root element."""
    try:
        tree = ET.parse(xml_file)
    except (OSError, ET.ParseError) as error:
        raise AuditInputError(
            f"Error reading {xml_file.name}: {error}"
        ) from error

    return tree.getroot()


def read_policy(policy_file):
    """Read and validate the YAML policy mapping."""
    try:
        with open(policy_file, encoding="utf-8") as policy_stream:
            policy = yaml.safe_load(policy_stream)
    except (OSError, yaml.YAMLError) as error:
        raise AuditInputError(
            f"Error reading {policy_file.name}: {error}"
        ) from error

    # An empty YAML file is a valid empty policy.
    if policy is None:
        return {}

    if not isinstance(policy, dict):
        raise AuditInputError(
            f"Error reading {policy_file.name}: policy must be a YAML mapping"
        )

    if "min_os" in policy and not isinstance(policy["min_os"], dict):
        raise AuditInputError(
            f"Error reading {policy_file.name}: min_os must be a mapping"
        )

    if "require_owner" in policy and not isinstance(
        policy["require_owner"], bool
    ):
        raise AuditInputError(
            f"Error reading {policy_file.name}: require_owner must be true or false"
        )

    if "max_down_interfaces" in policy:
        limit = policy["max_down_interfaces"]
        if type(limit) is not int or limit < 0:
            raise AuditInputError(
                f"Error reading {policy_file.name}: "
                "max_down_interfaces must be a non-negative whole number"
            )

    return policy


# ---------- Version comparison ----------
def version_is_outdated(found, required):
    """Return True when found is numerically lower than required."""
    found_parts = [int(part) for part in found.split(".")]
    required_parts = [int(part) for part in required.split(".")]

    # Treat missing trailing parts as zero: 9.1 equals 9.1.0.
    width = max(len(found_parts), len(required_parts))
    found_parts += [0] * (width - len(found_parts))
    required_parts += [0] * (width - len(required_parts))

    return tuple(found_parts) < tuple(required_parts)


# ---------- Main program ----------
def main():
    """Read the files, audit devices, and write the JSON report."""

    # ---------- Command-line arguments ----------
    if len(sys.argv) != 3:
        print("usage: python pa2.py DEVICES.xml POLICY.yaml")
        return 2

    xml_file = Path(sys.argv[1])
    policy_file = Path(sys.argv[2])

    # ---------- Read input files ----------
    try:
        root = read_inventory(xml_file)
        policy = read_policy(policy_file)
    except AuditInputError as error:
        print(error)
        return 1

    # ---------- Initialize report data ----------
    kept = 0
    skipped = 0
    roles = {}
    interfaces = {"up": 0, "down": 0, "other": 0}
    violations = []
    kept_devices = []

    min_os = policy.get("min_os")
    require_owner = policy.get("require_owner", False)
    max_down = policy.get("max_down_interfaces")

    # ---------- Check each device ----------
    for element in root.findall("device"):
        device_id = element.get("id")

        if not device_id:
            skipped += 1
            continue

        device = Device(element)
        kept_devices.append(device)
        kept += 1

        roles[device.role] = roles.get(device.role, 0) + 1

        # Check owner when the policy includes that rule.
        if require_owner and not device.has_owner():
            violations.append({
                "device": device.id,
                "type": "missing_owner",
            })

        # Check allowed roles and OS versions when min_os is in the policy.
        if min_os is not None:
            if device.role not in min_os:
                violations.append({
                    "device": device.id,
                    "type": "unknown_role",
                    "role": device.role,
                })
            elif version_is_outdated(
                device.os_version,
                min_os[device.role],
            ):
                violations.append({
                    "device": device.id,
                    "type": "os_outdated",
                    "found": device.os_version,
                    "required": min_os[device.role],
                })

        # Count interfaces and check the per-device down limit.
        device_interfaces = device.interface_status_counts()

        for status in interfaces:
            interfaces[status] += device_interfaces[status]

        if max_down is not None and device_interfaces["down"] > max_down:
            violations.append({
                "device": device.id,
                "type": "too_many_down",
                "down": device_interfaces["down"],
            })

    # ---------- Find compliant devices ----------
    violating_ids = {violation["device"] for violation in violations}
    compliant = sorted(
        device.id
        for device in kept_devices
        if device.id not in violating_ids
    )

    # ---------- Build and write the report ----------
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

    # ---------- Print a short summary ----------
    print("Site:", root.get("site"))
    print("Kept devices:", kept)
    print("Skipped devices:", skipped)
    print("Roles:", roles)
    print("Interfaces:", interfaces)

    return 0


# ---------- Start the program ----------
if __name__ == "__main__":
    sys.exit(main())