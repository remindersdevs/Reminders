# Copyright (C) 2023 Sasha Hale <dgsasha04@gmail.com>
#
# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at https://mozilla.org/MPL/2.0/.

param (
    [string[]]$arches = 'x64',
    [string]$configuration = 'Devel',
    [string]$root = 'C:\msys64',
    [switch]$help
)

$SCRIPT_PATH = $PSScriptRoot.replace('\', '/')

if ($help) {
    write-host 'Usage: build_windows.ps1 [options...]'
    write-host 'Options:'
    write-host "	-arches <arcn...>       Can be x86, x64, or ARM64. Comma separated list, default is x64."
    write-host "	-configuration <config> Can be Devel or Release, default is Devel."
    write-host "	-root <path>            MSYS2 root path, default is 'C:\msys64'."
    write-host "	-msi                    Build an msi installer"
    write-host "	-help 	                Display this message."
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
    } elseif ($arch -eq 'ARM64') {
        $msystems += 'clangarm64'
    } else {
        throw 'Invalid arch'
    }
}

if ($msystems.count -eq 0) {
    throw 'Specify an arch'
}

for ( $i = 0; $i -lt $msystems.count; $i++ ) {
    $msystem = $($msystems[$i])
    & ${root}\msys2_shell.cmd -defterm -here -no-start -shell bash -${msystem} -lc "${SCRIPT_PATH}/package-msys2.sh ${configuration}"
}
