# Builds ../data/skill.json: the trader, waiver and drafter rankings, scored to separate skill from luck.
# Usage: python3 skill.py CACHE_DIR   (ESPN cache from moves.py; run after moves.py, weeks.py, build.py and players.py; rankings.py reads the output)
#
# Trades (2018-2025): a trade's value to a team is how many points it added to that team's best possible lineup,
#   week by week (the roster that week vs the same roster with the trade undone), until a received player is traded again.
#   Scored two ways and averaged: with what players actually scored (results) and with ESPN's projection for the week of
#   the trade times the weeks left (the decision, judged on what was known at the time). Bench depth that would never
#   start adds nothing, so 3-for-1 consolidation trades aren't punished for the depth they give up.
# Waivers (2018-2025): points over a replacement starter from pickups while they were in the lineup, per season,
#   measured against that season's league average.
# Drafts (2016-2025): every QB/RB/WR/TE pick's season value over replacement, as a percentile against picks taken
#   within four spots of it across every draft; the owner's average percentile minus 50.
# Every owner's average is shrunk toward the league average by empirical Bayes (how much depends on how noisy that
# measure is and how many trades/seasons/picks the owner has), and a 90% bootstrap range is reported.
import json,os,sys,collections,random,statistics as st
here=os.path.dirname(os.path.abspath(__file__)); root=os.path.dirname(here); sys.path.insert(0,here)
import moves as M
D=lambda *p:os.path.join(root,*p)
MV=json.load(open(D('data','moves.json')))
idx=open(D('index.html')).read();i=idx.index('const LEAGUE');L=json.loads(idx[i:idx.index('\n',i)].split('=',1)[1].strip().rstrip(';'))
SLOTS={'QB':1,'RB':2,'WR':2,'TE':1,'D/ST':1,'K':1}
def best(pl,flex=1):
    by=collections.defaultdict(list)
    for p,v in pl: by[p].append(v)
    tot=0;left=[]
    for p,l in by.items():
        l.sort(reverse=True);n=SLOTS.get(p,0);tot+=sum(l[:n])
        if p in('RB','WR','TE'): left+=l[n:]
    left.sort(reverse=True);return tot+sum(left[:flex])
PROJ={}
def proj(y):
    if y not in PROJ:
        out={}
        for p in json.load(open(os.path.join(M.CACHE,f'pl_{y}.json'))):
            w={}
            for s in p.get('stats',[]):
                if s['seasonId']==y and s['statSourceId']==1 and s['statSplitTypeId']==1 and s['scoringPeriodId']>0 and 'stats' in s: w[s['scoringPeriodId']]=M.ppr(s['stats'],1)
            out[p['id']]=w
        PROJ[y]=out
    return PROJ[y]
WEEKS={}
def rosters(y):
    if y not in WEEKS:
        W=json.load(open(D('data','weeks',f'{y}.json')));T=W['teams'];out=collections.defaultdict(dict)
        for w,gs in W['weeks'].items():
            for g in gs:
                for s in 'ab': out[T[str(g[s]['t'])][0]][int(w)]=[(M.find(y,r[0],r[1]),r[1],r[3]) for r in g[s]['r']]
        WEEKS[y]=out
    return WEEKS[y]
def boot(v,n=4000):
    random.seed(1);m=sorted(st.mean(random.choices(v,k=len(v))) for _ in range(n));return m[int(.05*n)],m[int(.95*n)]
def shrink(groups,minn):
    allv=[x for v in groups.values() for x in v];g=st.mean(allv)
    s2=st.mean([st.pvariance(v) for v in groups.values() if len(v)>1])
    ms=[(st.mean(v),len(v)) for v in groups.values() if len(v)>=minn]
    tau2=max(1e-9,st.pvariance([m for m,_ in ms])-st.mean([s2/n for _,n in ms]));k=s2/tau2
    return g,k
def ranked(groups,minn,extra):
    g,k=shrink(groups,minn);rows=[]
    for o,v in groups.items():
        if len(v)<minn: continue
        m=st.mean(v);lo,hi=boot(v)
        rows.append(dict(o=o,shrunk=round((m-g)*len(v)/(len(v)+k),2),raw=round(m-g,1),lo=round(lo-g,1),hi=round(hi-g,1),n=len(v),**extra(o)))
    for r in rows: r['score']=r['shrunk'] if k<100 else r['raw']   # when differences are mostly noise, rank by the shrunk value but show the raw one
    return sorted(rows,key=lambda r:-r['shrunk']),dict(mean=round(g,1),k=round(k,1))

# ---- trades ----
wkof=lambda t:M.week_of(t['s'],t['d']) if t['d'][5:7] not in('01','02','03','04','05','06','07','08') else 1
done=sorted([t for t in L['trades'] if t['st']=='completed' and 2018<=t['s']<=2025],key=lambda t:(t['d'],t['id']))
def pinfo(y,g):
    nm,_,pos=g.partition('|')
    if pos in('Pick','Secret'): return None
    pid=M.find(y,nm,pos)
    return (pid,M.players(y)[pid]['pos'],M.players(y)[pid]['wk']) if pid is not None else None
def horizon(t,o,pids):
    for u in done:
        if u['s']==t['s'] and (u['d'],u['id'])>(t['d'],t['id']):
            for s in 'ab':
                if u[s]['o']==o and any((pinfo(u['s'],g) or [None])[0] in pids for g in u[s]['gave']): return wkof(u)-1
    return M.LASTWK(t['s'])
TV=collections.defaultdict(list);TD=collections.defaultdict(list)
for t in done:
    y=t['s'];w0=wkof(t);RO=rosters(y);PR=proj(y)
    for me,op in (('a','b'),('b','a')):
        o=t[me]['o']
        if not o or o not in RO: continue
        got=[x for x in (pinfo(y,g) for g in t[op]['gave']) if x];gave=[x for x in (pinfo(y,g) for g in t[me]['gave']) if x]
        gp={x[0] for x in got};end=horizon(t,o,gp);real=0.0
        for w in range(w0,end+1):
            r=RO[o].get(w)
            if not r: continue
            real+=best([(p,v) for _,p,v in r])-best([(p,v) for pid,p,v in r if pid not in gp]+[(pos,wk.get(w,0)) for _,pos,wk in gave])
        ex=0.0;wf=next((w for w in range(w0,w0+3) if w in RO[o]),None)
        if wf:
            pj=lambda pid:PR.get(pid,{}).get(wf,0);r=RO[o][wf];have={pid for pid,_,_ in r}
            act=[(p,pj(pid)) for pid,p,_ in r]+[(pos,pj(pid)) for pid,pos,_ in got if pid not in have]
            cf=[(p,pj(pid)) for pid,p,_ in r if pid not in gp]+[(pos,pj(pid)) for pid,pos,_ in gave]
            ex=(best(act)-best(cf))*(M.LASTWK(y)-wf+1)
        v=(real+ex)/2;TV[o].append(v)
        TD[o].append([t['id'],round(v,1),y,[g.split('|')[0] for g in t[op]['gave']][:3],t[op]['o'],round(real,1),round(ex,1)])
def trade_extra(o):
    l=TD[o];b=max(l,key=lambda x:x[1]);w=min(l,key=lambda x:x[1])
    return dict(real=round(st.mean(x[5] for x in l),1),proj=round(st.mean(x[6] for x in l),1),won=sum(x[1]>0 for x in l),best=b,worst=w)
out={}
out['trade'],out['tradeInfo']=ranked(TV,5,trade_extra)

# ---- waivers ----
WS=collections.defaultdict(lambda:collections.defaultdict(float));seasons=collections.defaultdict(set);adds=collections.Counter();hits=collections.Counter();bestp={}
for m in MV['moves']:
    if m['y']>=2026 or not m.get('o'): continue
    seasons[m['o']].add(m['y'])
    if m.get('add'): adds[m['o']]+=1
    if not m.get('add') or m.get('again') or m['add'][1] not in('QB','RB','WR','TE') or not m.get('st'): continue
    rp=MV['repl'][str(m['y'])][m['add'][1]];v=max(0.0,m['pts']-m['st']*rp);WS[m['o']][m['y']]+=v
    if m['st']>=3 and v>=20: hits[m['o']]+=1
    if m['o'] not in bestp or v>bestp[m['o']][1]: bestp[m['o']]=[m['add'][0],round(v,1),m['y'],m['st'],m['pts']]
ya={y:st.mean([WS[o][y] for o in seasons if y in seasons[o]]) for y in {y for s in seasons.values() for y in s}}
WG={o:[WS[o][y]-ya[y] for y in sorted(s)] for o,s in seasons.items()}
out['waiver'],out['waiverInfo']=ranked(WG,3,lambda o:dict(seasons=len(seasons[o]),adds=adds[o],hits=hits[o],perSeason=round(sum(WS[o].values())/len(seasons[o]),1),best=bestp.get(o)))

# ---- drafts ----
picks=[]
for y in range(2016,2026):
    for p in M.board_picks(y):
        if not p['pid'] or not p['o']: continue
        P=M.players(y)[p['pid']]
        if P['pos'] not in('QB','RB','WR','TE'): continue
        picks.append(dict(y=y,o=p['o'],pick=p['pick'],v=max(0.0,P['tot']-17*M.repl(y,P['pos'])),n=P['n'],pos=P['pos']))
by=collections.defaultdict(list)
for p in picks: by[p['pick']].append(p['v'])
for p in picks:
    pool=[v for k in range(p['pick']-4,p['pick']+5) for v in by.get(k,[])]
    p['pct']=100*(sum(v<p['v'] for v in pool)+sum(v==p['v'] for v in pool)/2)/len(pool)
DG=collections.defaultdict(list)
for p in picks: DG[p['o']].append(p['pct']-50)
def draft_extra(o):
    mine=[p for p in picks if p['o']==o];ys=sorted({p['y'] for p in mine})
    late=[p for p in mine if p['pick']>24] or mine;steal=max(late,key=lambda p:(p['v'],p['pct']))   # best value found after the first few rounds
    early=[p for p in mine if p['pick']<=30]
    return dict(drafts=len(ys),steal=[steal['n'],steal['pick'],round(steal['v'],1),steal['y']],early=round(st.mean(p['pct'] for p in early)-50,1) if early else None)
out['draft'],out['draftInfo']=ranked({o:v for o,v in DG.items() if len({p['y'] for p in picks if p['o']==o})>=3},30,draft_extra)
json.dump(out,open(D('data','skill.json'),'w'),separators=(',',':'))
for k in('trade','waiver','draft'): print(k,out[k+'Info'],[(r['o'],r['score'],r['lo'],r['hi']) for r in out[k]])
