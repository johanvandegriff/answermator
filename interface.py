import sys
from app import app

if __name__ == '__main__':
    # app.run(host='0.0.0.0')
    # https://stackoverflow.com/questions/37962925/flask-app-get-ioerror-errno-32-broken-pipe#38628780
    # https://stackoverflow.com/questions/50461657/ddg#50465220
    from gevent.pywsgi import WSGIServer
    port = 80
    if len(sys.argv) > 1:
        port = int(sys.argv[1])
    http_server = WSGIServer(('', port), app)
    print("starting web server on http://0.0.0.0:"+str(port)+"/")
    http_server.serve_forever()
