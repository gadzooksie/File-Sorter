# Creates a desktop shortcut showing the File Sorter icon (does not change file associations).
$ErrorActionPreference = 'Stop'
$dir = Split-Path -Parent $MyInvocation.MyCommand.Path
$cmd = Join-Path $dir 'File Sorter.cmd'
$ico = Join-Path $dir 'assets\file-sorter.ico'
if (!(Test-Path -LiteralPath $cmd) -or !(Test-Path -LiteralPath $ico)) { throw 'Missing File Sorter launcher or icon.' }
$desktop = [Environment]::GetFolderPath('Desktop')
$shortcut = (New-Object -ComObject WScript.Shell).CreateShortcut((Join-Path $desktop 'File Sorter.lnk'))
$shortcut.TargetPath = $cmd
$shortcut.WorkingDirectory = $dir
$shortcut.IconLocation = $ico + ',0'
$shortcut.Description = 'File Sorter - configurable automatic file organizer'
$shortcut.Save()
Write-Host ('Desktop shortcut created: ' + (Join-Path $desktop 'File Sorter.lnk'))
