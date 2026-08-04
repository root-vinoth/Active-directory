 # Overview

This document describes the network layout for the `pekka.local` lab: how the four VMs are connected, how they're addressed, DNS, and which ports carry AD authentication and Wazuh log traffic. Attack traffic (Kali → targets) is covered in the separate attack/mitigation file, not here.

# Topology

```text
              Host-Only Network — 192.168.56.0/24
     (AD authentication, Wazuh log forwarding, attack-sim traffic)

	    +---------------+---------------+---------------+
	    |               |               |               | 
	  DC01            WIN10            Kali            wazuh
	192.168.56.107     DHCP             DHCP        192.168.56.106
	 (static)                                         (static)
```

# Hosts & Addressing

| VM    | Role                    | Host-Only IP   | Assignment | Internet (NAT)                                                       |
| ----- | ----------------------- | -------------- | ---------- | --------------------------------------------------------------------- |
| DC01  | Domain Controller + DNS | 192.168.56.107 | Static     | Not needed — promoting a server to a DC doesn't require external downloads |
| WIN10 | Domain Client           | DHCP           | Dynamic    | Likely yes — needed to pull down Sysmon and the Wazuh agent installer  |
| Kali  | Attack Machine          | DHCP           | Dynamic    | Yes — confirmed, shows up as `10.0.2.15`                               |
| wazuh | Log Collector / SIEM    | 192.168.56.106 | Static     | Likely yes — needed to install the Wazuh manager packages              |

The "likely" rows are an assumption based on what each machine needed to download — worth a quick check in VirtualBox's adapter settings to confirm.

# DNS

DC01 runs the DNS Server role, installed automatically as part of `Install-ADDSForest`. It's authoritative for the `pekka.local` zone and points to itself as its primary DNS server. No custom records, zones, or forwarders — DNS is running on whatever Windows Server 2025 sets up by default.

# Ports & Protocols

| Traffic       | Port / Protocol | Purpose                        |
| ------------- | --------------- | ------------------------------ |
| WIN10 → DC01  | 53 (DNS)        | Locate the domain controller   |
| WIN10 → DC01  | 88 (Kerberos)   | Authentication                 |
| WIN10 → DC01  | 389 (LDAP)      | Directory lookups              |
| WIN10 → DC01  | 445 (SMB)       | Group Policy, file access      |
| WIN10 → wazuh | 1514/tcp        | Agent → manager log forwarding |

The first four are Windows' default behavior the moment a client joins and authenticates to a domain — nothing was manually configured for them. The Wazuh row is the one explicit choice made here: `WAZUH_MANAGER="192.168.56.106"` set during the agent install.

# Verification

✔ Host-Only network (192.168.56.0/24) reachable across all four VMs

✔ DC01 resolves `pekka.local` using itself as DNS

✔ WIN10 domain-joined and authenticating against DC01

✔ Wazuh agent on WIN10 forwarding logs to `192.168.56.106:1514`
