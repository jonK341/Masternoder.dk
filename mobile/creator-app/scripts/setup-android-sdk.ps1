# Download Android SDK command-line tools and install build packages for Capacitor.
$ErrorActionPreference = "Stop"
$sdkRoot = Join-Path $env:LOCALAPPDATA "Android\Sdk"
$zipUrl = "https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip"
$tmpZip = Join-Path $env:TEMP "android-cmdline-tools.zip"
$cmdRoot = Join-Path $sdkRoot "cmdline-tools"
$latestDir = Join-Path $cmdRoot "latest"

Write-Host "SDK root: $sdkRoot"
New-Item -ItemType Directory -Force -Path $sdkRoot | Out-Null

if (-not (Test-Path (Join-Path $latestDir "bin\sdkmanager.bat"))) {
    Write-Host "Downloading command-line tools..."
    Invoke-WebRequest -Uri $zipUrl -OutFile $tmpZip -UseBasicParsing
    $extractTmp = Join-Path $env:TEMP "android-cmdline-extract"
    if (Test-Path $extractTmp) { Remove-Item $extractTmp -Recurse -Force }
    Expand-Archive -Path $tmpZip -DestinationPath $extractTmp -Force
    New-Item -ItemType Directory -Force -Path $latestDir | Out-Null
    Move-Item -Path (Join-Path $extractTmp "cmdline-tools\*") -Destination $latestDir -Force
    Remove-Item $tmpZip -Force -ErrorAction SilentlyContinue
    Remove-Item $extractTmp -Recurse -Force -ErrorAction SilentlyContinue
}

$sdkmanager = Join-Path $latestDir "bin\sdkmanager.bat"
$env:ANDROID_HOME = $sdkRoot
$env:ANDROID_SDK_ROOT = $sdkRoot

Write-Host "Accepting SDK licenses..."
$yes = ("y`n" * 64)
$yes | & $sdkmanager --sdk_root=$sdkRoot --licenses | Out-Host

Write-Host "Installing SDK packages (may take several minutes)..."
$packages = @(
    "platform-tools",
    "platforms;android-35",
    "build-tools;35.0.0"
)
& $sdkmanager --sdk_root=$sdkRoot @packages

$localProps = Join-Path (Split-Path -Parent $PSScriptRoot) "android\local.properties"
$sdkEsc = $sdkRoot -replace '\\', '/'
"sdk.dir=$sdkEsc" | Set-Content -Path $localProps -Encoding ASCII
Write-Host "Wrote $localProps"
Write-Host "ANDROID_SDK_ROOT=$sdkRoot"
