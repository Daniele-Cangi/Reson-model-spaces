param(
    [Parameter(Mandatory = $true)]
    [string]$GitHubRepo,   # es: Daniele-Cangi/Reson-model-spaces
    [Parameter(Mandatory = $true)]
    [string]$HfSpaceRepo   # es: Nexus-Walker/Reson-model
)

$ErrorActionPreference = "Stop"

$gitHubUrl = "https://github.com/$GitHubRepo.git"
$hfUrl = "https://huggingface.co/spaces/$HfSpaceRepo"

if (git remote get-url github 2>$null) {
    git remote set-url github $gitHubUrl
} else {
    git remote add github $gitHubUrl
}

if (git remote get-url hfspace 2>$null) {
    git remote set-url hfspace $hfUrl
} else {
    git remote add hfspace $hfUrl
}

git push -u github main
git push -u hfspace main

Write-Host "Push completato su GitHub e Hugging Face Space."
