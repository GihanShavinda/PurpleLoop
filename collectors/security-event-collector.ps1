# PurpleForge AI P3.3 - native Windows Security event collector (PowerShell 5.1)
# Run under the SAME user that created security-key.dat (user-scope DPAPI).
[CmdletBinding()]
param([switch]$Once, [ValidateRange(1,3600)][int]$PollSeconds=10, [ValidateRange(1,50)][int]$BatchSize=25)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$Root='C:\PurpleForge'
$KeyPath=Join-Path $Root 'config\security-key.dat'
$StatePath=Join-Path $Root 'config\security-checkpoint.json'
$LogPath=Join-Path $Root 'logs\security-collector.log'
$LogName='Security'
$Endpoint='https://192.168.37.1:8443/telemetry/ingest'
$Ids=@(4624,4625,4634,4672,4688,4720)
function Log([string]$Message) {
    $line='{0} {1}' -f [DateTime]::UtcNow.ToString('o'),$Message
    Add-Content -LiteralPath $LogPath -Value $line -Encoding UTF8
    Write-Host $line
}
function Load-Key {
    $encrypted=(Get-Content -LiteralPath $KeyPath -Raw).Trim()
    $secure=ConvertTo-SecureString $encrypted
    $ptr=[IntPtr]::Zero
    try {
        $ptr=[Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($ptr)
    } finally { if ($ptr -ne [IntPtr]::Zero) { [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($ptr) } }
}
function Save-Checkpoint([long]$RecordId) {
    $temp="$StatePath.tmp"
    @{record_id=$RecordId; saved_at=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json -Compress | Set-Content -LiteralPath $temp -Encoding UTF8
    Move-Item -LiteralPath $temp -Destination $StatePath -Force
}
function Get-Checkpoint {
    if (Test-Path -LiteralPath $StatePath) { return [long]((Get-Content -LiteralPath $StatePath -Raw | ConvertFrom-Json).record_id) }
    $latest=Get-WinEvent -LogName $LogName -MaxEvents 1 -ErrorAction SilentlyContinue
    $id=if ($null -eq $latest) { [long]0 } else { [long]$latest.RecordId }
    Save-Checkpoint $id
    Log "Initialized checkpoint at RecordId=$id (historical events skipped)."
    return $id
}
function Convert-Record($Record) {
    [xml]$xml=$Record.ToXml()
    $fields=@{}
    foreach($field in @($xml.Event.EventData.Data)) {
        if ($null -ne $field -and $field.Name) { $fields[[string]$field.Name]=[string]$field.'#text' }
    }
    $id=[int]$Record.Id
    $title=switch($id) { 4624 {'Successful logon'} 4625 {'Failed logon'} 4634 {'Logoff'} 4672 {'Special privileges assigned'} 4688 {'Process created'} 4720 {'User account created'} default {'Security event'} }
    $severity=if($id -in @(4625,4720)){'medium'}else{'info'}
    return @{
        event_time=$Record.TimeCreated.ToUniversalTime().ToString('o')
        event_type="windows.security.$id"
        severity=$severity
        message="Windows Security $title (Event ID $id) on $env:COMPUTERNAME"
        payload=@{
            hostname=$env:COMPUTERNAME
            channel=$LogName
            record_id=[long]$Record.RecordId
            event_id=$id
            provider=$Record.ProviderName
            data=$fields
        }
    }
}
function Send-Batch($Records) {
    $events=@($Records | ForEach-Object { Convert-Record $_ })
    $json=@{events=$events} | ConvertTo-Json -Depth 12 -Compress
    $bytes=[Text.Encoding]::UTF8.GetBytes($json)
    # Match backend's configured maximum; reserve overhead for encoding differences.
    if ($bytes.Length -gt 200000) { throw "Batch is too large ($($bytes.Length) bytes). Lower -BatchSize." }
    $key=Load-Key
    try {
        $response=Invoke-RestMethod -Uri $Endpoint -Method POST -ContentType 'application/json' -Headers @{'X-Collector-Key'=$key} -Body $bytes -TimeoutSec 30
        if ([int]$response.accepted -ne $events.Count) { throw "Only $($response.accepted) of $($events.Count) events accepted." }
    } finally { $key=$null }
    $last=[long]$Records[-1].RecordId
    Save-Checkpoint $last
    Log "Accepted $($events.Count) Security events; checkpoint=$last"
}
New-Item -ItemType Directory -Force -Path (Split-Path $StatePath),(Split-Path $LogPath) | Out-Null
[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12
$checkpoint=Get-Checkpoint
Log "Collector started as $([Security.Principal.WindowsIdentity]::GetCurrent().Name); checkpoint=$checkpoint"
do {
    try {
        # Read records in ascending RecordId order; advance across irrelevant IDs as well.
        $xpath="*[System[EventRecordID > $checkpoint]]"
        $records=@(Get-WinEvent -LogName $LogName -FilterXPath $xpath -Oldest -MaxEvents $BatchSize -ErrorAction Stop)
        if ($records.Count -gt 0) {
            $selected=@($records | Where-Object { $_.Id -in $Ids })
            if ($selected.Count -gt 0) {
                Send-Batch $selected
            }
            # Checkpoint only after successful submit; skip non-target event IDs.
            $lastRead=[long]$records[-1].RecordId
            if ($lastRead -gt $checkpoint) {
                Save-Checkpoint $lastRead
                $checkpoint=$lastRead
            }
        }
    } catch {
        if ($_.FullyQualifiedErrorId -like 'NoMatchingEventsFound*' -or $_.Exception.Message -like '*No events were found*') {
            # Normal idle state
        } else {
            Log "Collector retry; checkpoint unchanged: $($_.Exception.GetType().Name) $($_.Exception.Message)"
        }
    }
    if (-not $Once) { Start-Sleep -Seconds $PollSeconds }
} while (-not $Once)
