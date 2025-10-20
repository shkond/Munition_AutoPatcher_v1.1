<#
Usage:
  .\check_first40_lines.ps1 -Path .\AutoPatcherLib.pas

What it does:
- Shows detected BOM (UTF-8/UTF-16/UTF-32) if present.
- Prints the first 40 text lines with line numbers.
- Shows a "visualized" form where invisible / suspicious characters are replaced with <U+XXXX>.
- Lists any suspicious Unicode codepoints (zero-width, BOM, non-breaking space, control chars).
- Dumps first 256 bytes as hex for quick inspection.
#>

param(
  [Parameter(Mandatory=$true)][string]$Path
)

if (-not (Test-Path $Path)) {
  Write-Error "File not found: $Path"
  exit 2
}

$bytes = [System.IO.File]::ReadAllBytes($Path)

function Detect-BOM {
  param($b)
  if ($b.Length -ge 3 -and $b[0] -eq 0xEF -and $b[1] -eq 0xBB -and $b[2] -eq 0xBF) { return "UTF-8 BOM (EF BB BF)" }
  if ($b.Length -ge 2 -and $b[0] -eq 0xFF -and $b[1] -eq 0xFE) { return "UTF-16 LE BOM (FF FE)" }
  if ($b.Length -ge 2 -and $b[0] -eq 0xFE -and $b[1] -eq 0xFF) { return "UTF-16 BE BOM (FE FF)" }
  if ($b.Length -ge 4 -and $b[0] -eq 0xFF -and $b[1] -eq 0xFE -and $b[2] -eq 0x00 -and $b[3] -eq 0x00) { return "UTF-32 LE BOM (FF FE 00 00)" }
  if ($b.Length -ge 4 -and $b[0] -eq 0x00 -and $b[1] -eq 0x00 -and $b[2] -eq 0xFE -and $b[3] -eq 0xFF) { return "UTF-32 BE BOM (00 00 FE FF)" }
  return "None detected"
}

$bom = Detect-BOM $bytes
Write-Host "BOM: $bom"
Write-Host "First 256 bytes (hex):"
$hex = ($bytes[0..([math]::Min(255, $bytes.Length-1))] | ForEach-Object { '{0:X2}' -f $_ }) -join ' '
Write-Host $hex
Write-Host ""

# Helper: returns visible representation of a line
function Visualize-Line {
  param([string]$line)
  $out = ''
  foreach ($ch in $line.ToCharArray()) {
    $cp = [int]$ch
    # Allow common printable characters and whitespace (tab)
    if (($cp -ge 32 -and $cp -le 126) -or $cp -eq 9) {
      $out += $ch
    } else {
      $out += "<U+{0:X4}>" -f $cp
    }
  }
  return $out
}

# Suspicious set to highlight
$SUSPICIOUS = @(
  0xFEFF, # ZERO WIDTH NO-BREAK SPACE / BOM
  0x200B, # ZERO WIDTH SPACE
  0x00A0, # NO-BREAK SPACE
  0x200E, # LEFT-TO-RIGHT MARK
  0x200F  # RIGHT-TO-LEFT MARK
)

# Read first 40 lines using .NET StreamReader with fallback decodings
function Read-Lines {
  param($path, $maxLines = 40)
  $encodings = @(
    [System.Text.Encoding]::UTF8,
    [System.Text.Encoding]::Unicode,      # UTF-16 LE
    [System.Text.Encoding]::BigEndianUnicode,
    [System.Text.Encoding]::ASCII,
    [System.Text.Encoding]::Default
  )
  foreach ($enc in $encodings) {
    try {
      $sr = New-Object System.IO.StreamReader($path, $enc, $true)
      $lines = @()
      for ($i=0; $i -lt $maxLines -and -not $sr.EndOfStream; $i++) {
        $lines += $sr.ReadLine()
      }
      $sr.Close()
      return ,@($enc.BodyName, $lines)
    } catch {
      # try next encoding
    }
  }
  return ,@("unknown", @())
}

$readResult = Read-Lines $Path 40
$detectedEncoding = $readResult[0]
$lines = $readResult[1]

Write-Host "Detected/used encoding for reading (attempt): $detectedEncoding"
Write-Host ""
Write-Host "First $(($lines).Count) lines (visualized):"
$ln = 1
$issues = @()
foreach ($line in $lines) {
  $vis = Visualize-Line $line
  Write-Host ("{0,3}: {1}" -f $ln, $vis)
  # scan for suspicious chars
  for ($i=0; $i -lt $line.Length; $i++) {
    $cp = [int]$line[$i]
    if ($cp -lt 32 -and $cp -ne 9 -and $cp -ne 10 -and $cp -ne 13) {
      $issues += [PSCustomObject]@{Line=$ln;Col=$i+1;CodePoint=$cp;Hex=("{0:X4}" -f $cp);Char="<U+{0:X4}>" -f $cp}
    } elseif ($SUSPICIOUS -contains $cp) {
      $issues += [PSCustomObject]@{Line=$ln;Col=$i+1;CodePoint=$cp;Hex=("{0:X4}" -f $cp);Char="<U+{0:X4}>" -f $cp}
    } elseif ($cp -gt 127 -and $cp -lt 160) {
      # C1 control block
      $issues += [PSCustomObject]@{Line=$ln;Col=$i+1;CodePoint=$cp;Hex=("{0:X4}" -f $cp);Char="<U+{0:X4}>" -f $cp}
    }
  }
  $ln++
}

if ($issues.Count -gt 0) {
  Write-Host ""
  Write-Host "Suspicious characters found:"
  $issues | Format-Table -AutoSize
} else {
  Write-Host ""
  Write-Host "No suspicious invisible/control characters found in the first lines."
}