from io import BytesIO
import os, sys, time

import requests
from urllib.request import urlretrieve
import zipfile

from flask import Flask, abort, request, redirect, url_for, send_file
from flask import render_template
import service.placeholder

import mysql.connector
import configparser

app = Flask('Galvarda')

if True:
    MainConfigFile = 'config.ini'

@app.route('/lib', methods=['GET'])
@app.route('/lib/', methods=['GET'])
def MainPage():
    config = configparser.ConfigParser();config.read(MainConfigFile)
    Database_Conn = mysql.connector.connect(host=config['mysql']['host'], port=config['mysql']['port'], user=config['mysql']['login'], password=config['mysql']['password'], database='galv_fb2index')
    Database_Cursor = Database_Conn.cursor()
    
    content = {}
    book_count = Database_Cursor.execute('SELECT COUNT(*) FROM libbook;')
    book_count = Database_Cursor.fetchall()
    book_count = int(book_count[0][0])
    content['book_count'] = book_count

    Database_Cursor.close(); Database_Conn.close()
    return render_template('index.html', content = content)

@app.route('/lib/search/<SearchType>/<SearchReq>', methods=['GET'])
def SearchPage(SearchType=None, SearchReq=None):
    config = configparser.ConfigParser();config.read(MainConfigFile)
    Database_Conn = mysql.connector.connect(host=config['mysql']['host'], port=config['mysql']['port'], user=config['mysql']['login'], password=config['mysql']['password'], database='galv_fb2index')
    Database_Cursor = Database_Conn.cursor()

    books = []
    if SearchType == 'book':
        books_q = Database_Cursor.execute(f"SELECT libavtor.BookId, libbook.Title, libbook.Title1, libavtorname.lfm, libadd.Image, libadd.Annotation FROM libavtor, libbook, libavtorname, libadd WHERE libbook.Title LIKE '{str(SearchReq)}%' AND libbook.Deleted = 0 AND libbook.BookId = libavtor.BookId AND libavtor.AvtorId = libavtorname.AvtorId AND libavtor.BookId = libadd.BookID;")
    if SearchType == 'author':
        books_q = Database_Cursor.execute(f"SELECT libavtor.BookId, libbook.Title, libbook.Title1, libavtorname.lfm, libadd.Image, libadd.Annotation FROM libavtor, libbook, libavtorname, libadd WHERE libavtorname.lfm LIKE '%{str(SearchReq)}%' AND libavtorname.AvtorId = libavtor.AvtorId AND libavtor.BookId = libbook.BookId AND libavtor.BookId = libadd.BookID;")
    
    books_q = Database_Cursor.fetchall()
        
    content = {}
    for book in books_q:
        if book[4] is None: img = getattr(service.placeholder, 'img')
        else: img = book[4]
        if book[2] == '': subTitle = ''
        else: subTitle = f"[{book[2]}]"
        books.append({'ID' : book[0],
                      'Title1' : book[1],
                      'Title2' : subTitle,
                      'Image' : img,
                      'Annotation' : book[5],
                      'Author' : book[3]})
        
    content['SearchType'] = SearchType
    content['SearchReq'] = SearchReq
    content['books'] = books
    Database_Cursor.close(); Database_Conn.close()
    return render_template('search.html', content = content)

@app.route('/lib/search/', methods=['POST'])
@app.route('/lib/search', methods=['POST'])
def SearchRedir():
    if request.method == 'POST':
        return redirect(url_for('SearchPage', SearchType=request.form['SearchTypeRadio'], SearchReq=request.form['search']))
    else: return redirect(request.referrer)

@app.route('/lib/download/<BookID>', methods=['GET'])
def DownloadPage(BookID):
    config = configparser.ConfigParser();config.read(MainConfigFile)

    if str(BookID).isdigit() == False: abort(403)
    if config.getboolean('WorkMode', 'externalStorage') is True:
        flibusta_links = config['WorkMode']['externalStorageURLs'].split()

        for link in flibusta_links:
            try:
                requests.head(link, timeout=2)
                alink = link
                break
            except: pass

        r = requests.get(f"{alink}/b/{BookID}/fb2", stream=True, timeout=15)
        r.raw.decode_content = True

        book = None
        with zipfile.ZipFile(BytesIO(r.content), 'r') as zip_ref:
            for file in zip_ref.namelist():
                if file[-3:] == 'fb2':
                    book = BytesIO(zip_ref.read(file))
                    break
    
        if book is None:
            abort(404)
        else:
            return send_file(book, as_attachment=True, mimetype='fb2', download_name=f"{BookID}.fb2")

    else:
        Database_Conn = mysql.connector.connect(host=config['mysql']['host'], port=config['mysql']['port'], user=config['mysql']['login'], password=config['mysql']['password'], database='galv_fb2index')
        Database_Cursor = Database_Conn.cursor()
        bookarch = Database_Cursor.execute(f"SELECT ArchiveName FROM ArchiveToBook WHERE BookID = {BookID};")
        bookarch = Database_Cursor.fetchall()
        try: bookarch = bookarch[0][0]
        except: abort(404)
        book = None
        with zipfile.ZipFile(f"{config['WorkMode']['internalStorage']}/{bookarch}.zip", 'r') as zip_ref:
            for file in zip_ref.namelist():
                if file == f"{BookID}.fb2":
                    book = BytesIO(zip_ref.read(file))
                    break
    
        if book is None:
            abort(404)
        else:
            return send_file(book, as_attachment=True, mimetype='fb2', download_name=f"{BookID}.fb2")

@app.route('/lib/book/<BookID>', methods=['GET'])
def BookPage(BookID):
    config = configparser.ConfigParser();config.read(MainConfigFile)
    Database_Conn = mysql.connector.connect(host=config['mysql']['host'], port=config['mysql']['port'], user=config['mysql']['login'], password=config['mysql']['password'], database='galv_fb2index')
    Database_Cursor = Database_Conn.cursor()

    book = Database_Cursor.execute(f"SELECT libavtor.BookId, libbook.Title, libbook.Title1, libavtorname.lfm, libadd.Image, libadd.Annotation FROM libavtor, libbook, libavtorname, libadd WHERE libbook.BookID = {str(BookID)} AND libbook.BookId = libavtor.BookId AND libavtor.AvtorId = libavtorname.AvtorId AND libavtor.BookId = libadd.BookID;")

    try: book = Database_Cursor.fetchall(); book = book[0]
    except: abort(404)

    if book[4] is None: img = getattr(service.placeholder, 'img')
    else: img = book[4]

    if book[2] == '': subTitle = ''
    else: subTitle = f"[{book[2]}]"

    reviews_db = Database_Cursor.execute(f"SELECT * FROM libreviews WHERE libreviews.BookId = {BookID} ORDER BY libreviews.Time DESC")
    reviews_db = Database_Cursor.fetchall()

    reviews = []

    if reviews_db is None: pass
    else:
        for review_db in reviews_db:
            if review_db[0] == '': author_nickname = 'Anon'
            else: author_nickname = f"[Flibusta] {review_db[0]}"
            author = {'nickname':author_nickname}
            review_date_year = f"{review_db[1].year}"
            review_date_month = f"{review_db[1].month:02d}"
            review_date_day = f"{review_db[1].day:02d}"
            
            review_date = {'year':review_date_year,
                           'month':review_date_month,
                           'day':review_date_day}
            
            review_body = review_db[3].replace('\\', '')

            review = {'author':author,
                      'date':review_date,
                      'body':review_body}
            reviews.append(review)

    content = {'BookID':book[0],
               'Title1':book[1],
               'Title2':subTitle,
               'Author':book[3],
               'Image':img,
               'Annotation':book[5],
               'Reviews':reviews}


    return render_template('book.html', content=content)

if __name__ == '__main__':
    app.run(debug=True)
