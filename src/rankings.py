# Builds ../data/rankings.json for the Rankings tab. Run after moves.py, weeks.py, playoffs.py and build.py.
import json,os,collections,math
here=os.path.dirname(os.path.abspath(__file__)); root=os.path.dirname(here); D=lambda *p:os.path.join(root,*p)
MV=json.load(open(D('data','moves.json')));PO=json.load(open(D('data','playoffs.json')))
idx=open(D('index.html')).read();i=idx.index('const LEAGUE');L=json.loads(idx[i:idx.index('\n',i)].split('=',1)[1].strip().rstrip(';'))
S=L['stats'];TR={t['id']:t for t in L['trades']}
CHAMPS={2016:'duane',2017:'kyle',2018:'fluff',2019:'charles',2020:'charles',2021:'squirm',2022:'charles',2023:'kyle',2024:'dylan',2025:'kyle'}
SACKOS={2016:'fluff',2017:'peanut',2018:'quincy',2019:'dilapi',2020:'dilapi',2021:'lucas',2022:'jordan',2023:'peanut',2024:'lucas',2025:'quincy'}
PLAYOFF={2016:{'charles','peanut','duane','squirm'},2017:{'kyle','charles','vicente','squirm'}}
FINAL={2016:{'duane','charles'},2017:{'kyle'}}
for y,P in PO.items():
    y=int(y)
    if not P.get('rounds'): continue
    PLAYOFF[y]={s['o'] for m in P['rounds'][0] for s in (m['a'],m['b'])}|{b['o'] for b in P.get('byes',[])}
    f=P['rounds'][-1][0];FINAL[y]={f['a']['o'],f['b']['o']}
DRAFT_YEARS={}
for y in range(2016,2026):
    o_s=set(MV['draftScore'].get(str(y),{}))|{o for o,v in S.items() if str(y) in v['seasons']}
    DRAFT_YEARS[y]=o_s
out={}
norm=lambda vals:(lambda lo,hi:{k:(v-lo)/(hi-lo) if hi>lo else .5 for k,v in vals.items()})(min(vals.values()),max(vals.values()))

# ---- current power ranking (2026): playoff odds + current roster strength (Kyle, 2026-11-06) ----
# Usage: python3 rankings.py [CACHE_DIR]. Needs CACHE_DIR's full_2026.json (rosters) and newest box_2026_N.json (schedule).
import sys,random,statistics as st,glob
W=json.load(open(D('data','weeks','2026.json')));T=W['teams'];cur=W.get('cur') or 99
done=[w for w in W['weeks'] if int(w)<cur]
rec=collections.defaultdict(lambda:dict(w=0,l=0,pf=0.0,last=[]))
for w in sorted(done,key=int):
    for g in W['weeks'][w]:
        if g['tier']: continue
        for me,op in ((g['a'],g['b']),(g['b'],g['a'])):
            o=T[str(me['t'])][0];r=rec[o];r['pf']+=me['p'];r['last'].append(me['p'])
            r['w' if me['p']>op['p'] else 'l']+=1
CACHE=sys.argv[1] if len(sys.argv)>1 else None
if rec and CACHE:
    full=json.load(open(os.path.join(CACHE,'full_2026.json')))
    boxes=sorted(glob.glob(os.path.join(CACHE,'box_2026_*.json')),key=lambda f:int(f.rsplit('_',1)[1][:-5]))
    sched=json.load(open(boxes[-1]))['schedule']
    owner={int(k):v[0] for k,v in T.items()}
    div={t['id']:t.get('divisionId',0) for t in full['teams']}
    POS={1:'QB',2:'RB',3:'WR',4:'TE',5:'K',16:'D/ST'}
    def val(p,inj):
        a=pr=None
        for x in p.get('stats',[]):
            if x.get('seasonId')==2026 and x.get('scoringPeriodId')==0 and x.get('statSplitTypeId')==0:
                if x.get('statSourceId')==0 and x.get('appliedAverage') is not None and x.get('appliedTotal',0)>0: a=x['appliedAverage']
                if x.get('statSourceId')==1 and x.get('appliedAverage') is not None: pr=x['appliedAverage']
        v=(a+pr)/2 if a is not None and pr is not None else (pr if pr is not None else (a or 0))
        if inj in('INJURY_RESERVE','SUSPENSION'): v=0
        elif inj=='OUT': v*=.5
        return v
    strength={};lineup={}
    for t in full['teams']:
        by=collections.defaultdict(list)
        for e in t.get('roster',{}).get('entries',[]):
            p=e['playerPoolEntry']['player'];pos=POS.get(p['defaultPositionId'])
            if pos: by[pos].append((val(p,p.get('injuryStatus') or e.get('injuryStatus')),p['fullName'],pos))
        for k in by: by[k].sort(reverse=True)
        pick=by['QB'][:1]+by['RB'][:2]+by['WR'][:2]+by['TE'][:1]+by['K'][:1]+by['D/ST'][:1]
        flex=sorted(by['RB'][2:]+by['WR'][2:]+by['TE'][1:],reverse=True)[:2]
        pick+=flex;o=owner[t['id']]
        strength[o]=sum(x[0] for x in pick);lineup[o]=[x[1] for x in sorted(pick,reverse=True)[:3]]
    # each sim game: mean blends roster strength (60%) with points per game so far (40%); spread from this season's scores
    avg={o:r['pf']/max(1,len(r['last'])) for o,r in rec.items()}
    mu={o:.6*strength[o]+.4*avg[o] for o in rec}
    sd=st.pstdev([p-avg[o] for o,r in rec.items() for p in r['last']]) or 25
    REG=full['settings']['scheduleSettings'].get('matchupPeriodCount',14)
    left=[(m['home']['teamId'],m['away']['teamId']) for m in sched if m['matchupPeriodId']>=cur and m['matchupPeriodId']<=REG and m.get('away')]
    random.seed(2026);N=20000;made=collections.Counter()
    for _ in range(N):
        w={o:r['w'] for o,r in rec.items()};pf={o:r['pf'] for o,r in rec.items()}
        for h,a in left:
            oh,oa=owner[h],owner[a];ph=random.gauss(mu[oh],sd);pa=random.gauss(mu[oa],sd)
            pf[oh]+=ph;pf[oa]+=pa;w[oh if ph>pa else oa]+=1
        key=lambda o:(w[o],pf[o])
        ids={owner[k]:k for k in owner}
        dw=[max((o for o in rec if div[ids[o]]==d),key=key) for d in (0,1)]
        rest=sorted((o for o in rec if o not in dw),key=key,reverse=True)[:4]
        for o in dw+rest: made[o]+=1
    odds={o:100*made[o]/N for o in rec}
    rs=norm(strength)
    sc={o:round(.5*odds[o]+50*rs[o],1) for o in rec}
    out['current']=dict(weeks=len(done),left=len({m['matchupPeriodId'] for m in sched if cur<=m['matchupPeriodId']<=REG}),rows=[dict(o=o,score=sc[o],team=next(v[1] for v in T.values() if v[0]==o),rec=f"{r['w']}-{r['l']}",pf=round(r['pf'],2),odds=round(odds[o],1),str=round(strength[o],1),top=lineup[o]) for o,r in sorted(rec.items(),key=lambda x:-sc[x[0]])])
elif rec: print('rankings.py: no CACHE_DIR given, 2026 power ranking not rebuilt')
if 'current' not in out:
    try: out['current']=json.load(open(D('data','rankings.json')))['current']
    except Exception: pass

# ---- all-time power ranking ----
rows={}
for o,v in S.items():
    seas=[y for y in range(2016,2026) if str(y) in v['seasons'] or o in DRAFT_YEARS.get(y,())]
    if len(seas)<3: continue
    w=sum(v['seasons'][str(y)]['w'] for y in seas if str(y) in v['seasons']);l=sum(v['seasons'][str(y)]['l'] for y in seas if str(y) in v['seasons'])
    pidx=[]
    for y in seas:
        r=v['seasons'].get(str(y))
        if not r or r.get('pts') is None: continue
        lg=[x['seasons'][str(y)]['pts'] for x in S.values() if str(y) in x['seasons'] and x['seasons'][str(y)].get('pts')]
        pidx.append(r['pts']/(sum(lg)/len(lg)))
    rows[o]=dict(o=o,seasons=len(seas),rec=f"{w}-{l}",pct=w/max(1,w+l),pidx=sum(pidx)/len(pidx) if pidx else 1,
        titles=sum(1 for y in seas if CHAMPS.get(y)==o),finals=sum(1 for y in seas if o in FINAL.get(y,())),
        po=sum(1 for y in seas if o in PLAYOFF.get(y,())),sackos=sum(1 for y in seas if SACKOS.get(y)==o))
k=4
P=norm({o:(r['pct']*r['seasons']+.5*k)/(r['seasons']+k) for o,r in rows.items()});X=norm({o:r['pidx'] for o,r in rows.items()})
# titles and finals count in total (a title is a title); playoff and Sacko rates are shrunk toward the league
# average with four phantom seasons so a three-year owner can't top the list on a small sample
k=4;mpo=sum(r['po'] for r in rows.values())/sum(r['seasons'] for r in rows.values());msk=sum(r['sackos'] for r in rows.values())/sum(r['seasons'] for r in rows.values())
Tt=norm({o:r['titles'] for o,r in rows.items()});F=norm({o:r['finals'] for o,r in rows.items()})
Po=norm({o:(r['po']+k*mpo)/(r['seasons']+k) for o,r in rows.items()});Sk=norm({o:(r['sackos']+k*msk)/(r['seasons']+k) for o,r in rows.items()})
for o,r in rows.items():
    r['score']=round(100*(.25*P[o]+.1*X[o]+.3*Tt[o]+.1*F[o]+.2*Po[o]+.05*(1-Sk[o])),1);r['pct']=round(r['pct']*100,1);r['pidx']=round(r['pidx']*100,1)
out['alltime']=sorted(rows.values(),key=lambda r:-r['score'])

# ---- drafting ----
dr=collections.defaultdict(list);best={}
for y,d in MV['draftScore'].items():
    for o,v in d.items():
        dr[o].append((v['score'],int(y)))
        if v['best'] and (o not in best or v['best'][2]>best[o][3]): best[o]=v['best']+[int(y)]
out['draft']=sorted([dict(o=o,score=round(sum(s for s,_ in v)/len(v),1),seasons=len(v),bestYear=max(v)[1],bestYearScore=round(max(v)[0],1),worstYear=min(v)[1],worstYearScore=round(min(v)[0],1),steal=best.get(o)) for o,v in dr.items() if len(v)>=3],key=lambda r:-r['score'])

# ---- trading ----
tr=collections.defaultdict(lambda:dict(net=0.0,n=0,won=0,best=None,worst=None,yrs=set()))
TRI=[[138,139,140]]   # three-team trades stored as two-team legs (same as TRI in template.html); count each as one trade
key=lambda tid:next((g[0] for g in TRI if tid in g),tid)
per={}   # (trade key, owner) -> [net, got, year, other owners]
for tid,x in MV['trades'].items():
    t=TR.get(int(tid))
    if not t or t['st']!='completed': continue
    for me,op in (('a','b'),('b','a')):
        o=t[me]['o']
        if not o: continue
        e=per.setdefault((key(int(tid)),o),[0.0,[],t['s'],[]]);e[0]+=x[me]['par']-x[op]['par'];e[1]+=[g[0] for g in x[me]['got']];e[3].append(t[op]['o'])
for (tid,o),(d,got,y,ops) in per.items():
        r=tr[o];r['net']+=d;r['n']+=1;r['won']+=d>0;r['yrs'].add(y)
        item=[tid,round(d,1),y,got[:3],ops[0]]
        if not r['best'] or d>r['best'][1]: r['best']=item
        if not r['worst'] or d<r['worst'][1]: r['worst']=item
out['trade']=sorted([dict(o=o,score=round(r['net'],1),n=r['n'],won=r['won'],avg=round(r['net']/r['n'],1),best=r['best'],worst=r['worst']) for o,r in tr.items() if r['n']>=5],key=lambda r:-r['score'])

# ---- waivers (ESPN 2018 on): points over a replacement starter while the pickup was in the lineup ----
wv=collections.defaultdict(lambda:dict(val=0.0,n=0,hits=0,best=None,yrs=set()))
for m in MV['moves']:
    if not m.get('add') or m.get('again') or m['y']>=2026 or m['add'][1] not in('QB','RB','WR','TE') or not m.get('st'): continue
    rp=MV['repl'][str(m['y'])][m['add'][1]];v=max(0.0,m['pts']-m['st']*rp)
    r=wv[m['o']];r['val']+=v;r['yrs'].add(m['y'])
    if m['st']>=3 and v>=20: r['hits']+=1
    if not r['best'] or v>r['best'][1]: r['best']=[m['add'][0],round(v,1),m['y'],m['st'],m['pts']]
for m in MV['moves']:
    if m.get('add') and m['y']<2026 and m['o']: wv[m['o']]['n']+=1; wv[m['o']]['yrs'].add(m['y'])
out['waiver']=sorted([dict(o=o,score=round(r['val']/len(r['yrs']),1),seasons=len(r['yrs']),total=round(r['val'],1),adds=r['n'],hits=r['hits'],best=r['best']) for o,r in wv.items() if len(r['yrs'])>=3],key=lambda r:-r['score'])
# trader, waiver and drafter rankings come from skill.py (lineup impact, luck vs skill, uncertainty) when it has been run
if os.path.exists(D('data','skill.json')):
    SK=json.load(open(D('data','skill.json')))
    for k in ('trade','waiver','draft'): out[k]=SK[k];out[k+'Info']=SK[k+'Info']
# ---- playoff appearances and droughts, 2016-2025 (seasons an owner sat out are skipped, not counted) ----
pl={}
for o,v in S.items():
    seas=[y for y in range(2016,2026) if str(y) in v['seasons'] or o in DRAFT_YEARS.get(y,())]
    if not seas: continue
    made=[y for y in seas if o in PLAYOFF.get(y,())];run=[];best=[]
    for y in seas:
        run=[] if y in made else run+[y]
        if len(run)>len(best): best=list(run)
    pl[o]=dict(po=len(made),seasons=len(seas),years=made,drought=len(best),dfrom=best[0] if best else None,dto=best[-1] if best else None,cur=len(run),last=made[-1] if made else None)
out['playoffs']=pl
json.dump(out,open(D('data','rankings.json'),'w'),separators=(',',':'))
for k,v in out.items():
    if k.endswith('Info') or k=='playoffs': continue
    rr=v['rows'] if isinstance(v,dict) else v
    print(k,[(r['o'],r['score']) for r in rr])
