Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'


$work = Join-Path ([IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $work | Out-Null
try {
    Copy-Item -Recurse -LiteralPath (Join-Path $PWD "release") -Destination $work
    $directory = Join-Path $work 'release'
    $marker = Get-Item -LiteralPath (Join-Path $directory 'gha-release.json')
    if ($marker.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Unsafe artifact manifest' }
    $manifest = Get-Content -Raw -LiteralPath $marker.FullName | ConvertFrom-Json
    $commit = & git rev-parse HEAD
    if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve smoke commit' }
    $expected = @{ commit = $commit; build_id = $env:CI_RUN_ID; pipeline = $env:GITHUB_REPOSITORY }
    foreach ($key in $expected.Keys) {
        if ($manifest.$key -cne $expected[$key]) { throw "Artifact identity mismatch: $key" }
    }
    $files = ConvertFrom-Json -InputObject (Get-Content -Raw .github/ci/assets.json)
    if (Compare-Object -CaseSensitive $files @($manifest.files.PSObject.Properties.Name)) { throw 'Unexpected manifest files' }
    if (Compare-Object -CaseSensitive @($files + 'gha-release.json') @((Get-ChildItem -LiteralPath $directory).Name)) { throw 'Unexpected artifact files' }
    foreach ($name in $files) {
        $file = Get-Item -LiteralPath (Join-Path $directory $name)
        if ($file.PSIsContainer -or ($file.Attributes -band [IO.FileAttributes]::ReparsePoint)) { throw "Unsafe artifact: $name" }
        if ((Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName).Hash.ToLowerInvariant() -cne $manifest.files.$name) { throw "Artifact checksum mismatch: $name" }
    }
    & pwsh -NoProfile -File tests/watchman_smoke_test.ps1 -Watchman (Join-Path $directory 'watchman-x86_64-windows-gnu.exe')
    if ($LASTEXITCODE -ne 0) { throw 'Windows smoke failed' }
} finally {
    Remove-Item -LiteralPath $work -Recurse -Force
}
