from io import BytesIO
import os, sys, time

import requests
from urllib.request import urlretrieve
import zipfile

import mysql.connector
import configparser

def getBook(BookID, config):
    if config.getboolean('WorkMode', 'externalStorage') is True:
        flibusta_links = config['WorkMode']['externalStorageURLs'].split()

        alink = None
        for link in flibusta_links:
            try:
                requests.head(link, timeout=2)
                alink = link
                break
            except: pass

        if alink is None: return 10

        try:
            r = requests.get(f"{alink}/b/{BookID}/fb2", stream=True, timeout=15)
            r.raw.decode_content = True
        except: return 11

        book = None
        try:
            with zipfile.ZipFile(BytesIO(r.content), 'r') as zip_ref:
                for file in zip_ref.namelist():
                    if file[-3:] == 'fb2':
                        book = BytesIO(zip_ref.read(file))
                        break
        except: return 12
    
        if book is None: return 13
        else: return book

    else:
        Database_Conn = mysql.connector.connect(host=config['mysql']['host'], port=config['mysql']['port'], user=config['mysql']['login'], password=config['mysql']['password'], database='galv_fb2index')
        Database_Cursor = Database_Conn.cursor()
        bookarch = Database_Cursor.execute(f"SELECT ArchiveName FROM ArchiveToBook WHERE BookID = {BookID};")
        bookarch = Database_Cursor.fetchall()
        try: bookarch = bookarch[0][0]
        except: return 14
        
        book = None
        try:
            with zipfile.ZipFile(f"{config['WorkMode']['internalStorage']}/{bookarch}.zip", 'r') as zip_ref:
                for file in zip_ref.namelist():
                    if file == f"{BookID}.fb2":
                        book = BytesIO(zip_ref.read(file))
                        break
        except:return 15
    
        if book is None: return 16
        else: return book
    return 1
