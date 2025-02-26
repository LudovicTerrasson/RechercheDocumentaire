import fitz  # PyMuPDF pour PDF
import os
import requests
from docx import Document
from tkinter import Tk, filedialog, Button, Label, Entry, Listbox, Scrollbar, END, BOTH, RIGHT, Y, ttk, IntVar, Frame
import pandas as pd
import threading
import time
import pytesseract
from pdf2image import convert_from_path
import json

def load_indexed_files():
    if os.path.exists('indexed_files.json'):
        with open('indexed_files.json', 'r') as f:
            indexed_files_data = json.load(f)
        return indexed_files_data
    else:
        return {}

def save_indexed_files():
    with open('indexed_files.json', 'w') as f:
        json.dump(indexed_files, f, indent=4)

indexed_files = load_indexed_files()

SOLR_URL = "http://localhost:8983/solr/pdf_index/update?commit=true"
SOLR_SEARCH_URL = "http://localhost:8983/solr/pdf_index/select?q={}"

# Stocker les résultats pour ouvrir les fichiers
search_results = []

# Fonction pour extraire le texte d'un PDF
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        page_text = page.get_text()
        if page_text.strip():  # Si le texte est sélectionnable
            text += page_text
        else:
            # Si aucun texte sélectionnable, on utilise OCR
            images = convert_from_path(pdf_path, first_page=page.number+1, last_page=page.number+1)
            for image in images:
                text += pytesseract.image_to_string(image, lang='fra')
    return text

# Fonction pour extraire le texte d'un DOCX
def extract_text_from_docx(docx_path):
    doc = Document(docx_path)
    return "\n".join([para.text for para in doc.paragraphs])

# Fonction pour extraire le texte d'un fichier Excel
def extract_text_from_excel(excel_path):
    df = pd.read_excel(excel_path)
    return df.to_string(index=False)

def index_document(file_path, progressbar, total_files, file_index, start_time, progress_label, stats):
    try:
        last_modified = os.path.getmtime(file_path)

        # Vérifie si le fichier a déjà été indexé et non modifié
        if file_path in indexed_files and indexed_files[file_path] == last_modified:
            stats['unchanged'] += 1
            print(f"📄 {file_path} déjà indexé et non modifié, ignoré.")
        else:
            # Traiter les fichiers modifiés ou non indexés
            if file_path.endswith('.pdf'):
                text = extract_text_from_pdf(file_path)
            elif file_path.endswith('.docx') or file_path.endswith('.doc'):
                text = extract_text_from_docx(file_path)
            elif file_path.endswith('.xlsx'):
                text = extract_text_from_excel(file_path)
            else:
                print(f"⚠️ Format non pris en charge : {file_path}")
                return

            data = {
                "id": os.path.basename(file_path),
                "content": text,
                "title": os.path.basename(file_path),
                "path": os.path.abspath(file_path)
            }

            response = requests.post(SOLR_URL, json=[data])
            if response.status_code == 200:
                print(f"✅ Document indexé : {file_path}")
                indexed_files[file_path] = last_modified
                save_indexed_files() 
                stats['new'] += 1
            else:
                print(f"❌ Erreur d'indexation pour {file_path}: {response.status_code}")

        # Calcul du temps restant estimé, même pour les fichiers inchangés
        elapsed_time = time.time() - start_time
        avg_time_per_file = elapsed_time / (file_index + 1)
        remaining_files = total_files - (file_index + 1)
        estimated_remaining_time = avg_time_per_file * remaining_files

        minutes_left = int(estimated_remaining_time // 60)
        seconds_left = int(estimated_remaining_time % 60)
        progress_label.config(text=(
            f"Temps restant estimé : {minutes_left}m {seconds_left}s\n"
            f"✅ Nouveaux fichiers indexés : {stats['new']}\n"
            f"📁 Fichiers inchangés : {stats['unchanged']}\n"
            f"🔄 Fichiers modifiés : {stats['modified']}\n"
            f"📂 Fichiers déplacés : {stats['moved']}"
        ))

        progressbar['value'] = (file_index + 1) * 100 / total_files

    except Exception as e:
        print(f"❌ Erreur lors de l'indexation de {file_path}: {e}")


# Fonction pour parcourir le dossier et indexer tous les fichiers
def index_directory():
    source_dir = filedialog.askdirectory()
    if not source_dir:
        return

    files_to_index = []
    for root_dir, _, files in os.walk(source_dir):
        for file in files:
            file_path = os.path.join(root_dir, file)
            files_to_index.append(file_path)

    total_files = len(files_to_index)
    progressbar_label.config(text="Indexation en cours...")
    progressbar['value'] = 0
    progressbar['maximum'] = 100

    start_time = time.time()

    threading.Thread(target=start_indexing, args=(files_to_index, total_files, start_time)).start()

# Fonction pour l'indexation dans un thread
def start_indexing(files_to_index, total_files, start_time):
    stats = {'new': 0, 'unchanged': 0, 'modified': 0, 'moved': 0}
    for index, file_path in enumerate(files_to_index):
        index_document(file_path, progressbar, total_files, index, start_time, progressbar_label, stats)

    time.sleep(2)  # Délai de 2 secondes pour laisser le temps à l'utilisateur de voir les statistiques
    progressbar_label.config(text="Indexation terminée !")
    print("✅ Indexation terminée !")

# Fonction de recherche Solr
def search_solr():
    keywords = [entry.get().strip() for entry in keyword_entries if entry.get().strip()]
    if not keywords:
        info_label.config(text="❌ Veuillez entrer au moins un mot-clé.")
        return

    # Vérifier si la case "Recherche floue" est cochée
    if is_fuzzy_search.get():
        solr_query = " AND ".join([f'content:*{keyword}*' for keyword in keywords])  # Ajoute les wildcards
    else:
        solr_query = " AND ".join([f'content:"{keyword}"' for keyword in keywords])

    search_url = SOLR_SEARCH_URL.format(f"{solr_query}&rows=9999")
    response = requests.get(search_url)
    results = response.json()

    global search_results
    search_results = []
    result_listbox.delete(0, END)

    docs = results['response']['docs']
    num_results = len(docs)
    info_label.config(text=f"📄 Nombre de documents trouvés : {num_results}")

    if num_results > 20:
        info_label.config(text=f"📄 Nombre de documents trouvés : {num_results} ⚠️ Trop de résultats. Ajoutez un mot-clé supplémentaire.")

    if not docs:
        info_label.config(text="❌ Aucun résultat trouvé.")
        return

    for doc in docs:
        if 'title' in doc and 'path' in doc:
            path = doc['path'][0] if isinstance(doc['path'], list) else doc['path']
            search_results.append((doc['title'], path))
            result_listbox.insert(END, doc['title'])

# Fonction pour ouvrir un fichier sélectionné
def open_file():
    try:
        selected_index = result_listbox.curselection()[0]
        _, file_path = search_results[selected_index]

        if not os.path.exists(file_path):
            info_label.config(text=f"❌ Le fichier {file_path} n'existe pas.")
            return

        os.system(f'open "{file_path}"')
    except IndexError:
        info_label.config(text="❌ Aucun fichier sélectionné.")
    except Exception as e:
        info_label.config(text=f"❌ Erreur lors de l'ouverture : {e}")

# Fonction pour ajouter un nouvel espace pour un mot-clé
def add_keyword_entry():
    if len(keyword_entries) < 15:  # Limite à 15 mots-clés
        # Créer un nouvel champ de mot-clé
        new_entry = Entry(keyword_frame, width=50)
        new_entry.pack(pady=2, padx=10, fill="x")  # Ajouter au bas de la frame

        # Ajouter le nouvel champ à la liste
        keyword_entries.append(new_entry)  # Ajout à la fin de la liste
    else:
        info_label.config(text="❌ Vous avez atteint le nombre maximum de 15 mots-clés.")



# Interface Tkinter
root = Tk()
root.title("Recherche et Indexation de Documents")

root.columnconfigure(0, weight=1)
root.rowconfigure(1, weight=1)

Label(root, text="Indexation de fichiers :").pack(pady=10)
index_button = Button(root, text="Sélectionner un répertoire pour indexation", command=index_directory)
index_button.pack(pady=10)

progressbar_label = Label(root, text="Sélectionner un dossier pour démarrer une nouvelle indexation")
progressbar_label.pack(pady=10)
progressbar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
progressbar.pack(pady=10)

Label(root, text="Entrez jusqu'à 5 mots-clés pour la recherche :").pack(pady=10)

# Création d'un Frame pour contenir les champs de mots-clés
keyword_frame = Frame(root)
keyword_frame.pack(pady=10)

# Création des 5 premiers champs de mots-clés
keyword_entries = [Entry(keyword_frame, width=50) for _ in range(5)]
for entry in keyword_entries:
    entry.pack(pady=2, padx=10, fill="x")

# Ajouter un bouton pour permettre à l'utilisateur d'ajouter plus de champs de mots-clés
add_button = Button(root, text="Ajouter un mot-clé", command=add_keyword_entry)
add_button.pack(pady=5)

# Case à cocher pour activer/désactiver la recherche floue
is_fuzzy_search = IntVar()
fuzzy_search_checkbox = ttk.Checkbutton(root, text="Recherche floue", variable=is_fuzzy_search)
fuzzy_search_checkbox.pack(pady=5)

search_button = Button(root, text="Rechercher", command=search_solr)
search_button.pack(pady=10)

info_label = Label(root, text="", fg="white")
info_label.pack(pady=5)

result_frame = Listbox(root)
result_frame.pack(fill=BOTH, expand=True, padx=10, pady=10)

scrollbar = Scrollbar(result_frame, orient="vertical")
scrollbar.pack(side=RIGHT, fill=Y)

result_listbox = Listbox(result_frame, yscrollcommand=scrollbar.set)
result_listbox.pack(fill=BOTH, expand=True)
scrollbar.config(command=result_listbox.yview)

open_button = Button(root, text="Ouvrir fichier sélectionné", command=open_file)
open_button.pack(pady=10)

root.mainloop()




