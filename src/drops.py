# Builds ../data/drops.json: the worst drops of all time, for the Rankings tab (Kyle 2026-11-23).
# A drop is judged by what the player did for everyone else after he was cut, using the same fantasy WAR as trades
# (moves.py): every week from the drop to the end of that season that he was in another team's starting lineup, in games
# that mattered (regular season, plus playoff weeks for teams still alive; consolation weeks don't count), his edge is his
# points minus a league-size replacement starter at his position (repl_n: the first player past N teams x slots; K and D/ST
# against the average started one), turned into wins with Phi(edge / (sd * sqrt 2)) - 0.5, sd = that season's weekly score SD.
# Weeks still being played never count. Once the team that cut him has him back (re-added or traded for), the drop stops
# counting. Kickers and defenses are left out, since they're streamed every week.
# Reads data/moves.json, data/weeks/*.json and data/players.json. Run after weeks.py, moves.py and players.py, before build.py.
import json,os,glob,math,collections,unicodedata,re
here=os.path.dirname(os.path.abspath(__file__)); root=os.path.dirname(here)
D=lambda *p:os.path.join(root,'data',*p)
MV=json.load(open(D('moves.json'))); PJ=json.load(open(D('players.json')))['p']
PHI=lambda z:0.5*(1+math.erf(z/math.sqrt(2)))
def norm(n):
    n=unicodedata.normalize('NFKD',n).encode('ascii','ignore').decode().lower()
    n=re.sub(r"\b(jr|sr|ii|iii|iv|v)\b\.?","",n); return re.sub(r"[^a-z]","",n)
def slots(y):
    fx=2 if y>=2026 else 1
    return {'QB':1,'RB':2+.45*fx,'WR':2+.5*fx,'TE':1+.05*fx}
# season points by positional rank, from players.json (a missing rank is filled from its neighbours)
RK=collections.defaultdict(dict)
for v in PJ.values():
    for y,s in v['y'].items():
        if s.get('rk') and v['pos'] in('QB','RB','WR','TE'): RK[(int(y),v['pos'])][s['rk']]=s['pts']
def rank_pts(y,pos,r):
    d=RK[(y,pos)]
    if r in d: return d[r]
    lo=max((k for k in d if k<r),default=None);hi=min((k for k in d if k>r),default=None)
    if lo and hi: return d[lo]+(d[hi]-d[lo])*(r-lo)/(hi-lo)
    return d.get(lo) or d.get(hi) or 0
out=[]
for f in sorted(glob.glob(D('weeks','*.json'))):
    y=int(os.path.basename(f)[:4]);wj=json.load(open(f));T=wj['teams'];cur=wj.get('cur')
    n=len(T)
    done=[int(w) for w,ms in wj['weeks'].items() if (not cur or int(w)<cur) and all(m['a']['p'] is not None for m in ms)]
    games=16 if y<=2020 else (17 if not cur else len([w for w in done if all(not m['tier'] for m in wj['weeks'][str(w)])]))
    REP={pos:rank_pts(y,pos,int(n*v+.5)+1)/games for pos,v in slots(y).items()}
    sc=[];kd=collections.defaultdict(list);start=collections.defaultdict(list);back=collections.defaultdict(list)   # norm name -> [(week, owner, pts, pos)]
    for w in done:
        for m in wj['weeks'][str(w)]:
            for k in('a','b'):
                s=m.get(k)
                if not s or s['p'] is None: continue
                if not m['tier']: sc.append(s['p'])
                if m['tier']=='Consolation': continue
                o=T[str(s['t'])][0]
                for nm,pos,sl,pts in s['r']:
                    if sl in('BE','IR'): back[norm(nm)].append((w,o));continue
                    if sl=='K': kd['K'].append(pts)
                    if sl=='D/ST': kd['D/ST'].append(pts)
                    start[norm(nm)].append((w,o,pts or 0,pos))
    mu=sum(sc)/len(sc);sd=math.sqrt(sum((v-mu)**2 for v in sc)/(len(sc)-1))
    for k,l in kd.items(): REP[k]=sum(l)/len(l)
    for i,m in enumerate(MV['moves']):
        if m['y']!=y or 'drop' not in m: continue
        nm,pos=m['drop'];rw=REP.get(pos,0)
        if pos not in('QB','RB','WR','TE'): continue          # kickers and defenses are streamed every week
        pts=par=war=0.0;st=0;who=collections.Counter()
        # the drop stops costing him once he's back on the team that cut him
        end=min([w for w,o in back.get(norm(nm),[])+[(a,b) for a,b,_,_ in start.get(norm(nm),[])] if o==m['o'] and w>m['w']]+[99])
        for w,o,v,p in start.get(norm(nm),[]):
            if w<m['w'] or w>=end or o==m['o']: continue
            st+=1;pts+=v;par+=v-rw;war+=PHI((v-rw)/(sd*math.sqrt(2)))-0.5;who[o]+=1
        if st: out.append(dict(i=i,y=y,w=m['w'],d=m['d'],o=m['o'],team=m['team'],p=nm,pos=pos,add=(m.get('add') or [None])[0],
            st=st,pts=round(pts,1),par=round(par,1),war=round(war,2),to=[o for o,_ in who.most_common()]))
# one entry per player per season: if he was cut more than once, the cut that cost the most counts
best={}
for e in out:
    k=(e['y'],norm(e['p']))
    if k not in best or e['war']>best[k]['war']: best[k]=e
top=sorted(best.values(),key=lambda e:-e['war'])[:25]
json.dump(top,open(D('drops.json'),'w'),separators=(',',':'))
for e in top[:12]: print(e['y'],e['w'],e['o'],e['p'],e['pos'],'->',e['to'],e['st'],'starts',e['pts'],'pts',e['war'],'WAR','for',e['add'])
