param(
    [string]$Version = "latest"
)

$ErrorActionPreference = "Stop"

$Repo = if ($env:ANKICLI_REPO) { $env:ANKICLI_REPO } else { "Takhoffman/ankicli" }
$ReleasesBase = if ($env:ANKICLI_RELEASES_BASE) { $env:ANKICLI_RELEASES_BASE } else { "https://github.com/$Repo/releases" }
$ReleaseApi = if ($env:ANKICLI_RELEASE_API) { $env:ANKICLI_RELEASE_API } else { "https://api.github.com/repos/$Repo/releases/latest" }
$InstallRoot = if ($env:ANKICLI_INSTALL_ROOT) { $env:ANKICLI_INSTALL_ROOT } else { Join-Path $env:LOCALAPPDATA "Programs\ankicli" }
$SkipVerify = if ($env:ANKICLI_SKIP_VERIFY) { [int]$env:ANKICLI_SKIP_VERIFY } else { 0 }

function Fail([string]$Message) {
    throw "ankicli install error: $Message"
}

function Resolve-Version {
    param([string]$Candidate)

    if ($Candidate -ne "latest") {
        return $Candidate
    }

    if ($env:ANKICLI_LATEST_VERSION) {
        return $env:ANKICLI_LATEST_VERSION
    }

    $Release = Invoke-RestMethod -Uri $ReleaseApi
    if (-not $Release.tag_name) {
        Fail "latest release response did not include a tag_name"
    }
    return $Release.tag_name.TrimStart("v")
}

function Get-TargetId {
    if ($env:ANKICLI_TARGET) {
        return $env:ANKICLI_TARGET
    }

    $Arch = [System.Runtime.InteropServices.RuntimeInformation]::OSArchitecture
    switch ($Arch) {
        "X64" { return "windows-x64" }
        default { Fail "unsupported Windows architecture: $Arch" }
    }
}

function Verify-Checksum {
    param(
        [string]$ArchivePath,
        [string]$ChecksumsPath
    )

    $ArchiveName = [System.IO.Path]::GetFileName($ArchivePath)
    $Line = Get-Content $ChecksumsPath | Where-Object { $_ -match [regex]::Escape($ArchiveName) } | Select-Object -First 1
    if (-not $Line) {
        Fail "missing checksum for $ArchiveName"
    }
    $Expected = ($Line -split "\s+")[0]
    $Actual = (Get-FileHash -Path $ArchivePath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($Expected.ToLowerInvariant() -ne $Actual) {
        Fail "checksum mismatch for $ArchiveName"
    }
}

$ResolvedVersion = Resolve-Version -Candidate $Version
$TargetId = Get-TargetId
$ArchiveName = "ankicli-$ResolvedVersion-$TargetId.zip"
$ChecksumsName = "ankicli-$ResolvedVersion-checksums.txt"
$ReleaseTag = "v$ResolvedVersion"
$TempRoot = Join-Path ([System.IO.Path]::GetTempPath()) ("ankicli-install-" + [guid]::NewGuid().ToString("N"))
$ArchivePath = Join-Path $TempRoot $ArchiveName
$ChecksumsPath = Join-Path $TempRoot $ChecksumsName
$ExtractDir = Join-Path $TempRoot "extract"

New-Item -ItemType Directory -Path $TempRoot | Out-Null

Invoke-WebRequest -Uri "$ReleasesBase/download/$ReleaseTag/$ArchiveName" -OutFile $ArchivePath
Invoke-WebRequest -Uri "$ReleasesBase/download/$ReleaseTag/$ChecksumsName" -OutFile $ChecksumsPath

Verify-Checksum -ArchivePath $ArchivePath -ChecksumsPath $ChecksumsPath
Expand-Archive -Path $ArchivePath -DestinationPath $ExtractDir -Force

$PayloadDir = Get-ChildItem -Path $ExtractDir -Directory | Select-Object -First 1
if (-not $PayloadDir) {
    Fail "release archive did not contain a payload directory"
}

$ExecutablePath = Join-Path $PayloadDir.FullName "ankicli.exe"
if (-not (Test-Path $ExecutablePath)) {
    Fail "release archive did not contain ankicli.exe"
}

New-Item -ItemType Directory -Force -Path $InstallRoot | Out-Null
$VersionRoot = Join-Path $InstallRoot $ResolvedVersion
if (Test-Path $VersionRoot) {
    Remove-Item $VersionRoot -Recurse -Force
}
New-Item -ItemType Directory -Force -Path $VersionRoot | Out-Null
Copy-Item (Join-Path $PayloadDir.FullName "*") $VersionRoot -Recurse -Force

Write-Host "Installed ankicli $ResolvedVersion to $(Join-Path $VersionRoot 'ankicli.exe')"

$CurrentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
if (-not $CurrentPath -or ($CurrentPath -split ';') -notcontains $VersionRoot) {
    Write-Host ""
    Write-Host "Add this directory to your PATH if needed:"
    Write-Host "  $VersionRoot"
}

if ($SkipVerify -ne 1) {
    & (Join-Path $VersionRoot "ankicli.exe") --version
    & (Join-Path $VersionRoot "ankicli.exe") --json doctor backend
}
