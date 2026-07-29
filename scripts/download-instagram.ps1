# Descarga masiva del Instagram @hostelvalizas (~todas las fotos del feed)
#
# MÉTODO A — cookies.txt (recomendado en Windows):
#   1) Extensión "Get cookies.txt LOCALLY" en Chrome/Edge
#   2) En instagram.com → exportar → guardar como:
#        hostel-valizas/cookies-instagram.txt
#   3) .\scripts\download-instagram.ps1
#
# MÉTODO B — cookies del browser:
#   .\scripts\download-instagram.ps1 -Browser edge
#   (cerrá el browser antes; a veces falla por DPAPI en Windows)
#
# Uso:
#   .\scripts\download-instagram.ps1
#   .\scripts\download-instagram.ps1 -Limit 200
#   .\scripts\download-instagram.ps1 -Browser firefox

param(
  [ValidateSet('chrome', 'edge', 'firefox', 'none')]
  [string]$Browser = 'none',
  [int]$Limit = 0,
  [string]$User = 'hostelvalizas',
  [string]$CookiesFile = ''
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$Out = Join-Path $Root "downloads\instagram\$User"
New-Item -ItemType Directory -Force -Path $Out | Out-Null

if (-not $CookiesFile) {
  $CookiesFile = Join-Path $Root 'cookies-instagram.txt'
}

$argsList = @(
  '-d', $Out,
  '--write-metadata',
  '-o', 'filename={date:%Y%m%d}_{shortcode}_{num}.{extension}',
  '-o', 'sleep-request=2.5-5',
  '-o', 'sleep=1-2'
)

if (Test-Path $CookiesFile) {
  Write-Host ">>> Usando cookies: $CookiesFile"
  $argsList += @('--cookies', $CookiesFile)
} elseif ($Browser -ne 'none') {
  Write-Host ">>> Browser cookies: $Browser (cerralo antes)"
  $argsList += @('--cookies-from-browser', $Browser)
} else {
  Write-Host ""
  Write-Host "FALTA LOGIN. Hacé esto (2 minutos):"
  Write-Host "  1) Instalá la extensión: Get cookies.txt LOCALLY"
  Write-Host "  2) Abrí https://www.instagram.com y logueate"
  Write-Host "  3) Exportá cookies → guardá como:"
  Write-Host "       $CookiesFile"
  Write-Host "  4) Volvé a correr: .\scripts\download-instagram.ps1"
  Write-Host ""
  exit 1
}

if ($Limit -gt 0) {
  $argsList = @('-o', "image-range=1-$Limit") + $argsList
}

$argsList += "https://www.instagram.com/$User/"

Write-Host ">>> Destino: $Out"
Write-Host "Corriendo gallery-dl..."
Write-Host ""

& gallery-dl @argsList
$code = $LASTEXITCODE

Write-Host ""
$count = @(Get-ChildItem -Path $Out -Recurse -File -Include *.jpg,*.jpeg,*.png,*.webp -ErrorAction SilentlyContinue).Count
Write-Host ">>> Imágenes descargadas: $count"
if ($code -ne 0) {
  Write-Host "Falló. Revisá cookies o probá -Browser edge con el browser cerrado."
  exit $code
}
Write-Host "Listo → $Out"
