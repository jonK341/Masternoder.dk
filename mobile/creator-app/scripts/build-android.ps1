# Build Super Encoder Android APK (requires JDK 17+ and Android SDK)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location $root

if (-not $env:JAVA_HOME) {
    $candidates = @(
        "C:\Program Files\Eclipse Adoptium\jdk-21*",
        "C:\Program Files\Eclipse Adoptium\jdk-17*",
        "C:\Program Files\Android\Android Studio\jbr"
    )
    foreach ($pattern in $candidates) {
        $hit = Get-Item $pattern -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($hit) {
            $env:JAVA_HOME = $hit.FullName
            break
        }
    }
}
if (-not $env:JAVA_HOME) {
    Write-Error "Set JAVA_HOME to JDK 17+ (e.g. winget install EclipseAdoptium.Temurin.17.JDK)"
}

Write-Host "JAVA_HOME=$env:JAVA_HOME"
npm run cap:sync
Set-Location android
.\gradlew.bat assembleRelease
Write-Host "APK: android\app\build\outputs\apk\release\app-release-unsigned.apk"
