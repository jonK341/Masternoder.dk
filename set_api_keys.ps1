# PowerShell script to set API keys in .env file
param(
    [string]$RunwayML = "",
    [string]$PikaLabs = "",
    [string]$StabilityAI = "",
    [string]$OpenAI = ""
)

$envFile = ".env"

if (-not (Test-Path $envFile)) {
    if (Test-Path ".env.example") {
        Copy-Item ".env.example" $envFile
        Write-Host "Created .env from .env.example" -ForegroundColor Green
    } else {
        Write-Host "Error: .env.example not found" -ForegroundColor Red
        exit 1
    }
}

Write-Host "`n=== Configure API Keys ===" -ForegroundColor Cyan
Write-Host ""

# Read current .env content
$content = Get-Content $envFile -Raw

# Function to update or add a key
function Update-EnvKey {
    param($key, $value, $description)
    
    if ($value -ne "") {
        # Check if key exists
        if ($content -match "^$key=.*$") {
            # Replace existing
            $content = $content -replace "^$key=.*$", "$key=$value"
            Write-Host "✓ Updated $key" -ForegroundColor Green
        } else {
            # Add new key
            $content += "`n$key=$value"
            Write-Host "✓ Added $key" -ForegroundColor Green
        }
    } else {
        Write-Host "- Skipped $key ($description)" -ForegroundColor Yellow
    }
}

# Prompt for keys if not provided as parameters
if ($RunwayML -eq "" -and $PikaLabs -eq "" -and $StabilityAI -eq "" -and $OpenAI -eq "") {
    Write-Host "Enter API keys (press Enter to skip):" -ForegroundColor Yellow
    Write-Host ""
    
    $RunwayML = Read-Host "RunwayML API Key (https://runwayml.com/api)"
    $PikaLabs = Read-Host "Pika Labs API Key (https://pika.art/api)"
    $StabilityAI = Read-Host "Stability AI API Key (https://platform.stability.ai/)"
    $OpenAI = Read-Host "OpenAI API Key (https://platform.openai.com/api-keys)"
}

# Update keys
Update-EnvKey "RUNWAYML_API_KEY" $RunwayML "For RunwayML video generation"
Update-EnvKey "PIKA_LABS_API_KEY" $PikaLabs "For Pika Labs video generation"
Update-EnvKey "STABILITY_AI_API_KEY" $StabilityAI "For Stable Video Diffusion"
Update-EnvKey "OPENAI_API_KEY" $OpenAI "For script generation"

# Write updated content
Set-Content -Path $envFile -Value $content -NoNewline

Write-Host ""
Write-Host "✓ .env file updated!" -ForegroundColor Green
Write-Host ""
Write-Host "To deploy to server, run:" -ForegroundColor Cyan
Write-Host '  python configure_api_keys.py --server' -ForegroundColor White

