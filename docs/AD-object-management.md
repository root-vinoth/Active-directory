# Overview

This document covers how Active Directory objects — Organizational Units, Groups, and Users — are created and organized inside the `pekka.local` domain for this lab. The goal was to mirror a real company structure (departments and employees), so objects are built in order, since each layer depends on the one before it:

**OU → Group → User → Group Membership**

## Example Objects Used in This Guide

| Object | Example           | Path                           |
| ------ | ----------------- | ------------------------------- |
| OU     | `IT`              | `DC=pekka,DC=local`             |
| Group  | `IT-Team`         | `OU=Groups,DC=pekka,DC=local`   |
| User   | `jdoe` (John Doe) | `OU=IT,DC=pekka,DC=local`       |

# Organizational Units (OUs)

OUs represent departments in the company structure (e.g. IT, HR, Sales). They're created first since Groups and Users live inside them, and they let Group Policy and permissions be scoped to a specific department.

## Create an OU

```powershell
New-ADOrganizationalUnit `
-Name "IT" `
-Path "DC=pekka,DC=local"
```

Nested OU (e.g. a "Servers" OU inside "IT"):

```powershell
New-ADOrganizationalUnit `
-Name "Servers" `
-Path "OU=IT,DC=pekka,DC=local"
```

<!-- screenshot: new OU visible in Active Directory Users and Computers -->

## View OUs

```powershell
Get-ADOrganizationalUnit -Filter *
Get-ADOrganizationalUnit -Filter * | Select Name   # names only
```

Find one specific OU:

```powershell
Get-ADOrganizationalUnit -Filter 'Name -eq "IT"'
```

## Rename / Move an OU

```powershell
# Rename
Rename-ADObject `
-Identity "OU=IT,DC=pekka,DC=local" `
-NewName "IT-Department"

# Move
Move-ADObject `
-Identity "OU=Servers,OU=IT,DC=pekka,DC=local" `
-TargetPath "OU=Infrastructure,DC=pekka,DC=local"
```

## List Everything Inside an OU

```powershell
Get-ADUser `
-Filter * `
-SearchBase "OU=IT,DC=pekka,DC=local"

Get-ADGroup `
-Filter * `
-SearchBase "OU=IT,DC=pekka,DC=local"
```

## Delete an OU

OUs are protected from accidental deletion by default, so the protection has to be turned off first.

```powershell
Set-ADOrganizationalUnit `
-Identity "OU=IT,DC=pekka,DC=local" `
-ProtectedFromAccidentalDeletion $false

Remove-ADOrganizationalUnit -Identity "OU=IT,DC=pekka,DC=local"
```

# Groups

Groups organize users by function and are used to assign permissions. This lab uses Security groups with Global scope, created inside their relevant OU.

## Create a Group

```powershell
New-ADGroup `
-Name "IT-Team" `
-GroupScope Global `
-GroupCategory Security `
-Path "OU=Groups,DC=pekka,DC=local"
```

<!-- screenshot: IT-Team group created, showing scope/category -->

## View Groups

```powershell
Get-ADGroup -Filter *
Get-ADGroup -Filter * | Select Name   # names only
```

Check who's in a group:

```powershell
Get-ADGroupMember -Identity "IT-Team"
```

## Add a User to a Group

```powershell
Add-ADGroupMember `
-Identity "IT-Team" `
-Members jdoe
```

## Delete a Group

```powershell
Remove-ADGroup -Identity "IT-Team"
```

# Users

Users represent employee accounts. Each one is created inside its department OU, then added to the relevant group.

## Create a User

```powershell
New-ADUser `
-Name "John Doe" `
-GivenName "John" `
-SamAccountName "jdoe" `
-UserPrincipalName "jdoe@pekka.local" `
-Path "OU=IT,DC=pekka,DC=local" `
-AccountPassword (ConvertTo-SecureString "P@ssw0rd123" -AsPlainText -Force) `
-Enabled $true
```

<!-- screenshot: jdoe created, visible under OU=IT in ADUC -->

## View Users

```powershell
Get-ADUser -Filter *
Get-ADUser -Filter * | Select Name   # names only
```

Check which groups a user belongs to:

```powershell
Get-ADPrincipalGroupMembership jdoe
Get-ADPrincipalGroupMembership jdoe | Select Name   # names only
```

## Delete a User

```powershell
Remove-ADUser -Identity "jdoe"
```

# Verification

✔ OU structure created and visible in ADUC

✔ Groups created inside the correct OU

✔ Users created inside the correct OU

✔ Users successfully added to their group

✔ Group membership confirmed with `Get-ADPrincipalGroupMembership`
