# Descarga una carpeta/archivo de Google Drive (si los dueños te pasaron un link)
# Requisitos: pip install gdown
#
# Uso:
#   .\scripts\download-gdrive.ps1 -Url "https://drive.google.com/drive/folders/XXXX"
#   .\scripts\download-gdrive.ps1 -Url "https://drive.google.com/file/d/XXXX/view"

param(
  [Parameter(Mandatory = $true)]
  [string]$Url
)

$ErrorActionPreference = 'Stop'
$Root = Resolve-Path (Join-Path $PSScriptRoot '..')
$Out = Join-Path $Root 'downloads\owners'
New-Item -ItemType Directory -Force -Path $Out | Out-Null

python -m pip install gdown --quiet
Write-Host "Descargando a $Out ..."
python -m gdown --folder $Url -O $Out --remaining-ok
if ($LASTEXITCODE -ne 0) {
  # fallback archivo suelto
  python -m gdown $Url -O $Out
}
Write-Host "Listo: $Out"
