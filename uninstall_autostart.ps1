$startupPath = [Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startupPath 'TIDAL RPC.lnk'

if (Test-Path -LiteralPath $shortcutPath) {
    Remove-Item -LiteralPath $shortcutPath -Force
    Write-Host 'Removed the TIDAL RPC startup shortcut.'
} else {
    Write-Host 'The TIDAL RPC startup shortcut was not installed.'
}
