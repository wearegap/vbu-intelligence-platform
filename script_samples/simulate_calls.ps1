<#
.SYNOPSIS
    Simulate a full VBU Intelligence Platform call analysis over each of the 5 sample lead scripts.
    For each script: reads the transcript → POSTs to the Anthropic extraction bridge →
    displays extracted signals → saves a JSON result file.

.USAGE
    From the repo root:
        .\script_samples\simulate_calls.ps1

.PREREQUISITES
    - Python 3.x available in PATH
    - ANTHROPIC_API_KEY set in .env (at repo root) or in the environment
    - Transcript files present in .\script_samples\
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ── Paths ─────────────────────────────────────────────────────────────────────
$Root        = Split-Path $PSScriptRoot -Parent
$ScriptsDir  = $PSScriptRoot
$BridgeScript = Join-Path $Root "anthropicClient.py"
$ResultsDir  = Join-Path $ScriptsDir "results"
$BridgeUrl   = "http://127.0.0.1:8766"
$ExtractUrl  = "$BridgeUrl/api/anthropic/extract-signals"

# ── Helpers ───────────────────────────────────────────────────────────────────
function Write-Header($text) {
    $line = "=" * 68
    Write-Host ""
    Write-Host $line -ForegroundColor Cyan
    Write-Host "  $text" -ForegroundColor Cyan
    Write-Host $line -ForegroundColor Cyan
}

function Write-Section($label, $value, $color = "White") {
    Write-Host ("  {0,-26}" -f "${label}:") -NoNewline -ForegroundColor DarkGray
    Write-Host $value -ForegroundColor $color
}

function Wait-ForBridge {
    param([int]$MaxWaitSec = 12)
    $deadline = (Get-Date).AddSeconds($MaxWaitSec)
    while ((Get-Date) -lt $deadline) {
        try {
            $null = Invoke-WebRequest -Uri "$BridgeUrl/health" -TimeoutSec 2 -ErrorAction Stop
            return $true
        } catch { Start-Sleep -Milliseconds 500 }
    }
    return $false
}

# ── Ensure results directory exists ──────────────────────────────────────────
if (-not (Test-Path $ResultsDir)) {
    New-Item -ItemType Directory -Path $ResultsDir | Out-Null
}

# ── Start bridge server if not already running ────────────────────────────────
Write-Header "GAP Velocity AI — Call Simulation Runner"
Write-Host ""
Write-Host "  Checking Anthropic bridge server at $BridgeUrl …" -ForegroundColor Gray

$bridgeAlreadyUp = $false
try {
    $null = Invoke-WebRequest -Uri "$BridgeUrl/health" -TimeoutSec 2 -ErrorAction Stop
    $bridgeAlreadyUp = $true
    Write-Host "  Bridge is already running." -ForegroundColor Green
} catch {
    Write-Host "  Bridge not running — starting it now …" -ForegroundColor Yellow
    Start-Process -FilePath "python" -ArgumentList "`"$BridgeScript`" serve 8766" `
        -WorkingDirectory $Root -WindowStyle Minimized
    if (Wait-ForBridge -MaxWaitSec 14) {
        Write-Host "  Bridge started successfully." -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "  ERROR: Bridge server did not start in time." -ForegroundColor Red
        Write-Host "  Make sure Python is available and ANTHROPIC_API_KEY is set in .env" -ForegroundColor Yellow
        exit 1
    }
}

# ── Lead definitions ──────────────────────────────────────────────────────────
$Leads = @(
    @{
        ClientName = "TechCore Solutions"
        File       = "TechCore_Solutions_Discovery.txt"
        ExpectedTech = "PowerBuilder"
        ExpectedLOC  = "~180K"
    },
    @{
        ClientName = "Meridian Financial Group"
        File       = "Meridian_Financial_Group_Discovery.txt"
        ExpectedTech = "VB.NET"
        ExpectedLOC  = "~420K"
    },
    @{
        ClientName = "Nexus Insurance Corp"
        File       = "Nexus_Insurance_Corp_Discovery.txt"
        ExpectedTech = "Clarion"
        ExpectedLOC  = "~95K"
    },
    @{
        ClientName = "Heritage Industrial Systems"
        File       = "Heritage_Industrial_Systems_Discovery.txt"
        ExpectedTech = "Delphi"
        ExpectedLOC  = "~250K"
    },
    @{
        ClientName = "Atlas Retail Solutions"
        File       = "Atlas_Retail_Solutions_Discovery.txt"
        ExpectedTech = "WebForms / ASP Classic"
        ExpectedLOC  = "~310K"
    }
)

# ── Complexity labels (matches COMPLEXITY array in the HTML) ──────────────────
$ComplexityLabels = @("Clean (1.0x)", "Conventional (1.3x)", "Complex (1.5x)", "Spaghetti (1.7x)")

# ── Process each lead ─────────────────────────────────────────────────────────
$Summary = @()
$Index   = 0

foreach ($Lead in $Leads) {
    $Index++
    $TranscriptPath = Join-Path $ScriptsDir $Lead.File

    Write-Header "Lead $Index / $($Leads.Count) — $($Lead.ClientName)"
    Write-Host "  File     : $($Lead.File)" -ForegroundColor DarkGray
    Write-Host "  Expected : $($Lead.ExpectedTech) · $($Lead.ExpectedLOC) LOC" -ForegroundColor DarkGray
    Write-Host ""

    # Read transcript
    if (-not (Test-Path $TranscriptPath)) {
        Write-Host "  [SKIP] Transcript file not found: $TranscriptPath" -ForegroundColor Red
        continue
    }
    $Transcript = Get-Content -Path $TranscriptPath -Raw -Encoding UTF8

    # POST to extraction bridge
    Write-Host "  Sending transcript to Anthropic extraction bridge …" -ForegroundColor Gray
    $Payload = @{
        clientName = $Lead.ClientName
        transcript = $Transcript
    } | ConvertTo-Json -Depth 3 -Compress

    $StartTime = Get-Date
    try {
        $Response = Invoke-WebRequest -Uri $ExtractUrl `
            -Method POST `
            -ContentType "application/json" `
            -Body ([System.Text.Encoding]::UTF8.GetBytes($Payload)) `
            -TimeoutSec 120 `
            -ErrorAction Stop
        $ElapsedMs = [int]((Get-Date) - $StartTime).TotalMilliseconds
        $Result    = $Response.Content | ConvertFrom-Json
        $Ext       = $Result.extraction
    } catch {
        $ElapsedMs = [int]((Get-Date) - $StartTime).TotalMilliseconds
        Write-Host "  [ERROR] API call failed: $_" -ForegroundColor Red
        Write-Host "  Make sure ANTHROPIC_API_KEY is set in .env and the bridge is running." -ForegroundColor Yellow
        $Summary += [PSCustomObject]@{
            Lead   = $Lead.ClientName
            Status = "FAILED"
            Error  = $_.Exception.Message
        }
        continue
    }

    # ── Display extracted signals ──────────────────────────────────────────
    Write-Host ""
    Write-Host "  ✓ Extraction complete in ${ElapsedMs}ms" -ForegroundColor Green
    Write-Host ""
    Write-Host "  ── MODERNIZATION SIGNALS ──────────────────────────────────" -ForegroundColor DarkCyan

    $sourceTech    = if ($Ext.sourceTech)       { $Ext.sourceTech }        else { "(not found)" }
    $targetTech    = if ($Ext.targetTech)       { $Ext.targetTech }        else { "(not found)" }
    $loc           = if ($Ext.linesOfCode)      { "{0:N0}" -f [int]$Ext.linesOfCode } else { "(not found)" }
    $complexIdx    = if ($null -ne $Ext.complexityLevel) { [int]$Ext.complexityLevel } else { -1 }
    $complexLabel  = if ($complexIdx -ge 0 -and $complexIdx -le 3) { $ComplexityLabels[$complexIdx] } else { "(not found)" }
    $devCount      = if ($Ext.customersDevCount) { "$($Ext.customersDevCount) developers" } else { "(not found)" }
    $confidence    = if ($Ext.confidence)        { "$($Ext.confidence)%" }  else { "—" }

    Write-Section "Source Technology"    $sourceTech    "Yellow"
    Write-Section "Target Platform"      $targetTech    "Cyan"
    Write-Section "Lines of Code"        $loc           "White"
    Write-Section "Complexity"           $complexLabel  "White"
    Write-Section "Customer Dev Count"   $devCount      "White"
    Write-Section "Extraction Confidence" $confidence   "Green"

    if ($Ext.sourceTechSnippet) {
        Write-Host ""
        Write-Host "  Source snippet   : `"$($Ext.sourceTechSnippet)`"" -ForegroundColor DarkGray
    }
    if ($Ext.linesSnippet) {
        Write-Host "  LOC snippet      : `"$($Ext.linesSnippet)`"" -ForegroundColor DarkGray
    }
    if ($Ext.complexitySnippet) {
        Write-Host "  Complexity snippet: `"$($Ext.complexitySnippet)`"" -ForegroundColor DarkGray
    }
    if ($Ext.devCountSnippet) {
        Write-Host "  Dev count snippet: `"$($Ext.devCountSnippet)`"" -ForegroundColor DarkGray
    }

    if ($Ext.summary) {
        Write-Host ""
        Write-Host "  ── AI SUMMARY ─────────────────────────────────────────────" -ForegroundColor DarkCyan
        Write-Host "  $($Ext.summary)" -ForegroundColor Gray
    }

    # ── Sales Strategy summary ─────────────────────────────────────────────
    if ($Ext.salesStrategy) {
        $ss = $Ext.salesStrategy
        Write-Host ""
        Write-Host "  ── SALES STRATEGY ─────────────────────────────────────────" -ForegroundColor DarkCyan
        Write-Section "Deal Motion"          ($ss.dealMotion        ?? "—") "Magenta"
        Write-Section "Value Angle"          ($ss.primaryValueAngle ?? "—") "Magenta"
        Write-Section "Timeline Urgency"     ($ss.timelineUrgency   ?? "—") "Magenta"
        Write-Section "Commercial Approach"  ($ss.commercialApproach ?? "—") "Magenta"
        $stratConf = if ($ss.confidence) { "$($ss.confidence)%" } else { "—" }
        Write-Section "Strategy Confidence"  $stratConf "Green"
    }

    # ── Save result to JSON ────────────────────────────────────────────────
    $SafeName   = $Lead.ClientName -replace '[^\w]', '_'
    $ResultFile = Join-Path $ResultsDir "${SafeName}_extraction.json"
    $Result | ConvertTo-Json -Depth 20 | Set-Content -Path $ResultFile -Encoding UTF8
    Write-Host ""
    Write-Host "  Result saved → $ResultFile" -ForegroundColor DarkGray

    $Summary += [PSCustomObject]@{
        Lead       = $Lead.ClientName
        Status     = "OK"
        SourceTech = $sourceTech
        LOC        = $loc
        Complexity = $complexLabel
        DevCount   = $devCount
        Confidence = $confidence
        ResultFile = $ResultFile
    }
}

# ── Final summary table ───────────────────────────────────────────────────────
Write-Header "Simulation Complete — Summary"
Write-Host ""
$Summary | Format-Table -AutoSize -Property Lead, Status, SourceTech, LOC, Complexity, DevCount, Confidence
Write-Host ""
Write-Host "  JSON results saved in: $ResultsDir" -ForegroundColor DarkGray
Write-Host ""

if (-not $bridgeAlreadyUp) {
    Write-Host "  Note: The Anthropic bridge was started by this script." -ForegroundColor DarkGray
    Write-Host "  It will continue running in the background for the HTML platform." -ForegroundColor DarkGray
    Write-Host "  To stop it, close the minimized cmd window or kill the python process." -ForegroundColor DarkGray
    Write-Host ""
}
