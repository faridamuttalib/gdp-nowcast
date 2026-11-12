import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import {forecast,reviewModel,scenario,quarterIndex} from '../dist/model.js';
const data=JSON.parse(fs.readFileSync(new URL('./fixtures/excel-reference.json',import.meta.url)));
const expected=JSON.parse(fs.readFileSync(new URL('./fixtures/expected.json',import.meta.url)));
const near=(a,b)=>assert.ok(Math.abs(a-b)<1e-10,`${a} != ${b}`);
test('Early web model reproduces all six approved Excel review forecasts',()=>{
 const r=reviewModel(data,'Early');assert.equal(r.n,6);near(r.mae,expected.early.mae_pp);
 r.rows.forEach((row,i)=>near(row.prediction,expected.early.rows[i].prediction));
});
test('Pre-GDP web model reproduces all six quarterly-model forecasts',()=>{
 const r=reviewModel(data,'Pre-GDP');assert.equal(r.n,6);near(r.mae,expected.quarterly.mae_pp);
 r.rows.forEach((row,i)=>near(row.prediction,expected.quarterly.rows[i].prediction));
});
test('Approved Q3 2026 early headline and official-total denominator',()=>{
 const f=forecast(data,{quarter:'2026Q3',cutoff:'2026-10-21',mode:'Auto'});
 assert.equal(f.stage,'Early');near(f.headline,.04930716341554797);near(f.sectors.reduce((a,s)=>a+s.contribution,0)+f.roundingContribution,f.headline*100);
});
test('Publication-date boundaries prevent future monthly and quarterly observations',()=>{
 assert.throws(()=>forecast(data,{quarter:'2026Q3',cutoff:'2026-10-08',mode:'Auto'}),/unavailable/);
 assert.throws(()=>forecast(data,{quarter:'2026Q1',cutoff:'2026-05-12',mode:'Pre-GDP'}),/Pre-GDP is not available/);
 assert.equal(forecast(data,{quarter:'2026Q1',cutoff:'2026-05-14',mode:'Auto'}).stage,'Pre-GDP');
});
test('Historical cutoff never shows future actual GDP in the review metrics',()=>{
 const r=reviewModel(data,'Pre-GDP','2026-05-14');assert.equal(r.n,4);assert.ok(r.rows.slice(4).every(r=>r.error&&!r.actual));
});
test('GDP for target and later quarters cannot change the forecast',()=>{
 const options={quarter:'2026Q1',cutoff:'2026-05-14',mode:'Pre-GDP'};
 const before=forecast(data,options);const modified=structuredClone(data);
 for(const row of modified.gdp)if(quarterIndex(row.quarter)>=quarterIndex(options.quarter))for(const key of Object.keys(row))if(key!=='quarter')row[key]=9999999;
 const after=forecast(modified,options);near(before.headline,after.headline);
});
test('Missing inputs fail explicitly; zero is retained as a numeric level',()=>{
 const missing=structuredClone(data);missing.monthly.find(r=>r.date==='2026-08-01').cpo=null;
 assert.throws(()=>forecast(missing,{quarter:'2026Q3',cutoff:'2026-10-21',mode:'Early'}),/Agriculture/);
 const zero=structuredClone(data);zero.monthly.find(r=>r.date==='2026-08-01').cpo=0;
 assert.ok(Number.isFinite(forecast(zero,{quarter:'2026Q3',cutoff:'2026-10-21',mode:'Early'}).headline));
});
test('Scenario contributions follow sector weights; baseline stays unchanged',()=>{
 const f=forecast(data,{quarter:'2026Q3',cutoff:'2026-10-21',mode:'Early'}),baseline=f.headline;
 const s=scenario(f,{services:1});near(s.headline-baseline,f.sectors[4].weight*.01);near(f.headline,baseline);
});
test('Operational data schema supports a valid current forecast',()=>{
 const live=JSON.parse(fs.readFileSync(new URL('../dist/data/model-data.json',import.meta.url)));
 assert.ok(live.sources.length===7&&live.gdp.length>=46);
 const f=forecast(live,{quarter:'2026Q3',cutoff:'2026-11-12',mode:'Auto'});assert.ok(Number.isFinite(f.headline));
});

test('Fixed services factor is prospective, stage-specific, and reconciles through GDP weights',()=>{
 const live=JSON.parse(fs.readFileSync(new URL('../dist/data/model-data.json',import.meta.url)));
 // Use a known complete quarter copied to a future label, preserving all release gates.
 const fixture=structuredClone(live);
 const q=fixture.quarterly.find(r=>r.quarter==='2026Q2');
 fixture.quarterly.push({...q,quarter:'2026Q3',servicesPublished:'2026-11-01',constructionPublished:'2026-11-01'});
 for(const source of ['ipi','retail'])fixture.releases[source]['2026-09-01']='2026-11-01';
 for(const [i,month] of ['07','08','09'].entries()){
  const row=fixture.monthly.find(r=>r.date===`2026-${month}-01`);
  if(!row)fixture.monthly.push({...fixture.monthly.find(r=>r.date===`2026-0${i+4}-01`),date:`2026-${month}-01`});
  else for(const key of ['cpo','mining','manufacturing'])if(!Number.isFinite(row[key]))row[key]=fixture.monthly.find(r=>r.date===`2026-0${i+4}-01`)[key];
 }
 const options={quarter:'2026Q3',cutoff:'2026-11-12',mode:'Pre-GDP'};
 const raw=forecast(fixture,{...options,applyAddFactors:false}),adjusted=forecast(fixture,options);
 near(adjusted.sectors[4].growth-raw.sectors[4].growth,.002);
 near(adjusted.headline-raw.headline,raw.sectors[4].weight*.002);
 near(adjusted.sectors.reduce((a,s)=>a+s.contribution,0)+adjusted.roundingContribution,adjusted.headline*100);
 assert.ok(adjusted.sectors.filter(s=>s.key!=='services').every(s=>s.addFactorPP===0));
 assert.ok(forecast(fixture,{...options,mode:'Early'}).sectors.every(s=>s.addFactorPP===0));
 assert.ok(forecast(fixture,{...options,cutoff:'2026-11-11'}).sectors.every(s=>s.addFactorPP===0));
});
