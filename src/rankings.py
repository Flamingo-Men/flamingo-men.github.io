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

# ---- current power ranking (2026, completed weeks only) ----
W=json.load(open(D('data','weeks','2026.json')));T=W['teams'];cur=W.get('cur') or 99
done=[w for w in W['weeks'] if int(w)<cur]
rec=collections.defaultdict(lambda:dict(w=0,l=0,pf=0.0,ap_w=0,ap_l=0,last=[]))
for w in sorted(done,key=int):
    scores=[]
    for g in W['weeks'][w]:
        if g['tier']: continue
        for me,op in ((g['a'],g['b']),(g['b'],g['a'])):
            o=T[str(me['t'])][0];r=rec[o];r['pf']+=me['p'];r['last'].append(me['p'])
            r['w' if me['p']>op['p'] else 'l']+=1;scores.append((o,me['p']))
    for o,p in scores:
        rec[o]['ap_w']+=sum(1 for x,q in scores if x!=o and p>q);rec[o]['ap_l']+=sum(1 for x,q in scores if x!=o and p<q)
if rec:
    wp={o:r['w']/max(1,r['w']+r['l']) for o,r in rec.items()};ap={o:r['ap_w']/max(1,r['ap_w']+r['ap_l']) for o,r in rec.items()}
    pf=norm({o:r['pf'] for o,r in rec.items()});rc=norm({o:r['last'][-1] for o,r in rec.items()})
    sc={o:round(100*(.3*wp[o]+.35*ap[o]+.2*pf[o]+.15*rc[o]),1) for o in rec}
    out['current']=dict(weeks=len(done),rows=[dict(o=o,score=sc[o],team=next(v[1] for v in T.values() if v[0]==o),rec=f"{r['w']}-{r['l']}",pf=round(r['pf'],2),ap=f"{r['ap_w']}-{r['ap_l']}",lastw=round(r['last'][-1],2)) for o,r in sorted(rec.items(),key=lambda x:-sc[x[0]])])

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
json.dump(out,open(D('data','rankings.json'),'w'),separators=(',',':'))
for k,v in out.items():
    if k.endswith('Info'): continue
    rr=v['rows'] if isinstance(v,dict) else v
    print(k,[(r['o'],r['score']) for r in rr])
