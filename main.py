import fitz  # PyMuPDF pour PDF
import os
import requests
from docx import Document
import tkinter as tk
from tkinter import Tk, filedialog, Button, Label, Entry, Listbox, Scrollbar, END, BOTH, RIGHT, LEFT, Y, ttk, IntVar, Frame, Toplevel
import pandas as pd
import threading
import time
from datetime import datetime
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

import json
import time

# Fonction pour enregistrer l'historique des indexations
def save_indexation_history(stats, source_dir, elapsed_time, indexation_time):
    # Créer un résumé de l'indexation
    indexation_summary = {
        "date": time.strftime(indexation_time),
        "dossier": source_dir,
        "nouveaux_documents": stats['new'],
        "documents_inchanges": stats['unchanged'],
        "documents_modifies": stats['modified'],
        "documents_deplaces": stats['moved'],
        "temps_total": elapsed_time 
    }

    # Charger l'historique existant, ou en créer un nouveau s'il n'existe pas
    try:
        with open('indexation_history.json', 'r') as f:
            history = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        history = []

    # Ajouter l'indexation à l'historique
    history.append(indexation_summary)

    # Sauvegarder l'historique mis à jour
    with open('indexation_history.json', 'w') as f:
        json.dump(history, f, indent=4)

    print("✅ Historique des indexations mis à jour !")

import json

def display_indexation_history():
    try:
        with open('indexation_history.json', 'r') as f:
            history = json.load(f)

        history_listbox.delete(0, END)  # Vider la Listbox avant d'ajouter les nouvelles entrées
        
        for entry in reversed(history):
            # Ajouter chaque ligne dans la Listbox séparément
            history_listbox.insert(END, f"Indexation effectuée le {entry['date']}")
            history_listbox.insert(END, f"- Dossier : {entry['dossier']}")
            history_listbox.insert(END, f"- {entry['nouveaux_documents']} nouveaux documents indexés.")
            history_listbox.insert(END, f"- {entry['documents_inchanges']} documents inchangés.")
            history_listbox.insert(END, f"- {entry['documents_modifies']} documents modifiés.")
            history_listbox.insert(END, f"- {entry['documents_deplaces']} documents déplacés.")
            history_listbox.insert(END, f"- Temps total : {entry['temps_total']} secondes.")
            history_listbox.insert(END, "")  # Ligne vide pour séparer les entrées
            
    except (FileNotFoundError, json.JSONDecodeError):
        history_listbox.insert(END, "Aucune indexation enregistrée.")




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

    elapsed_time = time.time() - start_time
    indexation_time = datetime.now().strftime('%d/%m/%Y à %H:%M')
    source_dir = os.path.dirname(files_to_index[0])


    # Affichage supplémentaire du récapitulatif final à la fin de l'indexation
    print(f"\nRésumé de l'indexation :")
    print(f"🗓️ Date de l'indexation : {indexation_time}")
    print(f"📂 Dossier indexé : {source_dir}")
    print(f"✅ Nouveaux fichiers indexés : {stats['new']}")
    print(f"📁 Fichiers inchangés : {stats['unchanged']}")
    print(f"🔄 Fichiers modifiés : {stats['modified']}")
    print(f"📂 Fichiers déplacés : {stats['moved']}")
    print(f"Temps total : {int(elapsed_time // 60)}m {int(elapsed_time % 60)}s")

    # Sauvegarder l'historique une fois l'indexation terminée
    save_indexation_history(stats, source_dir, elapsed_time, indexation_time)
    # Afficher l'historique mis à jour
    display_indexation_history()

    

# Fonction de recherche Solr
def search_solr():
    keywords = [entry.get().strip() for entry in keyword_entries if entry.get().strip()]
    if not keywords:
        info_label.config(text="❌ Veuillez entrer au moins un mot-clé.")
        return

    # Vérifier si la case "Recherche floue" est cochée
    if is_fuzzy_search.get():
        if is_or_search.get():  # Si la case "OU" est cochée
            solr_query = " OR ".join([f'content:*{keyword}*' for keyword in keywords])  # Recherche avec OR
        else:
            solr_query = " AND ".join([f'content:*{keyword}*' for keyword in keywords])  # Recherche avec AND
    else:
        if is_or_search.get():  # Si la case "OU" est cochée
            solr_query = " OR ".join([f'content:"{keyword}"' for keyword in keywords])  # Recherche avec OR
        else:
            solr_query = " AND ".join([f'content:"{keyword}"' for keyword in keywords])  # Recherche avec AND

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

        # Calculer la ligne et la colonne pour le nouvel élément
        row = len(keyword_entries) // 3  # Calcule la ligne
        column = len(keyword_entries) % 3  # Calcule la colonne

        # Ajouter le champ dans la grille
        new_entry.grid(row=row, column=column, padx=10, pady=2, sticky="ew")

        # Ajouter le nouvel champ à la liste
        keyword_entries.append(new_entry)  # Ajout à la fin de la liste
    else:
        info_label.config(text="❌ Vous avez atteint le nombre maximum de 15 mots-clés.")


# Fonction pour supprimer un champ de mot-clé
def remove_keyword_entry():
    if len(keyword_entries) > 3:
        entry_to_remove = keyword_entries.pop()
        entry_to_remove.destroy()  # Supprime le champ de l'interface
    else:
        info_label.config(text="❌ Vous devez conserver au moins 3 champs de mots-clés.")

# Fonction pour afficher une info-bulle
def show_info_message(message):
    # Fenêtre popup pour afficher les détails
    top = Toplevel()
    top.title("Information")
    top.geometry("400x250")
    
    label = Label(top, text=message, wraplength=280, justify="left")
    label.pack(pady=20)
    
    button = Button(top, text="Fermer", command=top.destroy)
    button.pack()

# Interface Tkinter
root = Tk()
root.title("Recherche et Indexation de Documents")

root.columnconfigure(0, weight=1)  # Laisser la colonne s'étendre
root.rowconfigure(0, weight=1)  # Laisser la première ligne s'étendre
root.rowconfigure(1, weight=1)
root.rowconfigure(2, weight=1)
root.rowconfigure(3, weight=1)
root.rowconfigure(4, weight=1)
root.rowconfigure(5, weight=1)
root.rowconfigure(6, weight=1)
root.rowconfigure(7, weight=1)
root.rowconfigure(8, weight=1)
root.rowconfigure(9, weight=1)
root.rowconfigure(10, weight=1)
root.rowconfigure(11, weight=1)
root.rowconfigure(12, weight=1)

# Indexation de fichiers label et bouton
Label(root, text="Indexation de fichiers :").grid(row=0, column=0, pady=10, padx=10, sticky="nsew")
button_frame = Frame(root)
button_frame.grid(row=1, column=0, pady=10, padx=10)

index_button = Button(button_frame, text="Sélectionner un répertoire pour indexation", command=index_directory)
index_button.pack(padx=10, pady=10)  # pack() le centre automatiquement


# Progressbar label et progressbar
progressbar_label = Label(root, text="Sélectionner un dossier pour démarrer une nouvelle indexation")
progressbar_label.grid(row=2, column=0, pady=10, padx=10, sticky="nsew")
progressbar = ttk.Progressbar(root, orient="horizontal", length=300, mode="determinate")
progressbar.grid(row=3, column=0, pady=10, padx=10, sticky="nsew")

# Créer un Frame pour contenir l'historique
history_frame = Frame(root)
history_frame.grid(row=4, column=0, padx=10, pady=10, sticky="nsew")  # Utilise grid ici

# Ajouter le label à la frame de l'historique
Label(history_frame, text="Historique des indexations :").grid(row=0, column=0, pady=10, padx=10, sticky="nsew")

# Configurer la grille pour que les éléments se développent
root.grid_rowconfigure(0, weight=0)  # Laisser la ligne 4 (l'historique) s'étendre
root.grid_columnconfigure(1, weight=1)  # Laisser la colonne 0 s'étendre

history_listbox = tk.Listbox(history_frame, height=10, width=50)
history_listbox.grid(row=1, column=0, sticky="nsew")  # Utiliser grid pour lier le listbox

# Ajouter la scrollbar qui s'ajuste à la hauteur de la Listbox
history_scrollbar = Scrollbar(history_frame, orient="vertical", command=history_listbox.yview)
history_scrollbar.grid(row=1, column=1, sticky="ns")  # La scrollbar à droite
history_listbox.config(yscrollcommand=history_scrollbar.set)

# Centrer la Listbox et la scrollbar dans leur frame
history_frame.grid_columnconfigure(0, weight=1)  # La colonne contenant la Listbox s'étend
history_frame.grid_columnconfigure(1, weight=0)  # La colonne contenant la scrollbar ne s'étend pas
history_frame.grid_rowconfigure(1, weight=1)  # Permettre à la ligne contenant les widgets de se développer


# Entrée des mots-clés label
Label(root, text="Entrez jusqu'à 5 mots-clés pour la recherche :").grid(row=5, column=0, pady=10, padx=10, sticky="nsew")

# Création des champs de mots-clés dans un Frame
keyword_frame = Frame(root)
keyword_frame.grid(row=6, column=0, pady=10, padx=10, sticky="nsew")

# Création des 5 premiers champs de mots-clés et placement dans la grille
keyword_entries = [Entry(keyword_frame, width=50) for _ in range(5)]
for i, entry in enumerate(keyword_entries):
    row = i // 3  # Calcule la ligne
    column = i % 3  # Calcule la colonne
    entry.grid(row=row, column=column, padx=10, pady=2, sticky="nsew")

# Configurer la colonne pour qu'elle s'étende proportionnellement
for col in range(3):
    keyword_frame.grid_columnconfigure(col, weight=1)

# Frame pour les boutons "Ajouter" et "Supprimer" les mots-clés
button_frame = Frame(root)
button_frame.grid(row=7, column=0, pady=5, padx=10)

# Sous-frame pour centrer les boutons
inner_button_frame = Frame(button_frame)
inner_button_frame.pack()

# Ajouter un bouton pour permettre d'ajouter un mot-clé
add_button = Button(inner_button_frame, text="Ajouter un mot-clé", command=add_keyword_entry)
add_button.pack(side="left", padx=5, pady=5)

# Bouton pour supprimer un mot-clé
remove_button = Button(inner_button_frame, text="Supprimer un mot-clé", command=remove_keyword_entry)
remove_button.pack(side="left", padx=5, pady=5)


# Frame pour la case à cocher et le bouton "i"
checkbox_frame = Frame(root)
checkbox_frame.grid(row=8, column=0, pady=5, padx=10, sticky="ew")

# Centrer le contenu du checkbox_frame
checkbox_frame.grid_columnconfigure(0, weight=1)  # La colonne contenant la case à cocher s'étend pour centrer
checkbox_frame.grid_columnconfigure(1, weight=1)  # La colonne contenant le bouton "i" s'étend également pour centrer
checkbox_frame.grid_rowconfigure(0, weight=1)  # La ligne s'étend

# Case à cocher pour activer/désactiver la recherche floue
is_fuzzy_search = IntVar()
fuzzy_search_checkbox = ttk.Checkbutton(checkbox_frame, text="Recherche floue", variable=is_fuzzy_search)
fuzzy_search_checkbox.grid(row=0, column=0, padx=5, sticky="e")  # Aligné à gauche mais dans une grille qui s'étend

# Ajouter un petit "i" pour plus d'infos à côté de la case à cocher
info_button = Button(checkbox_frame, text="i", command=lambda: show_info_message(
         "La recherche floue permet de trouver, en plus des mots-clés exacts, les mots qui contiennent ces mots-clés.\n" "\nExemple : si vous cherchez 'chat', cela retournera 'chats', mais aussi 'achat', etc. " "Si vous cherchez 'Dupont', cela retournera également 'A.Dupont'."))
info_button.grid(row=0, column=1, padx=5, pady=5, sticky="w")  # Aligné à droite mais dans une grille qui s'étend

# Case à cocher pour activer/désactiver la recherche avec OU
is_or_search = IntVar()
or_search_checkbox = ttk.Checkbutton(checkbox_frame, text="Recherche avec OU", variable=is_or_search)
or_search_checkbox.grid(row=1, column=0, padx=5, pady=5, sticky="e")  # La nouvelle case juste en dessous

# Ajouter un petit "i" pour plus d'infos à côté de la case à cocher "Recherche avec OU"
info_button_or = Button(checkbox_frame, text="i", command=lambda: show_info_message(
         "La recherche avec 'OU' permet de trouver des documents qui contiennent au moins un des mots-clés.\n" "\nExemple : si vous cherchez 'chat' OU 'chien', cela retournera les documents contenant 'chat' ou 'chien', ou les deux."))
info_button_or.grid(row=1, column=1, padx=5, pady=5, sticky="w")  # Aligné à droite de la nouvelle case à cocher




# Bouton de recherche
search_frame = Frame(root)
search_frame.grid(row=9, column=0, pady=10, padx=10)

search_button = Button(search_frame, text="Rechercher", command=search_solr)
search_button.pack(padx=10, pady=10)


# Label d'info
info_label = Label(root, text="", fg="white")
info_label.grid(row=10, column=0, pady=5, padx=10, sticky="nsew")

# Frame pour les résultats
result_frame = Frame(root)
result_frame.grid(row=11, column=0, padx=10, pady=10, sticky="nsew")  # Frame qui s'étend

# Ajouter un label pour indiquer "Résultats :"
Label(result_frame, text="Résultats :").grid(row=0, column=0, pady=10, padx=10, sticky="nsew")

# Configurer la ligne et la colonne pour qu'elles s'étendent proportionnellement
result_frame.grid_rowconfigure(0, weight=0)  # Le label ne doit pas prendre trop d'espace
result_frame.grid_rowconfigure(1, weight=1)  # La listbox doit occuper l'espace restant

# Scrollbar pour les résultats
scrollbar = Scrollbar(result_frame, orient="vertical")

# Listbox pour les résultats
result_listbox = Listbox(result_frame, yscrollcommand=scrollbar.set)
result_listbox.grid(row=1, column=0, sticky="nsew")  # Étendre la Listbox dans la grille

# Configurer la scrollbar pour la Listbox
scrollbar.grid(row=1, column=1, sticky="ns")  # Scrollbar à droite
scrollbar.config(command=result_listbox.yview)

# Centrer la Listbox et la scrollbar
result_frame.grid_columnconfigure(0, weight=1)  # Permettre à la première colonne de s'étendre
result_frame.grid_columnconfigure(1, weight=0)  # La deuxième colonne (pour la scrollbar) ne doit pas s'étendre
result_frame.grid_rowconfigure(0, weight=1)  # Permettre à la ligne de se développer


open_frame = Frame(root)
open_frame.grid(row=12, column=0, pady=10, padx=10)

open_button = Button(open_frame, text="Ouvrir fichier sélectionné", command=open_file)
open_button.pack(padx=10, pady=10)


root.mainloop()





