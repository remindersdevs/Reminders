
param (
    [string]$arch = 'x64',
    [string]$root = 'C:\msys64',
    [switch]$help
)

$SCRIPT_PATH = $PSScriptRoot.replace('\', '/')

if ($help) {
    write-host 'Usage: update_potfile.ps1 [options...]'
    write-host 'Options:'
    write-host "	-arches <arcn...> Can be x86, x64, or arm64."
    write-host "	-root <path>      MSYS2 root path, default is 'C:\msys64'."
    write-host "	-help 	          Display this message."
    exit
}

if ($root -match '[a-zA-Z]:(\/|\\).*') {
    $root = $root.TrimEnd('\', '/')
} else {
    throw 'Invalid root path'
}

if ($arch -eq 'x86') {
    $msystem = 'mingw32'
} elseif ($arch -eq 'x64') {
    $msystem = 'mingw64'
} elseif ($arch -eq 'arm64') {
    $msystem = 'clangarm64'
} else {
    throw 'Invalid arch'
}

& ${root}\msys2_shell.cmd -defterm -here -no-start -shell bash -${msystem} -lc "${SCRIPT_PATH}/update_potfile_msys.sh"
