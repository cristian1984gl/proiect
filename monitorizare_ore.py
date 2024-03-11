import os
import csv
import sqlite3
from datetime import datetime, timedelta
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import shutil

class Utilizator:
    def __init__(self, id, nume, prenume, companie, id_manager):
        self.id = id
        self.nume = nume
        self.prenume = prenume
        self.companie = companie
        self.id_manager = id_manager

class Administrator:
    def __init__(self, conexiune_db):
        self.conexiune_db = conexiune_db

    def inregistreaza_utilizator(self, id, nume, prenume, companie, id_manager):
        cursor = self.conexiune_db.cursor()
        cursor.execute("INSERT INTO utilizatori (ID, Nume, Prenume, Companie, IdManager) VALUES (?, ?, ?, ?, ?)",
                       (id, nume, prenume, companie, id_manager))
        self.conexiune_db.commit()
        print("Utilizator înregistrat cu succes!")

class Porta:
    def __init__(self, conexiune_db, director_intrari, director_backup_intrari):
        self.conexiune_db = conexiune_db
        self.director_intrari = director_intrari
        self.director_backup_intrari = director_backup_intrari

    def citeste_fisiere_intrari(self):
        fisiere_intrari = os.listdir(self.director_intrari)
        for fisier in fisiere_intrari:
            if fisier.startswith('Poarta') and fisier.endswith('.csv'):
                nume_porta = fisier.split('.')[0]
                self.proceseaza_fisier_intrare(fisier, nume_porta)

    def proceseaza_fisier_intrare(self, nume_fisier, nume_porta):
        cale_completa = os.path.join(self.director_intrari, nume_fisier)
        try:
            with open(cale_completa, newline='') as csvfile:
                cititor_csv = csv.reader(csvfile)
                for rand in cititor_csv:
                    id_persoana, ora_validare, sens = rand
                    self.inregistreaza_acces(nume_porta, id_persoana, ora_validare, sens)
        except Exception as e:
            print(f"Eroare la procesarea fisierului {nume_fisier}: {e}")

        cale_backup = os.path.join(self.director_backup_intrari, nume_fisier)
        shutil.move(cale_completa, cale_backup)

    def inregistreaza_acces(self, nume_porta, id_persoana, ora_validare, sens):
        cursor = self.conexiune_db.cursor()
        cursor.execute("INSERT INTO access (NumePorta, IdPersoana, OraValidare, Sens) VALUES (?, ?, ?, ?)",
                       (nume_porta, id_persoana, ora_validare, sens))
        self.conexiune_db.commit()

def calculeaza_ore_lucrate(conexiune_db):
    cursor = conexiune_db.cursor()
    data_curenta = datetime.now().date()
    data_ieri = data_curenta - timedelta(days=1)
    cursor.execute("SELECT IdPersoana, OraValidare, Sens FROM access WHERE DATE(OraValidare) = ?", (data_ieri,))
    intrari_ieșiri = cursor.fetchall()
    ore_lucrate = {}
    for intrare_iesire in intrari_ieșiri:
        id_persoana, ora_validare, sens = intrare_iesire
        if id_persoana not in ore_lucrate:
            ore_lucrate[id_persoana] = timedelta()
        elif sens == 'in':
            ora_intrare = datetime.strptime(ora_validare, '%Y-%m-%d %H:%M:%S')
        elif sens == 'out' and id_persoana in ore_lucrate:
            ora_iesire = datetime.strptime(ora_validare, '%Y-%m-%d %H:%M:%S')
            ore_lucrate[id_persoana] += ora_iesire - ora_intrare

    for id_persoana, ore in ore_lucrate.items():
        if ore < timedelta(hours=8):
            trimite_email_managerului(id_persoana)

    with open(f'{data_curenta}_chiulangii.csv', 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        csv_writer.writerow(['Nume', 'OreLucrate'])
        for id_persoana, ore in ore_lucrate.items():
            csv_writer.writerow([id_persoana, ore.total_seconds() / 3600])

    with open(f'{data_curenta}_chiulangii.txt', 'w') as txtfile:
        for id_persoana, ore in ore_lucrate.items():
            txtfile.write(f'{id_persoana},{ore.total_seconds() / 3600}\n')

def trimite_email_managerului(id_persoana):
    # Implementează codul pentru trimiterea emailului către managerul angajatului
    pass

# Conectare la baza de date
conexiune_db = sqlite3.connect('baza_de_date.db')

# Creare tabel pentru utilizatori
cursor = conexiune_db.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS utilizatori
                  (ID TEXT PRIMARY KEY,
                   Nume TEXT,
                   Prenume TEXT,
                   Companie TEXT,
                   IdManager TEXT)''')

# Creare tabel pentru acces
cursor.execute('''CREATE TABLE IF NOT EXISTS access
                  (NumePorta TEXT,
                   IdPersoana TEXT,
                   OraValidare TEXT,
                   Sens TEXT)''')

# Directorul pentru intrari și backup_intrari
director_intrari = 'intrari'
director_backup_intrari = 'backup_intrari'

if not os.path.exists(director_backup_intrari):
    os.makedirs(director_backup_intrari)

porta = Porta(conexiune_db, director_intrari, director_backup_intrari)
porta.citeste_fisiere_intrari()

calculeaza_ore_lucrate(conexiune_db)

# Închidem conexiunea cu baza de date
conexiune_db.close()
