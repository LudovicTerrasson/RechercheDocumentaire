PROJET : RECHERCHE DOCUMENTAIRE

DESCRIPTION

Ce projet permet d'indexer et de rechercher des documents (PDF, DOCX, etc.) en utilisant Apache Solr. Il inclut un script d'installation et de configuration pour simplifier le déploiement.

I_POUR MAC

Ouvrez le terminal

ETAPE 1 : Cloner le repository GitHub

git clone https://github.com/LudovicTerrasson/RechercheDocumentaire.git

cd RechercheDocumentaire

ETAPE 2 : Exécuter le script d'installation

./setup.sh

ETAPE 3 : Utilisation

source venv/bin/activate

python main.py

FIN

II_POUR WINDOWS

Ouvrez powershell en mode admin

ETAPE 1 : Cloner le repository GitHub

git clone https://github.com/LudovicTerrasson/RechercheDocumentaire.git

cd RechercheDocumentaire

ETAPE 2 : Exécuter le script d'installation

Set-ExecutionPolicy Unrestricted -Scope Process

.\setup.ps1


ETAPE 3 : Utilisation

.\venv\Scripts\Activate

python main.py

FIN
