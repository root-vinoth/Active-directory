# 🛡️ pekka.local — Active Directory Attack & Detection Lab

A self-built Active Directory environment — compromised, monitored, and documented end to end.

![Windows Server](https://img.shields.io/badge/Windows_Server-2025-0078D6) ![Kali Linux](https://img.shields.io/badge/Kali_Linux-2026.2-557C94) ![Wazuh](https://img.shields.io/badge/Wazuh-4.14.3-3AB7E6) ![VirtualBox](https://img.shields.io/badge/VirtualBox-7.2.2-183A61) ![Type](https://img.shields.io/badge/type-home_lab-informational)

## Overview

This repo documents a home lab built to practice Active Directory offense and defense in a realistic, self-contained environment. The domain (`pekka.local`), its users and groups, and the SIEM watching over it were all built from scratch, then attacked with the same techniques used against real-world AD environments.

Each write-up follows the same shape — objective, lab setup, attack steps, the Windows events it generates, MITRE ATT&CK mapping, and defensive recommendations where relevant.

## Architecture

```
Host-Only Network — 192.168.56.0/24

+----------+----------+----------+----------+
|   DC01   |  WIN10   |   Kali   |  wazuh   |
|  DC+DNS  |  Client  | Attacker |   SIEM   |
+----------+----------+----------+----------+
```

Full IP addressing, DNS, and port/protocol breakdown → [`docs/Network-topology.md`](docs/Network-topology.md)

## Lab Environment

|VM|Role|OS|CPU|RAM|Disk|
|---|---|---|---|---|---|
|**DC01**|Domain Controller + DNS|Windows Server 2025|4|4 GB|80 GB|
|**WIN10**|Domain Client|Windows 10 Pro|2|2.5 GB|40 GB|
|**KALI**|Attack Machine|Kali Linux 2026.2|2|4 GB|40 GB|
|**wazuh**|Log Collector / SIEM|Wazuh 4.14.3|2|3 GB|20 GB|

Hypervisor: VirtualBox 7.2.2. Full build steps — AD DS promotion, domain join, Wazuh agent + Sysmon install → [`docs/Lab-setup.md`](docs/Lab-setup.md)

## Repository Structure

```
.
├── docs/
│   ├── Lab-setup.md
│   ├── AD-object-management.md
│   └── Network-topology.md
│
└── attacks/
    ├── LLMNR-Poisoning.md
    ├── Brut-Force.md
    ├── Dns-Zone-transfer.md
    ├── smb-share-access.md
    ├── Kerberoasting.md
    ├── Silver-ticket.md
    └── Golden-ticket.md
```

## 📚 Documentation

| Page                                                 | Description                                                                                                                                            |
| ---------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| [Lab Setup](docs/Lab-setup.md)                       | Building the environment from bare VMs — including the Windows 10 Home → Pro edition workaround, AD DS promotion, and Wazuh agent + Sysmon deployment. |
| [AD Object Management](docs/AD-object-management.md) | Creating and organizing OUs, Groups, and Users with PowerShell.                                                                                        |
| [Network Topology](docs/Network-topology.md)         | IP addressing, DNS, and the ports/protocols behind AD auth and log forwarding.                                                                         |

## ⚔️ Attack Simulations

| Attack                                                   | MITRE ID              | Summary                                                                                          |
| -------------------------------------------------------- | --------------------- | ------------------------------------------------------------------------------------------------ |
| [LLMNR Poisoning](attacks/LLMNR-Poisoning.md)            | T1557.001             | Spoofing LLMNR broadcasts with Responder to capture and crack NTLM hashes.                       |
| [Brute Force / Password Spraying](attacks/Brut-Force.md) | T1110.003             | Spraying one password across a domain user list over SMB and LDAP with NetExec.                  |
| [DNS Zone Transfer](attacks/Dns-Zone-transfer.md)        | T1590.001             | Testing whether the DC's DNS server allows unauthorized AXFR transfers (it doesn't, by default). |
| [SMB Share Access](attacks/smb-share-access.md)          | T1039 / T1021.002     | Baselining legitimate SMB share access and writing a custom Wazuh rule to detect it.             |
| [Kerberoasting](attacks/Kerberoasting.md)                | T1558.003             | Requesting SPN service tickets and cracking them offline with Hashcat.                           |
| [Silver Ticket](attacks/Silver-ticket.md)                | T1558.002             | Forging a service-specific TGS ticket from a cracked service account key.                        |
| [Golden Ticket](attacks/Golden-ticket.md)                | T1003.006 / T1558.001 | Dumping `krbtgt` via DCSync and forging a domain-wide TGT for full domain compromise.            |

## 🔗 Attack Path

Roughly how the attacks chain together, from first touch to full domain compromise:

1. **Recon** — [DNS Zone Transfer](attacks/Dns-Zone-transfer.md) attempt, blocked by default DNS hardening
2. **Credential capture** — [LLMNR Poisoning](attacks/LLMNR-Poisoning.md) and [Password Spraying](https://claude.ai/chat/attacks/Brut-Force.md) get a foothold
3. **Credential access** — [Kerberoasting](attacks/Kerberoasting.md) cracks a service account's password offline
4. **Escalation** — that key forges a [Silver Ticket](attacks/Silver-ticket.md) for one service, while DCSync-ing `krbtgt` forges a [Golden Ticket](attacks/Golden-ticket.md) for the whole domain

## 🛡️ Detection & Monitoring

Every host forwards logs to Wazuh (`192.168.56.106:1514`), with Sysmon adding process, network, and file-creation telemetry from the Windows endpoints. SMB share access has a custom Wazuh detection rule (see that write-up); brute force activity is caught with Wazuh's built-in authentication rules.

|Event ID|Meaning|Seen In|
|---|---|---|
|4624|Successful logon|Password Spraying, SMB Share Access|
|4625|Failed logon|Password Spraying|
|4634|Logoff|Password Spraying, SMB Share Access|
|4662|Operation performed on an object|Golden Ticket (DCSync detection)|
|4672|Special privileges assigned to new logon|Golden Ticket, Silver Ticket|
|4769|Kerberos service ticket requested|Kerberoasting, Silver Ticket|
|5140|Network share object accessed|SMB Share Access|

## 🎯 MITRE ATT&CK Coverage

|Tactic|Technique|
|---|---|
|Reconnaissance|T1590.001 – Gather Victim Network Information: DNS|
|Credential Access|T1110 – Brute Force _(.001 Password Guessing, .002 Password Cracking, .003 Password Spraying, .004 Credential Stuffing)_|
|Credential Access|T1003.006 – OS Credential Dumping: DCSync|
|Credential Access|T1558 – Steal or Forge Kerberos Tickets _(.001 Golden Ticket, .002 Silver Ticket, .003 Kerberoasting)_|
|Credential Access|T1557.001 – LLMNR/NBT-NS Poisoning|
|Credential Access|T1040 – Network Sniffing|
|Discovery|T1087.002 – Account Discovery: Domain Account|
|Collection|T1039 – Data from Network Shared Drive|
|Lateral Movement|T1021.002 – SMB/Windows Admin Shares|
|Persistence / Privilege Escalation|T1078.002 – Valid Accounts: Domain Accounts|

## 🧰 Tools Used

|Tool|Used For|
|---|---|
|**Impacket**|`secretsdump`, `ticketer`, `GetUserSPNs`, `lookupsid`, `psexec`, `mssqlclient`|
|**NetExec / CrackMapExec**|SMB & LDAP password spraying, auth verification|
|**Responder**|LLMNR/NBT-NS poisoning|
|**Hashcat**|Offline hash cracking (NTLM, Kerberos TGS-REP)|
|**Wireshark**|Packet capture and traffic verification|
|**Wazuh + Sysmon**|Log collection, telemetry, custom detection rules|

## 🧠 Skills Demonstrated

- Active Directory administration via PowerShell (OU / Group / User lifecycle)
- Windows Server AD DS deployment and forest promotion
- Kerberos attack tradecraft — Kerberoasting, Silver Ticket, Golden Ticket
- Credential access techniques — LLMNR poisoning, password spraying
- SIEM engineering — Wazuh + Sysmon deployment, custom rule authoring
- Windows Security Event Log analysis
- MITRE ATT&CK-based threat documentation

## ⚠️ Disclaimer

Every attack in this repo was run against machines built specifically for this lab, isolated on a host-only virtual network with no route to production systems. This is educational documentation only — don't run these techniques against systems you don't own or don't have explicit permission to test.