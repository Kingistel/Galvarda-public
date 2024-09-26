import mysql.connector
import bs4
from PIL import Image
import requests
import base64
from io import BytesIO
from multiprocessing import Process, freeze_support, Pool
import time
import configparser

config = configparser.ConfigParser();config.read("../config.ini")

def GetContentFromFlib(FlibUrl: str, BookID: int):
    fPage = requests.get(f"{FlibUrl}/b/{BookID}", timeout=15)
    soup = bs4.BeautifulSoup(fPage.content, 'html.parser')
    try:
        imgurl = f"{FlibUrl}{soup.find('img', {'title' : 'Cover image'})['src']}"
    except:
        imgurl = None
    
    try:
        Annotation = [] 
        tmp = soup.find('h2', string='Аннотация')
        for i in range(5):
            tmp = tmp.findNext()
            if tmp.name == 'p':
                Annotation.append(tmp.text.replace("'", '"').encode('windows-1251', errors = 'ignore').decode())
            else: break
        Annotation = " ".join(str(element) for element in Annotation)
        if Annotation == '': Annotation = 'Аннотация отсутствует.'
    except:
        Annotation = 'Аннотация отсутствует.'
    del tmp
    del soup
    del fPage
    return imgurl, Annotation

def magic(BookID):
    Database_Conn = mysql.connector.connect(host=config['mysql']['host'], port=config['mysql']['port'], user=config['mysql']['login'], password=config['mysql']['password'], database='galv_fb2index')
    Database_Cursor = Database_Conn.cursor()
    BookID = BookID[0]
    print(BookID)
    imgurl, Annotation = GetContentFromFlib(FlibUrl='http://flibusta.site', BookID=BookID)
    if imgurl != None:
        r = requests.get(imgurl, stream=True, timeout=15)
        r.raw.decode_content = True
        try:
            im = Image.open(r.raw)
            im = im.resize((133,200))
            im = im.convert('RGB')
            buffered = BytesIO()
            im.save(buffered, format="JPEG")
            img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')
            del im, buffered
        except:
            print('Неизвесный формат изображения')
            img_str=None

        t = Database_Cursor.execute(f"UPDATE libadd SET Image='{img_str}', Annotation='{Annotation}' WHERE BookID={BookID}")
        t = Database_Conn.commit()
        del img_str, r

    else:
        t = Database_Cursor.execute(f"UPDATE libadd SET Annotation='{Annotation}' WHERE BookID={BookID}")
        t = Database_Conn.commit()
    Database_Cursor.close(); Database_Conn.close()
    del t, imgurl, Annotation, BookID

if __name__ == '__main__':
    freeze_support()

    print('get books')

    Database_Conn = mysql.connector.connect(host=config['mysql']['host'], port=config['mysql']['port'], user=config['mysql']['login'], password=config['mysql']['password'], database='galv_fb2index')
    Database_Cursor = Database_Conn.cursor()

    books = Database_Cursor.execute('SELECT BookID FROM libadd WHERE libadd.Image IS NULL AND libadd.Annotation IS NULL ORDER BY BookID;')
    books = Database_Cursor.fetchall();

    Database_Cursor.close(); Database_Conn.close()
    print('get books done')

    pool = Pool(processes=30, maxtasksperchild=40)
    results = pool.map(magic, books)
    pool.close()
    pool.join()

    '''
    for book in books:
        time.sleep(0.5)
        proc = Process(target=magic, args=(book[0],), daemon=True)
        proc.start()
        #magic(book[0])
    '''
