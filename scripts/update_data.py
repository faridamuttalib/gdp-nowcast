"""Atomic official-data refresh for local use and GitHub Actions. No forecasting dependencies."""
from pathlib import Path
from datetime import datetime,date,timezone,timedelta
from concurrent.futures import ThreadPoolExecutor
import urllib.request,urllib.parse,urllib.error,csv,io,json,re,html,hashlib,sys,os,time,argparse,math
ROOT=Path(__file__).resolve().parents[1]
MYT=timezone(timedelta(hours=8));BASE='https://www.dosm.gov.my'
URLS={'gdp':'https://storage.dosm.gov.my/gdp/gdp_qtr_real_supply.csv','ipi':'https://storage.dosm.gov.my/ipi/ipi_1d.csv','retail':'https://storage.dosm.gov.my/iowrt/iowrt_2d.csv','construction':'https://open.dosm.gov.my/dashboard/construction-statistics'}
ARCHIVES={'services':BASE+'/portal-main/release-archive/volume-index-of-services-Q22026','construction':BASE+'/portal-main/release-archive/construction-statistics-q22026','ipi':BASE+'/portal-main/release-archive/index-of-industrial-production-aug2026','retail':BASE+'/portal-main/release-archive/performance-of-wholesale--retail-trade-aug2026','gdp':BASE+'/portal-main/release-archive/gross-domestic-product-q22026'}
KEYS=['agriculture','mining','manufacturing','construction','services','duties']
def qlabel(d):return f'{d.year}Q{(d.month-1)//3+1}'
def release_quarter(d):
 q=d.year*4+(d.month-1)//3-1
 return f'{q//4}Q{q%4+1}'
def number(v):
 f=float(v)
 if not math.isfinite(f):raise ValueError('Non-finite source number')
 return f
def strip(s):return re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]+>',' ',s))).strip()
def records(text,required):
 reader=csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
 if not set(required)<=set(reader.fieldnames or []):raise ValueError(f'CSV schema changed: expected {required}')
 return list(reader)
def fetch(url,folder,name):
 parsed=urllib.parse.urlparse(url)
 if parsed.scheme!='https' or parsed.hostname not in ['www.dosm.gov.my','storage.dosm.gov.my','open.dosm.gov.my','bepi.mpob.gov.my']:raise ValueError('Unexpected download host')
 for attempt in range(3):
  try:
   req=urllib.request.Request(url,headers={'User-Agent':'Malaysia GDP Nowcast public data refresh/1.0'})
   with urllib.request.urlopen(req,timeout=45) as response:body=response.read()
   if not body:raise ValueError('Empty public download')
   (folder/name).write_bytes(body);print(f'Downloaded {name}: {len(body)} bytes',flush=True);return body
  except Exception:
   if attempt==2:raise
   time.sleep(1+attempt)
def parse_archive(text):
 return [(html.unescape(u),datetime.strptime(dt,'%d.%m.%Y').date(),strip(title)) for u,dt,title in re.findall(r'<a[^>]+href="([^"]+)"[^>]*>(\d\d\.\d\d\.\d{4}) - ([^<]+)</a>',text,re.I)]
def parse_cpo(text,year):
 heading=strip(text)
 if f'SUMMARY OF THE MALAYSIAN PALM OIL INDUSTRY {year}' not in heading:raise ValueError(f'Unexpected MPOB page for {year}')
 rows=[[strip(c) for c in re.findall(r'<t[dh]\b[^>]*>(.*?)</t[dh]>',tr,re.I|re.S)] for tr in re.findall(r'<tr\b[^>]*>(.*?)</tr>',text,re.I|re.S)]
 if not any(len(a)>=14 and re.match(r'^Jan\s+\d{2}$',a[2],re.I) for a in rows):raise ValueError('MPOB month layout changed')
 found=[a for a in rows if a and a[0].lower()=='crude palm oil']
 if len(found)!=1 or len(found[0])<14:raise ValueError('CPO production row missing')
 result={}
 for month,v in enumerate(found[0][2:14],1):
  if not v:continue
  if not re.fullmatch(r'(?:\d{1,3}(?:,\d{3})+|\d+)(?:\.\d+)?',v):raise ValueError('CPO number layout changed')
  result[f'{year}-{month:02d}-01']=number(v.replace(',',''))
 if year<datetime.now(MYT).year-1 and len(result)!=12:raise ValueError('Incomplete historical CPO year')
 return result
def monthly_calendar(entries,marker):
 result={};months=['jan','feb','mar','apr','may','jun','jul','aug','sep','oct','nov','dec']
 for url,published,title in entries:
  if marker not in title.lower():continue
  match=re.search(r'\b(jan[a-z]*|feb[a-z]*|mar[a-z]*|apr[a-z]*|may|jun[a-z]*|jul[a-z]*|aug[a-z]*|sep[a-z]*|oct[a-z]*|nov[a-z]*|dec[a-z]*)\s+(20\d\d)',title+' '+url.replace('-',' ').replace('_',' '),re.I)
  if match:result[f'{match[2]}-{months.index(match[1][:3].lower())+1:02d}-01']=published.isoformat()
 return result
def source_inventory(d):
 result=[]
 for key,name,url,unit,freq in [
  ('gdp','Real GDP components',URLS['gdp'],'RM million, constant 2015 prices','Quarterly'),
  ('cpo','Crude palm oil production','https://bepi.mpob.gov.my/stat/web_report1.php?val='+str(datetime.now(MYT).year)+'84','Tonnes','Monthly'),
  ('mining','Mining industrial production',URLS['ipi'],'Index, 2015=100','Monthly'),
  ('manufacturing','Manufacturing industrial production',URLS['ipi'],'Index, 2015=100','Monthly'),
  ('retail','Retail trade volume',URLS['retail'],'Index, 2015=100','Monthly'),
  ('servicesVolume','Services volume index',BASE+'/portal-main/release-content/volume-index-of-services-Q22026','Index, 2015=100','Quarterly'),
  ('constructionWork','Construction work done',URLS['construction'],'RM thousand, nominal','Quarterly')]:
  rows=d['gdp'] if key=='gdp' else d['quarterly'] if key in ['servicesVolume','constructionWork'] else d['monthly']
  valid=[r for r in rows if key=='gdp' or isinstance(r.get(key),(int,float))]
  if key=='cpo' and valid:url='https://bepi.mpob.gov.my/stat/web_report1.php?val='+max(r['date'] for r in valid)[:4]+'84'
  result.append({'id':key,'name':name,'url':url,'units':unit,'frequency':freq,'provider':'MPOB' if key=='cpo' else 'DOSM','observations':len(valid),'latest':max(r.get('date',r.get('quarter')) for r in valid) if valid else None,'downloadedAt':d['updatedAt']})
 return result
def unpublished_cpo_year_allowed(previous,today):
 return today.month<=2 and not any(r['date'].startswith(str(today.year)) and isinstance(r.get('cpo'),(int,float)) for r in (previous or {}).get('monthly',[]))
def validate(d,previous=None):
 if d.get('schemaVersion')!=1:raise ValueError('Unsupported data schema')
 for kind,key in [('gdp','quarter'),('monthly','date'),('quarterly','quarter')]:
  rows=d[kind];ids=[r[key] for r in rows]
  if len(ids)!=len(set(ids)):raise ValueError(f'Duplicate {kind} period')
  for row in rows:
   for v in row.values():
    if isinstance(v,(int,float)) and (not math.isfinite(v) or v<0):raise ValueError('Invalid source level')
 if len(d['gdp'])<40 or len(d['monthly'])<120:raise ValueError('Incomplete source history')
 for r in d['gdp']:
  if not all(isinstance(r.get(k),(int,float)) and r[k]>0 for k in KEYS+['total']):raise ValueError('Missing GDP component')
  if abs(sum(r[k] for k in KEYS)-r['total'])>max(5,r['total']*.0001):raise ValueError('GDP components do not reconcile')
 for k in ['cpo','mining','manufacturing','retail']:
  if sum(isinstance(r.get(k),(int,float)) for r in d['monthly'])<80:raise ValueError(f'Incomplete {k} history')
 if previous:
  for field,key,values in [('gdp','quarter',['total']),('monthly','date',['cpo','mining','manufacturing','retail']),('quarterly','quarter',['servicesVolume','constructionWork'])]:
   new={r[key]:r for r in d[field]}
   for r in previous[field]:
    for v in values:
     if isinstance(r.get(v),(int,float)) and not isinstance(new.get(r[key],{}).get(v),(int,float)):raise ValueError(f'Refresh lost {field} {r[key]} {v}')
def refresh(output):
 now=datetime.now(MYT);folder=ROOT/'data_snapshots'/now.strftime('%Y%m%d_%H%M%S_%f');folder.mkdir(parents=True)
 previous=json.loads(output.read_text()) if output.exists() else None
 jobs={**{k:(u,k+'.csv' if k!='construction' else k+'.html') for k,u in URLS.items()},**{k+'Archive':(u,k+'_archive.html') for k,u in ARCHIVES.items()},**{f'mpob{y}':(f'https://bepi.mpob.gov.my/stat/web_report1.php?val={y}84',f'mpob{y}.html') for y in range(2015,now.year+1)}}
 optional_cpo=unpublished_cpo_year_allowed(previous,now.date());warnings=[]
 def get(item):
  k,(u,name)=item
  try:return k,fetch(u,folder,name).decode('utf-8-sig')
  except urllib.error.HTTPError as e:
   if k==f'mpob{now.year}' and optional_cpo and e.code==404:return k,None
   raise
 try:
  with ThreadPoolExecutor(max_workers=5) as pool:texts=dict(pool.map(get,jobs.items()))
  archives={k:parse_archive(texts[k+'Archive']) for k in ARCHIVES}
  g={}
  for r in records(texts['gdp'],['series','date','sector','value']):
   if r['series']=='abs' and r['sector'] in [f'p{i}' for i in range(7)] and r['date']>='2015-01-01':
    q=qlabel(date.fromisoformat(r['date']));k=int(r['sector'][1:]);field='total' if k==0 else KEYS[k-1]
    item=g.setdefault(q,{'quarter':q})
    if field in item:raise ValueError('Duplicate GDP observation')
    item[field]=number(r['value'])
  monthly={}
  def put(dt,key,val):
   if dt<'2015-01-01':return
   row=monthly.setdefault(dt,{'date':dt,'cpo':None,'mining':None,'manufacturing':None,'retail':None})
   if row[key] is not None:raise ValueError('Duplicate monthly observation')
   row[key]=number(val)
  for r in records(texts['ipi'],['series','date','section','index']):
   if r['series']=='abs' and r['section'] in ['B','C']:put(r['date'],'mining' if r['section']=='B' else 'manufacturing',r['index'])
  for r in records(texts['retail'],['series','date','division','volume']):
   if r['series']=='abs' and r['division']=='47':put(r['date'],'retail',r['volume'])
  for y in range(2015,now.year+1):
   if texts[f'mpob{y}'] is None:
    warnings.append(f'{y} CPO annual page is not yet published; available prior-year observations retained.');continue
   try:production=parse_cpo(texts[f'mpob{y}'],y)
   except ValueError:
    if y==now.year and optional_cpo:
     warnings.append(f'{y} CPO annual page is not yet populated; available prior-year observations retained.');continue
    raise
   for dt,v in production.items():put(dt,'cpo',v)
  dates={'services':{'2026Q2':'2026-08-12'},'construction':{'2026Q2':'2026-08-13'}}
  for key,marker in [('services','volume index of services'),('construction','construction statistics')]:
   for u,published,title in archives[key]:
    if marker in title.lower() and published.month in [2,5,8,11] and published<=now.date():dates[key][release_quarter(published)]=published.isoformat()
  candidates=[(date(2026,8,12),BASE+'/portal-main/release-content/volume-index-of-services-Q22026')]+[(p,urllib.parse.urljoin(BASE,u)) for u,p,t in archives['services'] if 'volume index of services' in t.lower() and p<=now.date()]
  latest,vispage=max(candidates);page=fetch(vispage,folder,'services_release.html').decode('utf-8-sig')
  matches=re.findall(r'<a\s+download="[^"]*"\s+href="([^"]+)"',page,re.I)
  if len(matches)!=1:raise ValueError('DOSM services XLSX link changed')
  visurl=html.unescape(matches[0]);body=fetch(visurl,folder,'services_volume.xlsx')
  import openpyxl
  book=openpyxl.load_workbook(io.BytesIO(body),data_only=True,read_only=True)
  sh=book['Volume Segment'];year=None;vis={}
  for row in sh.iter_rows(min_row=12,values_only=True):
   if isinstance(row[1],str) and re.fullmatch(r'Q[1-4][rp]?',row[1].strip()):
    if isinstance(row[0],(float,int)):year=int(row[0])
    if not year or year<2015 or year>now.year:continue
    q=f'{year}Q{row[1][1]}'
    if q in vis:break
    if isinstance(row[2],(float,int)) and row[2]>0:vis[q]=float(row[2])
  book.close()
  if len(vis)<40 or release_quarter(latest) not in vis:raise ValueError('Incomplete services volume history')
  match=re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>',texts['construction'],re.S)
  if not match:raise ValueError('OpenDOSM construction data layout changed')
  actual=json.loads(match[1])['props']['pageProps']['timeseries']['data']['actual']
  if len(actual['x'])!=len(actual['value']):raise ValueError('Construction history incomplete')
  works={qlabel(datetime.fromtimestamp(x/1000,timezone.utc).date()):number(v) for x,v in zip(actual['x'],actual['value']) if datetime.fromtimestamp(x/1000,timezone.utc).year>=2015}
  quarterly=[{'quarter':q,'servicesVolume':vis.get(q),'servicesPublished':dates['services'].get(q),'constructionWork':works.get(q),'constructionPublished':dates['construction'].get(q)} for q in sorted(set(vis)|set(works))]
  releases={'ipi':monthly_calendar(archives['ipi'],'industrial production'),'retail':monthly_calendar(archives['retail'],'performance of wholesale'),'gdp':{}}
  # Archive URLs omit their anchor release; include that verified release explicitly.
  releases['ipi']['2026-08-01']='2026-10-09';releases['retail']['2026-08-01']='2026-10-09';releases['gdp']['2026Q2']='2026-08-14'
  for u,published,title in archives['gdp']:
   lower=title.lower()
   if 'gross domestic product' in lower and 'advance' not in lower and ('quarter' in lower or re.search(r'q[1-4]',lower)) and published.month in [2,5,8,11] and published<=now.date():releases['gdp'][release_quarter(published)]=published.isoformat()
  if previous:
   for key in releases:releases[key]={**previous['releases'].get(key,{}),**releases[key]}
  d={'schemaVersion':1,'updatedAt':now.isoformat(timespec='seconds'),'snapshotType':'official-source-refresh','provenance':{'description':'Latest revised official downloads. Historical forecasts do not recreate original-release data vintages.','servicesDownload':visurl,'refreshStatus':'complete','notes':warnings},'gdp':sorted(g.values(),key=lambda r:r['quarter']),'monthly':sorted(monthly.values(),key=lambda r:r['date']),'quarterly':quarterly,'releases':releases}
  d['sources']=source_inventory(d);validate(d,previous)
  d['snapshotId']=hashlib.sha256(json.dumps(d,sort_keys=True).encode()).hexdigest()[:16]
  (folder/'manifest.json').write_text(json.dumps({'sources':{k:u for k,(u,n) in jobs.items()},'updatedAt':d['updatedAt'],'snapshotId':d['snapshotId'],'status':'complete'},indent=2))
  output.parent.mkdir(parents=True,exist_ok=True)
  temporary=output.with_suffix('.tmp');temporary.write_text(json.dumps(d,indent=2,allow_nan=False),encoding='utf8');os.replace(temporary,output)
  print('SUCCESS: committed complete validated snapshot '+d['snapshotId'],flush=True);return d
 except Exception as e:
  (folder/'failure.txt').write_text(str(e),encoding='utf8');raise
if __name__=='__main__':
 parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,default=ROOT/'dist/data/model-data.json');args=parser.parse_args()
 try:refresh(args.output)
 except Exception as e:print('Refresh failed; preceding snapshot retained: '+str(e),file=sys.stderr);sys.exit(1)
