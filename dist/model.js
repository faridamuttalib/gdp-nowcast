export const SECTORS = [
  {key:'agriculture',name:'Agriculture',short:'Agriculture',color:'#758b3a'},
  {key:'mining',name:'Mining & quarrying',short:'Mining',color:'#747f98'},
  {key:'manufacturing',name:'Manufacturing',short:'Manufacturing',color:'#315da8'},
  {key:'construction',name:'Construction',short:'Construction',color:'#c79b21'},
  {key:'services',name:'Services',short:'Services',color:'#001a70'},
  {key:'duties',name:'Import duties',short:'Import duties',color:'#a66773'}
];
export const isNumber=v=>typeof v==='number'&&Number.isFinite(v);
// Frozen after the 2023–2024 calibration / 2025Q1–2026Q2 review.
// Never re-estimate these constants during source refresh or apply to older forecasts.
export const ADD_FACTOR_POLICY=Object.freeze({version:'2026-11-12',fromQuarter:'2026Q3',fromCutoff:'2026-11-12',earlyServicesPP:0,preGDPServicesPP:0.2});
export function quarterIndex(q){if(!/^\d{4}Q[1-4]$/.test(q))throw new Error('Choose a quarter such as 2026Q3.');return +q.slice(0,4)*4+(+q.at(-1)-1);}
export const quarterLabel=q=>`${Math.floor(q/4)}Q${q%4+1}`;
export const monthOf=(q,j)=>`${Math.floor(q/4)}-${String(q%4*3+j).padStart(2,'0')}-01`;
const previousDay=d=>new Date(new Date(d+'T12:00:00Z').valueOf()-86400000).toISOString().slice(0,10);
const fit=(pairs,window)=>{
 const p=window?pairs.slice(-window):pairs;
 if(p.length<12)return null;
 const mx=p.reduce((a,r)=>a+r.x,0)/p.length,my=p.reduce((a,r)=>a+r.y,0)/p.length;
 const variance=p.reduce((a,r)=>a+(r.x-mx)**2,0);
 if(variance<=1e-16)return null;
 const slope=p.reduce((a,r)=>a+(r.x-mx)*(r.y-my),0)/variance;
 return {intercept:my-slope*mx,slope,n:p.length,from:quarterLabel(p[0].q),through:quarterLabel(p.at(-1).q)};
};
export function forecast(data,{quarter,cutoff,mode='Auto',applyAddFactors=true}){
 const target=quarterIndex(quarter);
 if(!/^\d{4}-\d{2}-\d{2}$/.test(cutoff)||Number.isNaN(Date.parse(cutoff)))throw new Error('Choose a valid cutoff date.');
 if(!['Auto','Early','Pre-GDP'].includes(mode))throw new Error('Choose Auto, Early or Pre-GDP.');
 const g=new Map(data.gdp.filter(r=>quarterIndex(r.quarter)<target&&(!data.releases.gdp?.[r.quarter]||data.releases.gdp[r.quarter]<=cutoff)).map(r=>[quarterIndex(r.quarter),r]));
 const monthly=new Map(data.monthly.map(r=>[r.date,r]));
 const quarterly=new Map(data.quarterly.map(r=>[quarterIndex(r.quarter),r]));
 const growth=(q,k)=>isNumber(g.get(q)?.[k])&&g.get(q-4)?.[k]>0?g.get(q)[k]/g.get(q-4)[k]-1:null;
 const monthlySignal=(q,key,n)=>{
  const a=[],b=[];
  for(let j=1;j<=n;j++){const x=monthly.get(monthOf(q,j))?.[key],y=monthly.get(monthOf(q-4,j))?.[key];if(!isNumber(x)||!isNumber(y))return null;a.push(x);b.push(y);}
  const den=b.reduce((x,y)=>x+y,0);return den>0?a.reduce((x,y)=>x+y,0)/den-1:null;
 };
 const quarterlySignal=(q,key)=>quarterly.get(q-4)?.[key]>0&&isNumber(quarterly.get(q)?.[key])?quarterly.get(q)[key]/quarterly.get(q-4)[key]-1:null;
 const monthlyPublished=(n,retail)=>{
  const missing=[];
  for(let j=1;j<=n;j++)for(const src of retail?['ipi','retail']:['ipi']){
   const month=monthOf(target,j),date=data.releases[src]?.[month];
   if(!date||date>cutoff)missing.push(`${src==='ipi'?'IPI':'Retail volume'} ${month.slice(0,7)} ${date?`published ${date}`:'publication date unverified'}`);
  }return missing;
 };
 const earlyMissing=monthlyPublished(2,true);
 if(earlyMissing.length)throw new Error(`The early information set is unavailable by this cutoff: ${earlyMissing.join('; ')}.`);
 const lateMissing=monthlyPublished(3,false),qrow=quarterly.get(target);
 for(const [key,pub,name] of [['servicesVolume','servicesPublished','Services volume'],['constructionWork','constructionPublished','Construction work done']]){
  if(!isNumber(quarterlySignal(target,key)))lateMissing.push(`${name}: same-quarter observation or prior-year comparison missing`);
  if(!qrow?.[pub]||qrow[pub]>cutoff)lateMissing.push(`${name}: ${qrow?.[pub]?`published ${qrow[pub]}`:'publication pending or unverified'}`);
 }
 for(const key of ['cpo','mining','manufacturing'])if(!isNumber(monthlySignal(target,key,3)))lateMissing.push(`${key}: third-month observation missing`);
 const late=mode!=='Early'&&!lateMissing.length;
 if(mode==='Pre-GDP'&&!late)throw new Error(`Pre-GDP is not available at this cutoff. ${[...new Set(lateMissing)].join('; ')}. Use Auto or Early.`);
 const stage=late?'Pre-GDP':'Early',months=late?3:2;
 const methods=late?['Blend','Bridge','Bridge','Bridge','Bridge','AR(1)']:['Blend','Bridge','Bridge','Persistence','Blend','AR(1)'];
 const windows=[0,16,16,late?16:12,12,12];
 const signal=(q,k)=>{
  if(k===5||(!late&&k===3))return null;
  if(late&&k===3)return quarterlySignal(q,'constructionWork');
  if(late&&k===4)return quarterlySignal(q,'servicesVolume');
  return monthlySignal(q,['cpo','mining','manufacturing',null,'retail'][k],months);
 };
 const priorGDP=g.get(target-4)?.total;if(!(priorGDP>0))throw new Error('Prior-year total GDP is missing. Refresh the source data.');
 const quarters=[...g.keys()].sort((a,b)=>a-b);
 const sectors=SECTORS.map((sector,k)=>{
  const method=methods[k],window=windows[k],x=signal(target,k),lag=growth(target-1,sector.key),base=g.get(target-4)?.[sector.key];
  if(!isNumber(lag)||!isNumber(base))throw new Error(`${sector.name}: prior-quarter or prior-year GDP is missing.`);
  let bridge=null,ar=null;
  if(['Bridge','Blend'].includes(method)){
   bridge=fit(quarters.flatMap(q=>{const xx=signal(q,k),y=growth(q,sector.key);return isNumber(xx)&&isNumber(y)?[{q,x:xx,y}]:[];}),window);
   if(!bridge||!isNumber(x))throw new Error(`${sector.name}: at least 12 prior quarters and a current indicator are required.`);
  }
  if(['AR(1)','Blend'].includes(method)){
   ar=fit(quarters.flatMap(q=>{const xx=growth(q-1,sector.key),y=growth(q,sector.key);return isNumber(xx)&&isNumber(y)?[{q,x:xx,y}]:[];}),window);
   if(!ar)throw new Error(`${sector.name}: insufficient prior GDP history for AR(1).`);
  }
  const b=bridge?bridge.intercept+bridge.slope*x:null,a=ar?ar.intercept+ar.slope*lag:null;
  const rawGrowth=method==='Bridge'?b:method==='AR(1)'?a:method==='Blend'?(b+a)/2:lag;
  const addFactorPP=applyAddFactors&&target>=quarterIndex(ADD_FACTOR_POLICY.fromQuarter)&&cutoff>=ADD_FACTOR_POLICY.fromCutoff&&late&&sector.key==='services'?ADD_FACTOR_POLICY.preGDPServicesPP:0;
  const value=rawGrowth+addFactorPP/100;
  return {...sector,method,window,signal:x,lag,base,rawGrowth,addFactorPP,growth:value,level:base*(1+value),weight:base/priorGDP,contribution:base*value/priorGDP*100,bridge,ar,
   indicator:k===3?(late?'Construction work done':'Previous-quarter sector GDP'):k===4?(late?'Services volume index':'Retail volume index'):k===5?'Previous-quarter import duties GDP':['CPO production','Mining IPI','Manufacturing IPI'][k]};
 });
 const level=sectors.reduce((a,r)=>a+r.level,0),headline=level/priorGDP-1;
 const targetActual=data.gdp.find(r=>r.quarter===quarter);
 const actualRelease=data.releases.gdp?.[quarter];
 const actual=targetActual&&actualRelease&&actualRelease<=cutoff?targetActual.total/priorGDP-1:null;
 return {quarter,cutoff,stage,months,sectors,headline,level,priorGDP,actual,roundingContribution:(sectors.reduce((a,r)=>a+r.base,0)/priorGDP-1)*100,lateMissing:[...new Set(lateMissing)],excludedGDP:quarter,
  note:late?'Complete monthly quarter plus published quarterly indicators.':mode==='Early'?'Early stage selected. First two months only.':'Auto retained Early while the pre-GDP information set is incomplete.'};
}
export function reviewModel(data,stage,informationCutoff=null){
 const rows=[];
 for(let q=2025*4;q<=2026*4+1;q++){
  const quarter=quarterLabel(q),release=data.releases.gdp?.[quarter],g=data.gdp.find(r=>r.quarter===quarter),prior=data.gdp.find(r=>r.quarter===quarterLabel(q-4));
  if(!release||!g||!prior){rows.push({quarter,error:'Actual GDP or publication date unavailable'});continue;}
  if(informationCutoff&&release>informationCutoff){rows.push({quarter,error:'Actual GDP was not yet published at the selected cutoff'});continue;}
  try{const f=forecast(data,{quarter,cutoff:previousDay(release),mode:stage});const actual=g.total/prior.total-1;rows.push({quarter,actual,prediction:f.headline,errorPP:(f.headline-actual)*100});}
  catch(e){rows.push({quarter,error:e.message});}
 }
 const valid=rows.filter(r=>isNumber(r.errorPP));
 return {rows,n:valid.length,mae:valid.length?valid.reduce((a,r)=>a+Math.abs(r.errorPP),0)/valid.length:null,rmse:valid.length?Math.sqrt(valid.reduce((a,r)=>a+r.errorPP**2,0)/valid.length):null};
}
export function scenario(result,adjustments={}){
 const sectors=result.sectors.map(r=>({...r,deltaPP:Number(adjustments[r.key]||0),growth:r.growth+Number(adjustments[r.key]||0)/100}));
 return {sectors,headline:sectors.reduce((a,r)=>a+r.base*(1+r.growth),0)/result.priorGDP-1};
}
