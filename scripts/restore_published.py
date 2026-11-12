"""Use the last published public Pages snapshot as the refresh coverage baseline."""
from pathlib import Path
import os,json,time,urllib.request,urllib.error
from update_data import validate
ROOT=Path(__file__).resolve().parents[1]
def main():
 base=os.environ.get('PAGES_BASE_URL','').rstrip('/')
 if not base.startswith('https://'):raise ValueError('GitHub Pages did not return a secure base URL.')
 url=base+'/data/model-data.json?coverage='+str(int(time.time()))
 try:
  with urllib.request.urlopen(urllib.request.Request(url,headers={'Cache-Control':'no-cache'}),timeout=30) as response:data=json.load(response)
 except urllib.error.HTTPError as e:
  if e.code==404:
   print('No prior published snapshot (404); retaining the bundled validated baseline.');return
  raise
 target=ROOT/'dist/data/model-data.json';previous=json.loads(target.read_text());validate(data,previous)
 target.write_text(json.dumps(data,indent=2,allow_nan=False),encoding='utf8')
 print('Restored published coverage baseline '+str(data.get('snapshotId','')))
if __name__=='__main__':main()
