# Builds ../data/players.json for the player cards and site search: every player who touched the league
# (drafted, on a weekly lineup, added, dropped or traded), with ESPN season stats for each year, which league
# team held him each week, and every draft, waiver and trade move involving him.
# Usage: python3 players.py CACHE_DIR   (same ESPN cache as moves.py; run after moves.py, weeks.py and build.py)
import json,os,sys,collections
here=os.path.dirname(os.path.abspath(__file__)); root=os.path.dirname(here); sys.path.insert(0,here)
import moves as M
D=lambda *p:os.path.join(root,*p)
YEARS=list(range(2016,2027))
NFL={1:'ATL',2:'BUF',3:'CHI',4:'CIN',5:'CLE',6:'DAL',7:'DEN',8:'DET',9:'GB',10:'TEN',11:'IND',12:'KC',13:'LV',14:'LAR',15:'MIA',16:'MIN',17:'NE',18:'NO',
     19:'NYG',20:'NYJ',21:'PHI',22:'ARI',23:'PIT',24:'LAC',25:'SF',26:'SEA',27:'TB',28:'WSH',29:'CAR',30:'JAX',33:'BAL',34:'HOU'}
def nfl(y,t):
    a=NFL.get(t)
    if a=='LV' and y<=2019: return 'OAK'
    if a=='LAC' and y<=2016: return 'SD'
    return a
# season stat line: games, pass att/cmp/yds/td/int, rush att/yds/td, rec/tgt/yds/td, fumbles lost
LINE=['210','0','1','3','4','20','23','24','25','53','58','42','43','72']

MV=json.load(open(D('data','moves.json')))
idx=open(D('index.html')).read();i=idx.index('const LEAGUE');L=json.loads(idx[i:idx.index('\n',i)].split('=',1)[1].strip().rstrip(';'))
TRI=[[138,139,140]]   # three-team trade legs (template.html TRI)

def raw(y):
    out={}
    for p in json.load(open(os.path.join(M.CACHE,f'pl_{y}.json'))):
        team=None;line=None
        for s in p.get('stats',[]):
            if s['seasonId']!=y or s['statSourceId']!=0 or 'stats' not in s: continue
            if s['statSplitTypeId']==1 and s.get('proTeamId'): team=s['proTeamId']
            if s['statSplitTypeId']==0 and s['scoringPeriodId']==0: line=[round(s['stats'].get(k,0)) for k in LINE]
        out[p['id']]=(team or p.get('proTeamId'),line)
    return out

P={}            # pid -> player record
alias={}        # normalized name -> pid
def rec(y,name,pos=None):
    pid=M.find(y,name,pos)
    if pid is None: return None
    if pid not in P:
        info=M.players(y)[pid]
        P[pid]=dict(n=info['n'],pos=info['pos'],y={},mv=[])
    alias.setdefault(M.norm(name),pid);alias.setdefault(M.norm(P[pid]['n']),pid)
    return P[pid]
def season(r,y):
    return r['y'].setdefault(y,dict(own={}))

# weekly lineups, 2018 on: who held him each week and whether he started
for y in YEARS:
    f=D('data','weeks',f'{y}.json')
    if not os.path.exists(f): continue
    W=json.load(open(f));T=W['teams']
    for w,gs in W['weeks'].items():
        for g in gs:
            for side in ('a','b'):
                o=T[str(g[side]['t'])][0]
                for nm,pos,slot,pts in g[side]['r']:
                    r=rec(y,nm,pos)
                    if r: season(r,y)['own'][int(w)]=[o,0 if slot in('BE','IR') else 1]
# drafts (sticker boards for every year)
for y in YEARS:
    for p in M.board_picks(y):
        if not p['o']: continue
        r=rec(y,p['n'],p['pos'])
        if not r: continue
        n=len(M.DR[str(y)]['cols']);season(r,y)
        r['mv'].append(dict(y=y,k='draft',o=p['o'],pick=p['pick'],rd=(p['pick']-1)//n+1))
# waiver and free agent adds and drops (ESPN, 2018 on)
for m in MV['moves']:
    y=m['y']
    for key,kind in (('add','add'),('drop','drop')):
        if not m.get(key): continue
        r=rec(y,m[key][0],m[key][1])
        if not r: continue
        season(r,y)
        e=dict(y=y,d=m['d'],w=m['w'],k=kind,o=m['o'],via=m['k'])
        if kind=='add' and m.get('st') is not None: e.update(st=m['st'],pts=m.get('pts'))
        r['mv'].append(e)
# trades (completed and vetoed)
tri={i:g for g in TRI for i in g}
for t in L['trades']:
    for side,other in (('a','b'),('b','a')):
        for g in t[side]['gave']:
            nm,_,pos=g.partition('|')
            if pos in('Pick','Secret'): continue
            r=rec(t['s'],nm,pos)
            if not r: continue
            season(r,t['s'])
            r['mv'].append(dict(y=t['s'],d=t['d'],k='trade',o=t[side]['o'],to=t[other]['o'],id=tri.get(t['id'],[t['id']])[0],st=t['st']))
# 2016 and 2017 have no weekly lineups: use the rebuilt end-of-season rosters
for y in (2016,2017):
    for o,R in MV['rosters'].get(str(y),{}).items():
        for p in R['players']:
            r=rec(y,p[1],p[2] or None)
            if r: season(r,y).setdefault('roster',[]).append(o)

# stats for every season each player has, not just the league ones
for y in YEARS:
    PY=M.players(y);RW=raw(y);rank={}
    by=collections.defaultdict(list)
    for i,p in PY.items(): by[p['pos']].append((p['tot'],i))
    for pos,l in by.items():
        for k,(t,i) in enumerate(sorted(l,reverse=True)): rank[i]=k+1
    for pid,r in P.items():
        p=PY.get(pid)
        if not p or (not p['tot'] and y not in r['y']): continue
        s=season(r,y);team,line=RW.get(pid,(None,None))
        s['pts']=round(p['tot'],1);s['rk']=rank.get(pid);s['nfl']=nfl(y,team)
        if line: s['ln']=line
        if p['wk']: s['wk']={w:round(v,1) for w,v in p['wk'].items()}
    for pid,r in P.items():
        if y in r['y'] and r['y'][y].get('pts') is None and not r['y'][y]['own'] and not r['y'][y].get('roster') and not any(m['y']==y for m in r['mv']): del r['y'][y]

# compact output: owner weeks as {owner:[[week,started],...]} summaries are built in the browser
out={}
for pid,r in P.items():
    if not r['y']: continue
    for y,s in r['y'].items():
        if not s['own']: s.pop('own')
        else: s['own']={w:v for w,v in sorted(s['own'].items())}
    r['mv'].sort(key=lambda m:(m['y'],m.get('d') or f"{m['y']}-08-01",{'draft':0,'trade':2}.get(m['k'],1)))
    out[pid]=r
names={k:v for k,v in alias.items() if v in out}
json.dump(dict(p=out,names=names),open(D('data','players.json'),'w'),ensure_ascii=False,separators=(',',':'))
print('players',len(out),'names',len(names),'bytes',os.path.getsize(D('data','players.json')))
