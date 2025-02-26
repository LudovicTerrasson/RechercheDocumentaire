# Vérification et installation de Python 3
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python 3 n'est pas installé. Veuillez l'installer manuellement depuis https://www.python.org/downloads/"
    exit 1
} else {
    Write-Host "Python 3 est déjà installé."
}

# Vérification et installation de Java 8
$javaVersion = java -version 2>&1
if ($javaVersion -notmatch "1.8") {
    Write-Host "Java 8 n'est pas installé ou la version est incorrecte. Veuillez l'installer manuellement depuis https://adoptium.net/"
    exit 1
} else {
    Write-Host "Java 8 est déjà installé."
}

# Vérification si l'environnement virtuel existe déjà
if (-Not (Test-Path "venv")) {
    Write-Host "Création d'un nouvel environnement virtuel..."
    python -m venv venv
} else {
    Write-Host "L'environnement virtuel existe déjà."
}

# Vérification et installation de Tesseract
if (-Not (Get-Command tesseract -ErrorAction SilentlyContinue)) {
    Write-Host "Tesseract n'est pas installé. Téléchargement et installation..."
    Invoke-WebRequest -Uri "https://github.com/UB-Mannheim/tesseract/wiki" -OutFile "tesseract_installer.exe"
    Start-Process -Wait -FilePath "tesseract_installer.exe" -ArgumentList "/quiet"
    Remove-Item "tesseract_installer.exe"
} else {
    Write-Host "Tesseract est déjà installé."
}

# Configuration de la variable d'environnement TESSDATA_PREFIX
$env:TESSDATA_PREFIX = "C:\Program Files\Tesseract-OCR\"
Write-Host "La variable d'environnement TESSDATA_PREFIX a été définie sur : $env:TESSDATA_PREFIX"

# Vérification du fichier de langue français (fra.traineddata)
if (-Not (Test-Path "$env:TESSDATA_PREFIX\tessdata\fra.traineddata")) {
    Write-Host "Le fichier de langue français (fra.traineddata) est manquant. Téléchargement..."
    Invoke-WebRequest -Uri "https://github.com/tesseract-ocr/tessdata/raw/master/fra.traineddata" -OutFile "$env:TESSDATA_PREFIX\tessdata\fra.traineddata"
} else {
    Write-Host "Le fichier de langue français est déjà installé."
}

# Activation de l'environnement virtuel
Write-Host "Activation de l'environnement virtuel..."
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
. .\venv\Scripts\Activate

# Mise à jour de pip dans l'environnement virtuel
Write-Host "Mise à jour de pip..."
pip install --upgrade pip

# Vérification et installation de tkinter
Write-Host "Vérification de tkinter..."
try {
    python -c "import tkinter"
} catch {
    Write-Host "Tkinter non trouvé. Assurez-vous d'avoir installé la version complète de Python."
}

# Installation des dépendances Python
Write-Host "Installation des dépendances..."
pip install -r requirements.txt

# Vérification et installation de Solr
if (-Not (Test-Path "C:\solr")) {
    Write-Host "Solr n'est pas installé. Téléchargement et installation..."
    Invoke-WebRequest -Uri "https://downloads.apache.org/lucene/solr/8.11.2/solr-8.11.2.zip" -OutFile "solr.zip"
    Expand-Archive -Path "solr.zip" -DestinationPath "C:\solr"
    Remove-Item "solr.zip"
} else {
    Write-Host "Solr est déjà installé."
}

# Vérification si le port 8983 est utilisé
$portCheck = netstat -ano | Select-String ":8983"
if ($portCheck) {
    Write-Host "Erreur : Le port 8983 est déjà utilisé. Solr ne peut pas démarrer."
    exit 1
} else {
    Write-Host "Démarrage de Solr..."
    Start-Process -NoNewWindow -FilePath "C:\solr\bin\solr.cmd" -ArgumentList "start"
}

# Attendre quelques secondes pour le démarrage complet de Solr
Write-Host "Attente de 5 secondes..."
Start-Sleep -Seconds 5

# Création du core pdf_index
Write-Host "Création du core 'pdf_index'..."
Start-Process -NoNewWindow -FilePath "C:\solr\bin\solr.cmd" -ArgumentList "create -c pdf_index"

# Vérification du démarrage de Solr
Write-Host "Vérification de l'état de Solr..."
Invoke-WebRequest -Uri "http://localhost:8983/solr/admin/cores?action=STATUS&core=pdf_index" -UseBasicParsing

# Désactivation de l'environnement virtuel (facultatif)
deactivate

Write-Host "Installation terminée !"
