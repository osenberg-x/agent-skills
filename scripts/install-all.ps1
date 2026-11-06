<#
.SYNOPSIS
    Link this repo's skills into every known agent skills directory on this machine.

.DESCRIPTION
    Scans %USERPROFILE% for <agent>/skills and <agent>/<sub>/skills, then creates
    a directory junction for each skill. The source stays in the repo - nothing is copied.

    Skips plugin caches (connectors, marketplace) and nested skills/skills, which are
    not skill load points and would either be wiped by the tool or cause recursion.

    Pure ASCII on purpose: PowerShell 5.1 reads .ps1 as ANSI unless it has a BOM,
    so non-ASCII literals break quoting on non-UTF8 systems.

.PARAMETER Name
    Only handle these skills. Defaults to every top-level dir containing SKILL.md.

.PARAMETER Uninstall
    Remove the junctions. Leaves the repo and everything else untouched.

.PARAMETER DryRun
    Print what would happen without changing anything.

.EXAMPLE
    .\install-all.ps1 -DryRun
    .\install-all.ps1
    .\install-all.ps1 -Name de-jargon
    .\install-all.ps1 -Uninstall
#>
param(
    [string[]]$Name = @(),
    [switch]$Uninstall,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$repo = Split-Path -Parent $PSScriptRoot
$usr = $env:USERPROFILE

$skills = if ($Name.Count -gt 0) {
    $Name
} else {
    Get-ChildItem $repo -Directory |
        Where-Object { Test-Path (Join-Path $_.FullName "SKILL.md") } |
        ForEach-Object { $_.Name }
}

if (-not $skills) {
    Write-Output "no skill found: no top-level dir under $repo contains SKILL.md"
    exit 1
}

$targets = @()
Get-ChildItem $usr -Directory -Force -ErrorAction SilentlyContinue | ForEach-Object {
    $s1 = Join-Path $_.FullName "skills"
    if (Test-Path $s1) { $targets += $s1 }
    Get-ChildItem $_.FullName -Directory -Force -ErrorAction SilentlyContinue | ForEach-Object {
        $s2 = Join-Path $_.FullName "skills"
        if (Test-Path $s2) { $targets += $s2 }
    }
}

$targets = ($targets | Sort-Object -Unique) | Where-Object {
    $_ -notmatch 'connectors|marketplace|skills\\skills|\.astrbot'
}

Write-Output ("repo:    " + $repo)
Write-Output ("skills:  " + ($skills -join ", "))
Write-Output ("targets: " + $targets.Count)
Write-Output ""

$created = 0; $removed = 0; $skipped = 0; $failed = 0

foreach ($skillName in $skills) {
    $source = Join-Path $repo $skillName
    foreach ($dir in $targets) {
        $link = Join-Path $dir $skillName
        $short = $link.Replace($usr, "~")
        $item = Get-Item $link -Force -ErrorAction SilentlyContinue

        if ($Uninstall) {
            if (-not $item) { $skipped++; continue }
            if ($item.LinkType -ne "Junction") {
                Write-Output ("  skip, real directory not a junction: " + $short)
                $skipped++
                continue
            }
            if ($DryRun) {
                Write-Output ("  would remove: " + $short)
                $removed++
                continue
            }
            [System.IO.Directory]::Delete($item.FullName, $false)
            $removed++
            continue
        }

        if ($item) {
            if ($item.LinkType -eq "Junction" -and ($item.Target -contains $source)) {
                $skipped++
            } else {
                Write-Output ("  skip, exists and points elsewhere: " + $short)
                $skipped++
            }
            continue
        }

        if ($DryRun) {
            Write-Output ("  would create: " + $short)
            $created++
            continue
        }

        try {
            New-Item -ItemType Junction -Path $link -Target $source -ErrorAction Stop | Out-Null
            $created++
        } catch {
            Write-Output ("  failed: " + $short + " :: " + $_.Exception.Message)
            $failed++
        }
    }
}

Write-Output ""
if ($Uninstall) {
    Write-Output ("removed " + $removed + ", skipped " + $skipped + ", failed " + $failed)
} else {
    Write-Output ("created " + $created + ", existing " + $skipped + ", failed " + $failed)
}
if ($DryRun) { Write-Output "(dry run, nothing changed)" }
