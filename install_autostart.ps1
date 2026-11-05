$ErrorActionPreference = 'Stop'

$projectPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$entryPoint = Join-Path $projectPath 'tidal_rpc.py'
$exampleEnv = Join-Path $projectPath '.env.example'
$localEnv = Join-Path $projectPath '.env'

if (-not (Test-Path -LiteralPath $entryPoint)) {
    throw "Could not find tidal_rpc.py in $projectPath"
}

if (-not (Test-Path -LiteralPath $localEnv)) {
    Copy-Item -LiteralPath $exampleEnv -Destination $localEnv
    Write-Host 'Created .env. Add your Discord and TIDAL credentials before starting the app.'
}

$pythonPath = (& py -c 'import sys; print(sys.executable)' | Select-Object -Last 1).Trim()
if (-not $pythonPath -or -not (Test-Path -LiteralPath $pythonPath)) {
    throw 'Python launcher (py) could not find a Python installation.'
}

$pythonwPath = Join-Path (Split-Path -Parent $pythonPath) 'pythonw.exe'
if (-not (Test-Path -LiteralPath $pythonwPath)) {
    throw "Could not find pythonw.exe beside $pythonPath"
}

$startupPath = [Environment]::GetFolderPath('Startup')
$shortcutPath = Join-Path $startupPath 'TIDAL RPC.lnk'
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($shortcutPath)
$shortcut.TargetPath = $pythonwPath
$shortcut.Arguments = '"' + $entryPoint + '"'
$shortcut.WorkingDirectory = $projectPath
$shortcut.Description = 'TIDAL Discord Rich Presence'
$shortcut.WindowStyle = 7
$shortcut.Save()

Write-Host "Installed startup shortcut: $shortcutPath"
Write-Host 'TIDAL RPC will start in the notification area when you sign in to Windows.'
