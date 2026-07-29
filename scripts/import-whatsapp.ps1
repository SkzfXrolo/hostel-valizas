# Junta fotos que salieron de WhatsApp en downloads\whatsapp
#
# Forma A (recomendada, 200 fotos de un saque):
#   1) WhatsApp Desktop → chat con los dueños
#   2) Menú ⋮ del chat → Exportar chat → "Incluir archivos multimedia"
#   3) Te genera un .zip (o carpeta). Corré:
#        .\scripts\import-whatsapp.ps1 -From "C:\Users\robin\Downloads\WhatsApp Chat - ....zip"
#
# Forma B (arrastrar / guardar a mano):
#   Guardá o arrastrá las fotos a:
#     downloads\whatsapp\_drop
#   y corré:
#        .\scripts\import-whatsapp.ps1
#
# Forma C (vigilar carpeta mientras guardás):
#        .\scripts\import-whatsapp.ps1 -Watch

param(
  [string]$From = '',
  [switch]$Watch,
  [int]$WatchSeconds = 600
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Dest = Join-Path $Root 'downloads\whatsapp'
$Drop = Join-Path $Dest '_drop'
New-Item -ItemType Directory -Force -Path $Dest, $Drop | Out-Null

function Import-ImagesFromDir([string]$dir) {
  $files = Get-ChildItem -Path $dir -Recurse -File -Include *.jpg,*.jpeg,*.png,*.webp,*.heic,*.JPG,*.JPEG,*.PNG,*.WEBP -ErrorAction SilentlyContinue
  $n = 0
  foreach ($f in $files) {
    # saltar thumbs / basura chica
    if ($f.Length -lt 20KB) { continue }
    $name = $f.Name
    $target = Join-Path $Dest $name
    if (Test-Path $target) {
      $hash = Get-FileHash $f.FullName -Algorithm MD5
      $target = Join-Path $Dest ("{0}_{1}{2}" -f $f.BaseName, $hash.Hash.Substring(0, 6), $f.Extension)
    }
    Copy-Item -LiteralPath $f.FullName -Destination $target -Force
    $n++
  }
  return $n
}

if ($From) {
  if (-not (Test-Path -LiteralPath $From)) { throw "No existe: $From" }

  $temp = Join-Path $env:TEMP ("wa-import-" + [guid]::NewGuid().ToString('n'))
  New-Item -ItemType Directory -Force -Path $temp | Out-Null

  if ($From -match '\.zip$') {
    Write-Host "Descomprimiendo zip..."
    Expand-Archive -LiteralPath $From -DestinationPath $temp -Force
    $copied = Import-ImagesFromDir $temp
  } elseif ((Get-Item -LiteralPath $From).PSIsContainer) {
    $copied = Import-ImagesFromDir $From
  } else {
    throw "Pasá un .zip o una carpeta"
  }

  Remove-Item -Recurse -Force $temp -ErrorAction SilentlyContinue
  $total = @(Get-ChildItem $Dest -File -Include *.jpg,*.jpeg,*.png,*.webp,*.heic -ErrorAction SilentlyContinue).Count
  Write-Host "Importadas ahora: $copied"
  Write-Host "Total en $Dest : $total"
  exit 0
}

# Importar lo que haya en _drop
$fromDrop = Import-ImagesFromDir $Drop
Write-Host "Desde _drop: $fromDrop archivo(s)"

if ($Watch) {
  Write-Host ""
  Write-Host "Vigilando $Drop durante $WatchSeconds s..."
  Write-Host "En WhatsApp: seleccioná fotos → Guardar / Arrastrá a esa carpeta."
  Write-Host "Ctrl+C para cortar."
  Write-Host ""
  $end = (Get-Date).AddSeconds($WatchSeconds)
  $seen = @{}
  Get-ChildItem $Drop -Recurse -File -ErrorAction SilentlyContinue | ForEach-Object { $seen[$_.FullName] = $true }

  while ((Get-Date) -lt $end) {
    Start-Sleep -Seconds 2
    $new = Get-ChildItem $Drop -Recurse -File -Include *.jpg,*.jpeg,*.png,*.webp,*.heic -ErrorAction SilentlyContinue |
      Where-Object { -not $seen.ContainsKey($_.FullName) -and $_.Length -ge 20KB }
    foreach ($f in $new) {
      $seen[$f.FullName] = $true
      $target = Join-Path $Dest $f.Name
      if (Test-Path $target) {
        $target = Join-Path $Dest ("{0}_{1:HHmmss}{2}" -f $f.BaseName, (Get-Date), $f.Extension)
      }
      Copy-Item -LiteralPath $f.FullName -Destination $target -Force
      Write-Host "  + $($f.Name)"
    }
  }
}

$total = @(Get-ChildItem $Dest -File -ErrorAction SilentlyContinue | Where-Object { $_.Extension -match '\.(jpe?g|png|webp|heic)$' }).Count
Write-Host "Total fotos en downloads\whatsapp: $total"
Write-Host "Carpeta drop: $Drop"
