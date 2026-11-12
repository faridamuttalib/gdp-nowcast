// Retrospective latest-vintage review. No Q3 2026 target is used for calibration.
import fs from 'node:fs';
import {forecast,SECTORS} from '../dist/model.js';
const data=JSON.parse(fs.readFileSync(new URL('../dist/data/model-data.json',import.meta.url)));
const mean=x=>x.reduce((a,b)=>a+b,0)/x.length;
const mae=x=>mean(x.map(Math.abs));
const rmse=x=>Math.sqrt(mean(x.map(v=>v*v)));
const output={snapshotId:data.snapshotId,calibration:'2023Q1–2024Q4',review:'2025Q1–2026Q2',stages:{}};
for(const stage of ['Early','Pre-GDP']){
 const rows=[];
 for(const g of data.gdp.filter(r=>r.quarter>='2023Q1'&&r.quarter<='2026Q2')){
  const release=data.releases.gdp?.[g.quarter];
  if(!release)throw new Error(`Missing GDP publication date: ${g.quarter}`);
  const prior=data.gdp.find(r=>r.quarter===`${+g.quarter.slice(0,4)-1}${g.quarter.slice(4)}`);
  const cutoff=new Date(Date.parse(release)-86400000).toISOString().slice(0,10);
  const f=forecast(data,{quarter:g.quarter,cutoff,mode:stage,applyAddFactors:false});
  rows.push({quarter:g.quarter,headlineErrorPP:(f.headline-(g.total/prior.total-1))*100,
   servicesWeight:f.sectors.find(s=>s.key==='services').weight,
   errorsPP:Object.fromEntries(f.sectors.map(s=>[s.key,(g[s.key]/prior[s.key]-1-s.growth)*100]))});
 }
 const train=rows.filter(r=>r.quarter<'2025Q1'),review=rows.filter(r=>r.quarter>='2025Q1');
 if(train.length!==8||review.length!==6)throw new Error('Incomplete calibration/review sample');
 const sectors=SECTORS.map(s=>{
  const a=train.map(r=>r.errorsPP[s.key]),b=review.map(r=>r.errorsPP[s.key]);
  const candidatePP=Math.round(mean(a)*10)/10;
  return {sector:s.key,calibrationMeanActualMinusModelPP:mean(a),candidatePP,
   calibrationSameSignCount:a.filter(v=>Math.sign(v)===Math.sign(candidatePP)).length,
   reviewBiasPP:mean(b),rawMAE:mae(b),candidateMAE:mae(b.map(v=>v-candidatePP)),
   rawRMSE:rmse(b),candidateRMSE:rmse(b.map(v=>v-candidatePP))};
 });
 const factor=stage==='Pre-GDP'?0.2:0;
 const raw=review.map(r=>r.headlineErrorPP),adjusted=review.map(r=>r.headlineErrorPP+r.servicesWeight*factor);
 output.stages[stage]={sectors,headline:{rawMAE:mae(raw),adjustedMAE:mae(adjusted),rawRMSE:rmse(raw),adjustedRMSE:rmse(adjusted)},rows};
}
process.stdout.write(JSON.stringify(output,null,2)+'\n');
