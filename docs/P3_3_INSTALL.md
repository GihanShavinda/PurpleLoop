# P3.3 Windows Security Event Collector — no Docker

This additive package installs a SECOND collector on the Windows 10 VMware guest `DESKTOP-5RPP763` (`192.168.37.128`). It does not modify the running Sysmon collector, P3 API, Angular application, PostgreSQL, Caddy, or the Ubuntu collector.

## Prerequisites
- Host: FastAPI on 127.0.0.1:8000, Caddy on 192.168.37.1:8443, PostgreSQL, Angular on 4200.
- Windows 10 VM: Caddy root CA already imported into `Cert:\LocalMachine\Root`; PowerShell 5.1; HTTPS test and `windows_event` source's key.
- Run commands BELOW **inside Windows 10 VM PowerShell as Administrator**, except the explicit Angular action.

## 1. Register a separate source in Angular (on host)
In Telemetry > Register native collector: Asset `DESKTOP-5RPP763`; type `windows_event`; name `Windows 10 Security Events P3.3`. Save the ONE-TIME key somewhere secure; do not share it. Do not reuse the Sysmon key.

## 2. Copy script to Windows 10
Transfer `collector/security-event-collector.ps1` from the ZIP to `C:\PurpleForge\collector\security-event-collector.ps1` using your trusted VMware file-transfer method.

```powershell
Test-Path 'C:\PurpleForge\collector\security-event-collector.ps1'
Get-WinEvent -ListLog Security | Select-Object LogName,IsEnabled,RecordCount
Get-WinEvent -LogName Security -MaxEvents 1 | Select-Object TimeCreated,RecordId,Id
Test-NetConnection 192.168.37.1 -Port 8443
```

## 3. Encrypt the NEW collector key under Gihan's logon
Use SAME logged-on user that will run the scheduled task.

```powershell
$secureKey = Read-Host 'Enter NEW P3.3 windows_event collector key' -AsSecureString
$secureKey | ConvertFrom-SecureString | Set-Content 'C:\PurpleForge\config\security-key.dat'
Remove-Variable secureKey
icacls 'C:\PurpleForge\config\security-key.dat' /inheritance:r
icacls 'C:\PurpleForge\config\security-key.dat' /grant:r "$($env:USERNAME):(R)"
```

## 4. Verify Security log reading and local auditing

```powershell
Get-WinEvent -LogName Security -MaxEvents 5 | Select-Object TimeCreated,RecordId,Id
# View existing local audit policy (read-only):
auditpol /get /category:*
```

Security 4624/4625 are normally enabled but depend on policy. Do not blindly change all auditing settings. If 4688 events are wanted, review your OS privacy/security policy and enable only the necessary process creation subcategory, optionally with command lines; those command lines can contain sensitive information.

## 5. First run: initialize checkpoint (no historical flood)
Stop no existing Sysmon tasks. This script is a separate process with a separate key/checkpoint.

```powershell
Unblock-File 'C:\PurpleForge\collector\security-event-collector.ps1'
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'C:\PurpleForge\collector\security-event-collector.ps1' -Once
Get-Content 'C:\PurpleForge\config\security-checkpoint.json'
```

## 6. Generate harmless new security event
Lock then unlock Windows or sign out/in to generate logon-related records; an RDP logon also creates events if configured. Avoid trying deliberately incorrect passwords. The test also forwards other configured IDs if they occur naturally.

```powershell
Get-WinEvent -LogName Security -MaxEvents 10 | Select-Object TimeCreated,RecordId,Id
powershell.exe -NoProfile -ExecutionPolicy Bypass -File 'C:\PurpleForge\collector\security-event-collector.ps1' -Once
Get-Content 'C:\PurpleForge\logs\security-collector.log' -Tail 15
```

Open Angular > Telemetry and check source `Windows 10 Security Events P3.3` for `windows.security.4624`, `.4634` etc. It remains `Configured` until one eligible event is accepted.

## 7. Enable continuous scheduled task after manual acceptance
This runs at user logon in the SAME account that encrypted the key, and runs continuously.

```powershell
$taskName='PurpleForge Security Event Collector'
$action=New-ScheduledTaskAction -Execute 'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe' -Argument '-NoProfile -ExecutionPolicy Bypass -File "C:\PurpleForge\collector\security-event-collector.ps1"'
$trigger=New-ScheduledTaskTrigger -AtLogOn -User "$env:USERDOMAIN\$env:USERNAME"
$principal=New-ScheduledTaskPrincipal -UserId "$env:USERDOMAIN\$env:USERNAME" -LogonType Interactive -RunLevel Highest
$settings=New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Seconds 0) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew
Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Description 'Native PurpleForge Windows Security event collector'
Start-ScheduledTask -TaskName $taskName
Get-ScheduledTask -TaskName $taskName | Select-Object TaskName,State
Get-Content 'C:\PurpleForge\logs\security-collector.log' -Tail 15
```

Do not run a manual continuous instance and scheduled instance simultaneously.

## Troubleshooting

```powershell
Get-ScheduledTaskInfo -TaskName 'PurpleForge Security Event Collector' | Select-Object LastRunTime,LastTaskResult
Get-Content 'C:\PurpleForge\logs\security-collector.log' -Tail 30
Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object CommandLine -like '*security-event-collector.ps1*' | Select-Object ProcessId,CommandLine
```

- `401`: Use the ONE-TIME API key generated for the enabled `windows_event` source; verify it has not been replaced or exposed.
- TLS failure: Verify trust store, Caddy process, lab firewall and address; never disable certificate verification.
- `Access denied`: Run as administrator/same DPAPI logon user. Do not switch to SYSTEM with this user's encrypted key.
- `No events`: Confirm Security event auditing and that matching Event IDs are being generated. A configured source without new eligible events may not show `Receiving`.
- If no event is accepted yet, the checkpoint should reflect locally read records; this isn't proof of backend ingestion.

## Caveats
- Events can contain usernames, workstation names, and command lines. Keep the VMnet1 lab isolated, restrict dashboard roles and use retention controls later.
- Best-effort at-least-once forwarding: a lost response after server commit can produce duplicates. Add idempotency using source+record ID in a later backend milestone.
- Only ID 4624,4625,4634,4672,4688,4720 are forwarded. Other Security IDs are skipped.
- This collector doesn't install Sysmon, modify audit policy, or enable automatic remediation.
