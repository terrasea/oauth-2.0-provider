from DB import ZODB as DB, SERVER, PORT
import transaction

def add_anonymous_url(url):
    db = DB(SERVER, PORT)
    try:
        if 'anonymous_urls' in db.dbroot:
            urls = db.get('anonymous_urls')
            urls.add(url)
            db.put('anonymous_urls', urls)
        else:
            urls = set()
            urls.add(url)
            db.put('anonymous_urls', urls)
        db.commit()
    except Exception, e:
        logging.error(''.join(['add_anonymous_url: ', str(e)]))
        db.abort()
    finally:
        db.close()
        

def get_anonymous_urls():
    db = DB(SERVER, PORT)
    try:
        return db.get('anonymous_urls')
    except Exception, e:
        logging.error(''.join(['get_anonymous_urls: ', str(e)]))
    finally:
        db.close()

    return None


if __name__ == '__main__':
    import time
    add_anonymous_url('http://pynnnn.org')
    print int(time.time()*100), '"', get_anonymous_urls(), '"'
