param(
    [string]$SourceRoot = "",
    [string]$BackupRoot = "D:\OASIS_BACKUP",
    [int]$KeepCount = 20
)

$ErrorActionPreference = "Stop"

if ([string]::IsNullOrWhiteSpace($SourceRoot)) {
    $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
    $projectDir = Split-Path -Parent $scriptDir
    $SourceRoot = Split-Path -Parent $projectDir
}

if (-not (Test-Path $SourceRoot)) {
    throw "Source folder not found: $SourceRoot"
}

New-Item -ItemType Directory -Force -Path $BackupRoot | Out-Null
New-Item -ItemType Directory -Force -Path (Join-Path $BackupRoot "logs") | Out-Null

$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$destination = Join-Path $BackupRoot ("full_" + $timestamp)
$logPath = Join-Path $BackupRoot ("logs\\backup_" + $timestamp + ".log")

New-Item -ItemType Directory -Force -Path $destination | Out-Null

robocopy $SourceRoot $destination /E /R:2 /W:1 /XJ /Z /FFT /NP /NFL /NDL /LOG:$logPath | Out-Null
$robocopyExit = $LASTEXITCODE

if ($robocopyExit -ge 8) {
    throw "Backup failed. Robocopy exit code: $robocopyExit"
}

Set-Content -Path (Join-Path $BackupRoot "latest_backup.txt") -Value $destination -Encoding UTF8

$allBackups = Get-ChildItem -Path $BackupRoot -Directory | Where-Object { $_.Name -like "full_*" } | Sort-Object LastWriteTime -Descending
if ($allBackups.Count -gt $KeepCount) {
    $toDelete = $allBackups | Select-Object -Skip $KeepCount
    foreach ($old in $toDelete) {
        Remove-Item -Path $old.FullName -Recurse -Force -ErrorAction SilentlyContinue
    }
}

Write-Output "BACKUP_OK: $destination"
Write-Output "ROBOCOPY_EXIT: $robocopyExit"
