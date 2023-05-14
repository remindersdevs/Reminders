
param (
    [string[]]$arches = 'x64',
    [string]$root = 'C:\msys64',
    [switch]$msi,
    [switch]$release,
    [switch]$help
)

$SCRIPT_PATH = $PSScriptRoot.replace('\', '/')

if ($help) {
    write-host 'Usage: build_windows.ps1 [options...]'
    write-host 'Options:'
    write-host "	-arches <arcn...> Can be x86, x64, or arm64. Comma separated list, default is x64."
    write-host "	-root <path>      MSYS2 root path, default is 'C:\msys64'."
    write-host "	-msi              Build an msi installer"
    write-host "	-release          Build a release build instead of devel build"
    write-host "	-help 	          Display this message."
    exit
}

if ($root -match '[a-zA-Z]:(\/|\\).*') {
    $root = $root.TrimEnd('\', '/')
} else {
    throw 'Invalid root path'
}

[string[]]$msystems = @()

for ( $i = 0; $i -lt $arches.count; $i++ ) {
    $arch = $($arches[$i])
    if ($arch -eq 'x86') {
        $msystems += 'mingw32'
    } elseif ($arch -eq 'x64') {
        $msystems += 'mingw64'
    } elseif ($arch -eq 'arm64') {
        $msystems += 'clangarm64'
    } else {
        throw 'Invalid arch'
    }
}

if ($msystems.count -eq 0) {
    throw 'Specify an arch'
}

if ($release) {
    $type = "stable"
    $conf = "Release"
} else {
    $type = "devel"
    $conf = "Devel"
}

for ( $i = 0; $i -lt $msystems.count; $i++ ) {
    $msystem = $($msystems[$i])
    & ${root}\msys2_shell.cmd -defterm -here -no-start -shell bash -${msystem} -lc "${SCRIPT_PATH}/package-msys2.sh ${type}"
}

if ($msi) {
    for ( $i = 0; $i -lt $arches.count; $i++ ) {
        $arch = $($arches[$i])
        dotnet build $PSScriptRoot\Reminders.wixproj -property:Configuration=$conf -property:Platform=$arch
    }
}
