"""Local dashboard with a same-origin, localhost-only source refresh endpoint."""
from pathlib import Path
from http.server import ThreadingHTTPServer,SimpleHTTPRequestHandler
from urllib.parse import urlparse
from datetime import datetime,timezone
import argparse,json,subprocess,sys,threading
ROOT=Path(__file__).resolve().parents[1];LOCK=threading.Lock()
class Handler(SimpleHTTPRequestHandler):
 refresh_enabled=True
 def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT/'dist'),**kwargs)
 def end_headers(self):
  self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');super().end_headers()
 def reply(self,status,body):
  data=json.dumps(body).encode();self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
 def do_GET(self):
  if urlparse(self.path).path=='/api/capabilities':return self.reply(200,{'refresh':self.refresh_enabled,'mode':'local' if self.refresh_enabled else 'static','authentication':'localhost-only'})
  super().do_GET()
 def do_POST(self):
  if urlparse(self.path).path!='/api/refresh':return self.reply(404,{'error':'Unknown endpoint'})
  if not self.refresh_enabled:return self.reply(405,{'error':'Static hosting: run the refresh workflow on GitHub.'})
  host=self.headers.get('Host','');origin=self.headers.get('Origin')
  if host.split(':')[0] not in ['127.0.0.1','localhost']:return self.reply(403,{'error':'This refresh service only accepts localhost requests.'})
  if self.headers.get('X-Nowcast-Refresh')!='1' or (origin and origin not in ['http://'+host,'https://'+host]):return self.reply(403,{'error':'Refresh requires a same-origin dashboard request.'})
  if int(self.headers.get('Content-Length','0'))>4096:return self.reply(413,{'error':'Request too large'})
  self.rfile.read(int(self.headers.get('Content-Length','0')))
  if not LOCK.acquire(blocking=False):return self.reply(409,{'error':'A source refresh is already running.'})
  try:
   proc=subprocess.run([sys.executable,str(ROOT/'scripts/update_data.py')],cwd=ROOT,capture_output=True,text=True,timeout=300)
   if proc.returncode:
    message=(proc.stderr or proc.stdout).strip().splitlines()[-1]
    return self.reply(502,{'error':message,'retainedPreviousSnapshot':True})
   data=json.loads((ROOT/'dist/data/model-data.json').read_text());return self.reply(200,{'snapshotId':data['snapshotId'],'updatedAt':data['updatedAt']})
  except Exception as e:return self.reply(500,{'error':str(e),'retainedPreviousSnapshot':True})
  finally:LOCK.release()
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--port',type=int,default=8767);parser.add_argument('--open-browser',action='store_true');parser.add_argument('--static-only',action='store_true');args=parser.parse_args()
 Handler.refresh_enabled=not args.static_only
 try:server=ThreadingHTTPServer(('127.0.0.1',args.port),Handler)
 except OSError:
  if args.open_browser:
   try:
    import urllib.request,webbrowser
    with urllib.request.urlopen(f'http://127.0.0.1:{args.port}/api/capabilities',timeout=2) as response:existing=json.load(response)
    if existing.get('mode') in ['local','static']:
     webbrowser.open(f'http://127.0.0.1:{args.port}');sys.exit(0)
   except (OSError,ValueError):pass
  raise
 print(f'Malaysia GDP dashboard: http://127.0.0.1:{args.port}',flush=True)
 if args.open_browser:
  import webbrowser
  threading.Timer(.6,lambda:webbrowser.open(f'http://127.0.0.1:{args.port}')).start()
 try:server.serve_forever()
 except KeyboardInterrupt:server.server_close()
