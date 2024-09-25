import mysql.connector
import zipfile
import os,sys
import configparser

config = configparser.ConfigParser();config.read("../config.ini")

def files(path):
    for file in os.listdir(path):
        if os.path.isfile(os.path.join(path, file)):
            yield file

for file in files(config['WorkMode']['IternalStorage']):
    Database_Conn = mysql.connector.connect(host=config['mysql']['host'], port=config['mysql']['port'], user=config['mysql']['login'], password=config['mysql']['password'], database='galv_fb2index')
    Database_Cursor = Database_Conn.cursor()
    if file[-3:] == 'zip':
        print(file)
        arch = zipfile.ZipFile(f"{config['WorkMode']['IternalStorage']}/{file}", 'r')
        books = arch.namelist()
        for book in books:
            bookne = book[:-4] # тип book file name without extension, bookne
            if bookne.isdigit():
                Database_Cursor.execute(f"INSERT INTO ArchiveToBook VALUES ({bookne}, '{file[:-4]}')")
                Database_Conn.commit()
