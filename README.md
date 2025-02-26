PROJET : RECHERCHE DOCUMENTAIRE

DESCRIPTION

Ce projet permet d'indexer et de rechercher des documents (PDF, DOCX, etc.) en utilisant Apache Solr. Il inclut un script d'installation et de configuration pour simplifier le déploiement.

ETAPE 1 : Cloner le repository GitHub

git clone <URL_DU_REPO>
cd <NOM_DU_REPO>

ETAPE 2 : Exécuter le script d'installation

./setup.sh

Ce script :
Vérifie et installe les dépendances nécessaires (Python, Java 8, Solr)
Crée et active un environnement virtuel
Installe les bibliothèques Python requises
Installe et configure Apache Solr
Crée un core Solr pour l'indexation des documents

ETAPE 3 : Utilisation

source venv/bin/activate
python main.py

FIN
