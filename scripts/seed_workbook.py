"""One-time read-only import of the approved Excel workbook. No macros run."""
from pathlib import Path
from datetime import datetime,date,timezone
import json,sys,hashlib
import openpyxl
from openpyxl.utils.cell import range_boundaries
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT.parent/'model_work'
sys.path.insert(0,str(ROOT/'scripts'))
def iso(v):
 if isinstance(v,(datetime,date)):return v.strftime('%Y-%m-%d')
 return v if isinstance(v,str) and len(v)>=10 else None
def table(w,s,name):
 sh=w[s];a,b,c,d=range_boundaries(sh.tables[name].ref)
 return [[sh.cell(r,col).value for col in range(a,c+1)] for r in range(b+1,d+1)]
def make(workbook):
 w=openpyxl.load_workbook(workbook,data_only=True)
 g=[]
 for r in table(w,'GDP history','GDPInputs'):
  if all(isinstance(x,(int,float)) for x in r[2:9]):g.append(dict(zip(['quarter','agriculture','mining','manufacturing','construction','services','duties','total'],[r[0]]+r[2:9])))
 m=[dict(zip(['date','cpo','mining','manufacturing','retail'],[iso(r[0])]+r[3:7])) for r in table(w,'Monthly data','MonthlyInputs')]
 qt=[dict(zip(['quarter','servicesVolume','servicesPublished','constructionWork','constructionPublished'],[r[0],r[1],iso(r[2]),r[3],iso(r[4])])) for r in table(w,'Quarterly inputs','QuarterlyInputs')]
 releases={'ipi':{},'retail':{},'gdp':{}}
 for r in table(w,'Web data','ReleaseCalendar'):
  if iso(r[0]):
   if iso(r[1]):releases['ipi'][iso(r[0])]=iso(r[1])
   if iso(r[2]):releases['retail'][iso(r[0])]=iso(r[2])
 meta=json.loads((WORK/'quarterly_meta.json').read_text(encoding='utf8'))
 for r in meta['all_release_checks']:releases['gdp'][r[0]]=r[-1]
 audit=w['Web data'];stamp=audit['B3'].value
 if not isinstance(stamp,datetime):stamp=datetime(2026,11,10)
 stamp=stamp.isoformat()+'+08:00'
 return {'schemaVersion':1,'updatedAt':stamp,'snapshotType':'approved-workbook','provenance':{'description':'Read-only import from the approved quarterly workbook; revised data, not historical first-release vintages.'},'gdp':g,'monthly':m,'quarterly':qt,'releases':releases}
if __name__=='__main__':
 from update_data import source_inventory,validate
 book=ROOT.parent/'outputs/quarterly_model/Malaysia_GDP_Quarterly_Update.xlsm'
 data=make(book);data['sources']=source_inventory(data);validate(data)
 data['snapshotId']=hashlib.sha256(json.dumps(data,sort_keys=True).encode()).hexdigest()[:16]
 (ROOT/'dist/data/model-data.json').write_text(json.dumps(data,indent=2,allow_nan=False),encoding='utf8')
 # Frozen fixtures are separate from refreshing operational inputs.
 frozen=json.loads((WORK/'model_v2.json').read_text());meta=json.loads((WORK/'quarterly_meta.json').read_text())
 f={**data,'updatedAt':'2026-10-21T16:02:00+08:00','snapshotType':'frozen-parity-fixture'}
 f['gdp']=[dict(zip(['quarter','agriculture','mining','manufacturing','construction','services','duties','total'],[r[0]]+r[2:9])) for r in frozen['history'] if all(isinstance(v,(int,float)) for v in r[2:9])]
 f['monthly']=[dict(zip(['date','cpo','mining','manufacturing','retail'],[r[0],r[1],r[2],r[3],r[5]])) for r in frozen['monthly']]
 f['quarterly']=[dict(zip(['quarter','servicesVolume','servicesPublished','constructionWork','constructionPublished'],r)) for r in meta['rows']]
 f['releases']={'ipi':{},'retail':{},'gdp':data['releases']['gdp']}
 for r in meta['calendar']:
  if r[1]:f['releases']['ipi'][r[0]]=r[1]
  if r[2]:f['releases']['retail'][r[0]]=r[2]
 (ROOT/'tests/fixtures/excel-reference.json').write_text(json.dumps(f,indent=2,allow_nan=False),encoding='utf8')
 expected=json.loads((WORK/'quarterly_review.json').read_text());expected={k:expected[k] for k in ['early','quarterly']};(ROOT/'tests/fixtures/expected.json').write_text(json.dumps(expected,indent=2),encoding='utf8')
 print(f'Imported {len(data["gdp"])} GDP quarters, {len(data["monthly"])} months, {len(data["quarterly"])} quarterly rows.')
