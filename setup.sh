#!/bin/bash

# Vérification et installation de Homebrew
if ! command -v brew &> /dev/null
then
    echo "Homebrew n'est pas installé. Installation de Homebrew..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
else
    echo "Homebrew est déjà installé."
fi

# Vérification et installation de Python 3
if ! command -v python3 &> /dev/null
then
    echo "Python 3 n'est pas installé. Installation de Python 3..."
    brew install python
else
    echo "Python 3 est déjà installé."
fi

# Vérification et installation de Java 8
if ! java -version &> /dev/null || [[ $(java -version 2>&1) != *"1.8"* ]]
then
    echo "Java 8 n'est pas installé ou la version est incorrecte. Installation de Java 8..."
    brew install openjdk@8
else
    echo "Java 8 est déjà installé."
fi

# Vérification si l'environnement virtuel existe déjà
if [ ! -d "venv" ]; then
    echo "Création d'un nouvel environnement virtuel..."
    python3 -m venv venv
else
    echo "L'environnement virtuel existe déjà."
fi

# Activation de l'environnement virtuel
source venv/bin/activate

# Mettre à jour pip dans l'environnement virtuel
echo "Mise à jour de pip dans l'environnement virtuel..."
pip install --upgrade pip

# Vérification et installation de tkinter si nécessaire
echo "Vérification de tkinter..."
python3 -c "import tkinter" 2>/dev/null || {
  echo "tkinter non trouvé, installation via brew..."
  brew install python-tk
}

# Installation des dépendances du projet dans l'environnement virtuel
echo "Installation des dépendances..."
pip install -r requirements.txt

# Installation de Solr
echo "Installation de Solr..."
brew install solr

# Vérification si le port 8983 est déjà utilisé
echo "Vérification du port 8983..."
if lsof -i :8983; then
  echo "Erreur : Le port 8983 est déjà utilisé. Solr ne peut pas démarrer sur ce port."
  exit 1
else
  echo "Démarrage de Solr sur le port 8983..."
  solr start
fi

# Attendre quelques secondes pour que Solr démarre correctement
echo "Attente de 5 secondes pour le démarrage complet de Solr..."
sleep 5

# Création du core pdf_index
echo "Création du core 'pdf_index'..."
solr create -c pdf_index

# Vérification du démarrage de Solr
echo "Vérification de l'état de Solr..."
curl "localhost:8983/solr/admin/cores?action=STATUS&core=pdf_index"

# Désactivation de l'environnement virtuel (facultatif)
deactivate

echo "Installation terminée !"

