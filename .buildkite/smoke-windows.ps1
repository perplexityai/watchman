Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Set-SmokeCommit {
    if ($env:BUILDKITE_PULL_REQUEST -and $env:BUILDKITE_PULL_REQUEST -ne 'false') {
        $merge = & buildkite-agent meta-data get github-pr-merge
        if ($LASTEXITCODE -ne 0 -or $merge -cnotmatch '^[0-9a-f]{40}$') { throw 'Missing pinned PR merge SHA' }
        & git fetch --no-tags origin $merge | Out-Host
        if ($LASTEXITCODE -ne 0) { throw 'Cannot fetch pinned PR merge' }
        $head = & git rev-parse 'FETCH_HEAD^2'
        if ($LASTEXITCODE -ne 0 -or $head -cne $env:BUILDKITE_COMMIT) { throw 'Pinned merge does not contain PR head' }
        & git checkout --detach FETCH_HEAD | Out-Host
        if ($LASTEXITCODE -ne 0) { throw 'Cannot check out pinned PR merge' }
    }
}

Set-SmokeCommit
$work = Join-Path ([IO.Path]::GetTempPath()) ([guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Path $work | Out-Null
try {
    & buildkite-agent artifact download 'release/*' $work --build $env:BUILDKITE_BUILD_ID --step dist-build | Out-Host
    if ($LASTEXITCODE -ne 0) { throw 'Artifact download failed' }
    $directory = Join-Path $work 'release'
    $marker = Get-Item -LiteralPath (Join-Path $directory 'buildkite-release.json')
    if ($marker.Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Unsafe artifact manifest' }
    $manifest = Get-Content -Raw -LiteralPath $marker.FullName | ConvertFrom-Json
    $commit = & git rev-parse HEAD
    if ($LASTEXITCODE -ne 0) { throw 'Cannot resolve smoke commit' }
    $expected = @{ commit = $commit; build_id = $env:BUILDKITE_BUILD_ID; pipeline = $env:BUILDKITE_PIPELINE_SLUG }
    foreach ($key in $expected.Keys) {
        if ($manifest.$key -cne $expected[$key]) { throw "Artifact identity mismatch: $key" }
    }
    $files = ConvertFrom-Json -InputObject (Get-Content -Raw .buildkite/assets.json)
    if (Compare-Object -CaseSensitive $files @($manifest.files.PSObject.Properties.Name)) { throw 'Unexpected manifest files' }
    if (Compare-Object -CaseSensitive @($files + 'buildkite-release.json') @((Get-ChildItem -LiteralPath $directory).Name)) { throw 'Unexpected artifact files' }
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
