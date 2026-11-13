# Builds ../data/dashboard.json for the home page: this week's live scoreboard, last week's awards,
# season storylines, playoff odds after every completed week and the projected playoff bracket.
# Usage: python3 dashboard.py [CACHE_DIR]   (needs ESPN_S2 for the private 2026 league; run after build.py and rankings.py)
# Only two ESPN calls are always fresh (league + this week's box score), so it is cheap enough to run every few minutes on game days.
import json,os,re,sys,subprocess,collections,random,statistics as st,datetime
here=os.path.dirname(os.path.abspath(__file__)); root=os.path.dirname(here); D=lambda *p:os.path.join(root,*p)
CACHE=sys.argv[1] if len(sys.argv)>1 else os.path.join(root,'.espn-cache'); os.makedirs(CACHE,exist_ok=True)
Y=2026;B=f'https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl/seasons/{Y}/segments/0/leagues/92604'
MEMBER={'Charles Lorenzo':'charles','Jack Duffy':'fluff','Chris DiLapi':'dilapi','Sean Woram':'squirm','Tommy Curran':'quincy','Kyle Klugewicz':'kyle',
 'Andrew Woram':'peanut','Lucas Pace':'lucas','Sean Kelly':'skelly','Jordan Cruz':'jordan','Christian Rod':'rod','Jeremy Carroll':'jerry','Dylan Olivieri':'dylan','Adam Smith':'ghost','Mateus Toppin':'mateus'}
NICK={'fluff':'Floof','lucas':'Sal','dilapi':'Chris','rod':'RodFather','squirm':'Squirm','quincy':'Quincy','jerry':'Jerry','ghost':'Ghost','kyle':'Kyle','charles':'Charles','jordan':'Jordan','dylan':'Dylan'}
nk=lambda o:NICK.get(o,o.title())
POS={1:'QB',2:'RB',3:'WR',4:'TE',5:'K',16:'D/ST'}
SLOT={0:'QB',2:'RB',4:'WR',6:'TE',16:'D/ST',17:'K',23:'FLX',20:'BE',21:'IR'}
ORDER=['QB','RB','WR','TE','FLX','D/ST','K','BE','IR']
ns={};src=open(os.path.join(here,'build.py')).read();exec(src[src.index('RENAME='):src.index('\n',src.index('RENAME='))],ns)
RN={' '.join(k.lower().split()):v for k,v in ns['RENAME'].items()}

def get(path,name,fresh=False):
    f=os.path.join(CACHE,name)
    if fresh or not os.path.exists(f):
        cmd=['curl','-fsS','-o',f,B+path]
        s2,sw=os.environ.get('ESPN_S2',''),os.environ.get('ESPN_SWID','')
        if s2: cmd+=['-H','Cookie: '+'; '.join([f'espn_s2={s2}']+([f'SWID={sw}'] if sw else []))]
        subprocess.run(cmd,check=True)
    return json.load(open(f))

L=get('?view=mTeam&view=mSettings&view=mMatchupScore&view=mStatus&view=mRoster','dash_league.json',fresh=True)
mem={m['id']:f"{m['firstName']} {m['lastName']}" for m in L['members']}
T={}
for t in L['teams']:
    nm=re.sub(r'\s+',' ',t.get('name') or (t.get('location','')+' '+t.get('nickname',''))).strip()
    T[t['id']]=dict(o=MEMBER.get(mem.get((t.get('owners') or [''])[0])),team=RN.get(' '.join(nm.lower().split()),nm),div=t.get('divisionId',0),seed=t.get('playoffSeed'))
OW={k:v['o'] for k,v in T.items()};TEAM={v['o']:v['team'] for v in T.values()}
SS=L['settings']['scheduleSettings'];REG=SS.get('matchupPeriodCount',14);NPO=SS.get('playoffTeamCount',6)
DIVS={d['id']:d['name'] for d in SS.get('divisions',[])}
CUR=L['status']['currentMatchupPeriod'];SCHED=L['schedule']
def score(m,k):return m[k].get('totalPoints') if k in m else None
# a week counts as completed only once ESPN has moved on to the next matchup period (never an in-progress week)
done=sorted({m['matchupPeriodId'] for m in SCHED if m['matchupPeriodId']<CUR and m['matchupPeriodId']<=REG})
games={w:[(OW[m['home']['teamId']],OW[m['away']['teamId']],m['home']['totalPoints'],m['away']['totalPoints']) for m in SCHED if m['matchupPeriodId']==w and 'away' in m] for w in done}
future=lambda k:[(OW[m['home']['teamId']],OW[m['away']['teamId']]) for m in SCHED if k<m['matchupPeriodId']<=REG and 'away' in m]
OWN=list(TEAM)

def record(k):
    r={o:dict(w=0,l=0,pf=0.0,pa=0.0,s=[],res='') for o in OWN}
    for w in done:
        if w>k: break
        for a,b,pa,pb in games[w]:
            for me,op,pm,po in ((a,b,pa,pb),(b,a,pb,pa)):
                x=r[me];x['pf']+=pm;x['pa']+=po;x['s'].append(pm);win=pm>po;x['w' if win else 'l']+=1;x['res']+='W' if win else 'L'
    return r

# ---- roster strength for the latest odds (same model as rankings.py, so the two pages agree) ----
def val(p,inj):
    a=pr=None
    for x in p.get('stats',[]):
        if x.get('seasonId')==Y and x.get('scoringPeriodId')==0 and x.get('statSplitTypeId')==0:
            if x.get('statSourceId')==0 and x.get('appliedAverage') is not None and x.get('appliedTotal',0)>0: a=x['appliedAverage']
            if x.get('statSourceId')==1 and x.get('appliedAverage') is not None: pr=x['appliedAverage']
    v=(a+pr)/2 if a is not None and pr is not None else (pr if pr is not None else (a or 0))
    if inj in('INJURY_RESERVE','SUSPENSION'): v=0
    elif inj=='OUT': v*=.5
    return v
strength={}
for t in L['teams']:
    by=collections.defaultdict(list)
    for e in t.get('roster',{}).get('entries',[]):
        p=e['playerPoolEntry']['player'];pos=POS.get(p['defaultPositionId'])
        if pos: by[pos].append(val(p,p.get('injuryStatus') or e.get('injuryStatus')))
    for k in by: by[k].sort(reverse=True)
    pick=by['QB'][:1]+by['RB'][:2]+by['WR'][:2]+by['TE'][:1]+by['K'][:1]+by['D/ST'][:1]+sorted(by['RB'][2:]+by['WR'][2:]+by['TE'][1:],reverse=True)[:2]
    strength[OW[t['id']]]=sum(pick)

def sim(k,latest,N=20000):
    r=record(k);n={o:len(x['s']) for o,x in r.items()};avg={o:x['pf']/max(1,n[o]) for o,x in r.items()}
    lg=sum(x['pf'] for x in r.values())/max(1,sum(n.values()))
    if latest: mu={o:.6*strength[o]+.4*avg[o] for o in OWN}
    else: mu={o:(n[o]*avg[o]+3*lg)/(n[o]+3) for o in OWN}   # early weeks: points per game shrunk toward the league average
    res=[p-avg[o] for o,x in r.items() for p in x['s']];sd=(st.pstdev(res) if len(res)>2 else 25) or 25
    left=future(k);random.seed(Y);made=collections.Counter();bye=collections.Counter();div={T[i]['o']:T[i]['div'] for i in T}
    for _ in range(N):
        w={o:x['w'] for o,x in r.items()};pf={o:x['pf'] for o,x in r.items()}
        for h,a in left:
            ph=random.gauss(mu[h],sd);pa=random.gauss(mu[a],sd);pf[h]+=ph;pf[a]+=pa;w[h if ph>pa else a]+=1
        key=lambda o:(w[o],pf[o])
        dw=sorted([max((o for o in OWN if div[o]==d),key=key) for d in sorted(set(div.values()))],key=key,reverse=True)
        rest=sorted((o for o in OWN if o not in dw),key=key,reverse=True)[:NPO-len(dw)]
        for o in dw+rest: made[o]+=1
        for o in dw: bye[o]+=1
    return {o:round(100*made[o]/N,1) for o in OWN},{o:round(100*bye[o]/N,1) for o in OWN}

odds={};byes={}
for k in done:
    odds[k],byes[k]=sim(k,k==done[-1])
last=done[-1] if done else 0
# the Rankings tab ran the same latest-week sim; reuse its numbers when it covers this week so both pages match exactly
try:
    RC=json.load(open(D('data','rankings.json')))['current']
    if RC['weeks']==last: odds[last]={**odds[last],**{x['o']:x['odds'] for x in RC['rows']}}
except Exception: pass
R=record(last)

# ---- lineups for completed weeks (data/weeks/2026.json when it has the week, otherwise ESPN) ----
WK=json.load(open(D('data','weeks',f'{Y}.json'))) if os.path.exists(D('data','weeks',f'{Y}.json')) else {'weeks':{}}
def parse_box(d,w):
    out=[]
    for m in d['schedule']:
        if m['matchupPeriodId']!=w or 'away' not in m: continue
        sides=[]
        for k in ('home','away'):
            s=m[k];ro=[]
            for e in (s.get('rosterForCurrentScoringPeriod') or {}).get('entries',[]):
                p=e['playerPoolEntry']['player']
                act=[x for x in p.get('stats',[]) if x.get('scoringPeriodId')==w and x.get('statSourceId')==0]
                prj=[x for x in p.get('stats',[]) if x.get('scoringPeriodId')==w and x.get('statSourceId')==1]
                ro.append([p['fullName'],POS.get(p.get('defaultPositionId'),''),SLOT.get(e['lineupSlotId'],'FLX'),round(act[0]['appliedTotal'],2) if act else 0,round(prj[0]['appliedTotal'],1) if prj else 0])
            ro.sort(key=lambda r:ORDER.index(r[2]) if r[2] in ORDER else 9)
            sides.append(dict(t=s['teamId'],o=OW[s['teamId']],p=round(s.get('totalPointsLive') or s.get('totalPoints') or 0,2),proj=round(s.get('totalProjectedPointsLive') or 0,1),wp=s.get('winProbability'),r=ro))
        out.append(sides)
    return out
def lineups(w):
    if str(w) in WK['weeks']:
        return [[dict(o=WK['teams'][str(s['t'])][0],p=s['p'],r=s['r']) for s in (g['a'],g['b'])] for g in WK['weeks'][str(w)] if not g['tier']]
    return [[dict(o=s['o'],p=s['p'],r=[x[:4] for x in s['r']]) for s in g] for g in parse_box(get(f'?view=mBoxscore&view=mMatchupScore&scoringPeriodId={w}',f'box_{Y}_{w}.json'),w)]
LU={w:lineups(w) for w in done}

# ---- this week's scoreboard (live) ----
live=[]
if CUR<=17:
    for g in parse_box(get(f'?view=mBoxscore&view=mMatchupScore&scoringPeriodId={CUR}',f'dash_box_{CUR}.json',fresh=True),CUR):
        live.append([dict(o=s['o'],team=TEAM[s['o']],p=s['p'],proj=s['proj'],wp=s['wp'],r=[x for x in s['r'] if x[2]!='IR']) for s in g])
started=any(s['p'] for g in live for s in g)

# ---- weekly awards for the last completed week ----
FLEXOK={'RB','WR','TE'}
def optimal(ro):
    by=collections.defaultdict(list)
    for n,pos,sl,p in [x[:4] for x in ro]: by[pos].append(p)
    for k in by: by[k].sort(reverse=True)
    tot=sum(by['QB'][:1])+sum(by['RB'][:2])+sum(by['WR'][:2])+sum(by['TE'][:1])+sum(by['K'][:1])+sum(by['D/ST'][:1])
    return tot+sum(sorted(by['RB'][2:]+by['WR'][2:]+by['TE'][1:],reverse=True)[:2])
awards=[]
if last:
    G=LU[last];sides=[(s,o2) for a,b in G for s,o2 in ((a,b),(b,a))]
    f=lambda x:f"{x:.2f}".rstrip('0').rstrip('.')
    hi=max(sides,key=lambda x:x[0]['p']);lo=min(sides,key=lambda x:x[0]['p'])
    awards.append(dict(k='Top dog',o=hi[0]['o'],v=f(hi[0]['p']),t=f"Week high, beat {nk(hi[1]['o'])} by {f(hi[0]['p']-hi[1]['p'])}" if hi[0]['p']>hi[1]['p'] else f"Week high, and still lost to {nk(hi[1]['o'])}"))
    awards.append(dict(k='Basement',o=lo[0]['o'],v=f(lo[0]['p']),t="Lowest score of the week"+(f", somehow beat {nk(lo[1]['o'])}" if lo[0]['p']>lo[1]['p'] else "")))
    wins=[x for x in sides if x[0]['p']>x[1]['p']];loss=[x for x in sides if x[0]['p']<x[1]['p']]
    lk=min(wins,key=lambda x:x[0]['p']);hb=max(loss,key=lambda x:x[0]['p'])
    beat=lambda p:sum(1 for s,_ in sides if s['p']<p)
    awards.append(dict(k='Luckiest win',o=lk[0]['o'],v=f(lk[0]['p']),t=f"Won with a score that would have lost to {len(sides)-1-beat(lk[0]['p'])} of {len(sides)-1} teams"))
    awards.append(dict(k='Heartbreaker',o=hb[0]['o'],v=f(hb[0]['p']),t=f"Would have beaten {beat(hb[0]['p'])} of {len(sides)-1} teams, but lost to {nk(hb[1]['o'])}"))
    bl=max(G,key=lambda g:abs(g[0]['p']-g[1]['p']));w_,l_=sorted(bl,key=lambda s:-s['p'])
    awards.append(dict(k='Blowout',o=w_['o'],o2=l_['o'],v=f"+{f(w_['p']-l_['p'])}",t=f"{nk(w_['o'])} ran over {nk(l_['o'])}, {f(w_['p'])} to {f(l_['p'])}"))
    cl=min(G,key=lambda g:abs(g[0]['p']-g[1]['p']));w_,l_=sorted(cl,key=lambda s:-s['p'])
    awards.append(dict(k='Nail-biter',o=w_['o'],o2=l_['o'],v=f(w_['p']-l_['p']),t=f"{nk(w_['o'])} edged {nk(l_['o'])}, {f(w_['p'])} to {f(l_['p'])}"))
    mvp=max(((r,s) for s,_ in sides for r in s['r'] if r[2] not in('BE','IR')),key=lambda x:x[0][3])
    awards.append(dict(k='MVP',o=mvp[1]['o'],v=f(mvp[0][3]),t=f"{mvp[0][0]} ({mvp[0][1]}) went off for {nk(mvp[1]['o'])}",pl=mvp[0][0]))
    bb=[]
    for s,op in sides:
        gap=optimal(s['r'])-s['p']
        bb.append((s['p']<op['p'] and optimal(s['r'])>op['p'],gap,s,op))
    cost=[x for x in bb if x[0]]
    x=max(cost,key=lambda x:x[1]) if cost else max(bb,key=lambda x:x[1])
    bench=max((r for r in x[2]['r'] if r[2]=='BE'),key=lambda r:r[3],default=None)
    awards.append(dict(k='Bench blunder',o=x[2]['o'],v=f"{f(x[1])} left",t=(f"The best lineup would have beaten {nk(x[3]['o'])}" if x[0] else "Most points left on the bench")+(f". {bench[0]} sat with {f(bench[3])}" if bench else ""),pl=bench[0] if bench else None))

# ---- season storylines ----
CW={}  # career wins before this season, from the league stats baked into index.html
idx=open(D('index.html')).read();i=idx.index('const LEAGUE');LG=json.loads(idx[i:idx.index('\n',i)].split('=',1)[1].strip().rstrip(';'))
for o,v in LG['stats'].items():
    CW[o]=sum(r['w'] for y,r in v['seasons'].items() if not r.get('live') and int(y)<Y)
RK=json.load(open(D('data','rankings.json'))) if os.path.exists(D('data','rankings.json')) else {}
PLO=RK.get('playoffs',{})
stories=[]
def story(tag,os_,t,pri):stories.append(dict(tag=tag,o=os_,t=t,p=pri))
od=odds.get(last,{});left_w=REG-last
rec=lambda o:f"{R[o]['w']}-{R[o]['l']}"
if last:
    # best/worst starts through this many weeks since 2018 (regular season only)
    hist=[]
    for y in range(2018,Y):
        f_=D('data','weeks',f'{y}.json')
        if not os.path.exists(f_): continue
        W=json.load(open(f_));rr=collections.Counter();ll=collections.Counter()
        for w in sorted(W['weeks'],key=int)[:last]:
            for g in W['weeks'][w]:
                if g['tier']: continue
                for me,op in ((g['a'],g['b']),(g['b'],g['a'])):
                    o=W['teams'][str(me['t'])][0];(rr if (me['p'] or 0)>(op['p'] or 0) else ll)[o]+=1
        hist+=[(rr[o],y,o) for o in set(rr)|set(ll)]
    top=max(OWN,key=lambda o:(R[o]['w'],R[o]['pf']));hb=max(h[0] for h in hist) if hist else 0
    if R[top]['l']==0: story('Undefeated watch',[top],f"{nk(top)} is {rec(top)}. Nobody has ever gone undefeated in this league. Can he win out the last {left_w}?",100)
    else:
        who=[h for h in hist if h[0]==hb]
        same=', '.join(f"his own {y} start" if o==top else f"{nk(o)} in {y}" for _,y,o in who[:3])
        if R[top]['w']>=hb: story('Best start ever',[top],f"{nk(top)} is {rec(top)}, the best start through {last} weeks since the league moved to ESPN in 2018"+(f" (matching {same})" if R[top]['w']==hb else "")+". "+("Is this the year Floof finally gets ring number two?" if top=='fluff' else "Can anyone catch him?"),95)
        else: story('Top seed',[top],f"{nk(top)} leads the league at {rec(top)}.",60)
    bot=min(OWN,key=lambda o:(R[o]['w'],R[o]['pf']))
    if R[bot]['w']==0: story('Winless watch',[bot],f"{nk(bot)} is {rec(bot)}. Is the first winless season in league history on the table?",98)
    else: story('Sacko watch',[bot],f"{nk(bot)} sits in last at {rec(bot)}"+(f", with {od.get(bot,0):.0f}% playoff odds" if od else "")+". "+("Can Quincy dodge back-to-back Sackos?" if bot=='quincy' else "Can he climb out before the Sacko comes for him?"),70)
    # streaks of three or more
    for o in OWN:
        s=R[o]['res'];c=len(s)-len(s.rstrip(s[-1])) if s else 0
        if c>=4: story('Hot streak' if s[-1]=='W' else 'Cold streak',[o],f"{nk(o)} has {'won' if s[-1]=='W' else 'lost'} {c} straight. "+("Who stops him?" if s[-1]=='W' else "Does he snap it this week?"),55+c)
    # points: unlucky (top-4 points, outside the playoff spots) and the points leader
    pf=sorted(OWN,key=lambda o:-R[o]['pf'])
    lead=pf[0];story('Points leader',[lead],f"{nk(lead)} leads the league with {R[lead]['pf']:,.1f} points"+(f" but is only {rec(lead)}" if lead!=top else "")+".",50)
    pa=max(OWN,key=lambda o:R[o]['pa']);story('Bad luck',[pa],f"{nk(pa)} has had {R[pa]['pa']:,.1f} points scored against him, the most in the league. He's {rec(pa)}.",45)
    # playoff bubble and droughts
    bub=sorted([o for o in OWN if 15<=od.get(o,0)<=85],key=lambda o:-od[o])
    if bub: story('On the bubble',bub[:4],"Still sweating: "+", ".join(f"{nk(o)} {od[o]:.0f}%" for o in bub[:4])+f" to make the playoffs with {left_w} weeks left.",80)
    for o in OWN:
        p=PLO.get(o)
        if p and p['cur']>=2 and od.get(o,0)>=40: story('Drought',[o],f"{nk(o)} hasn't made the playoffs in {p['cur']} straight seasons. At {od[o]:.0f}%, is this the year it ends?",75+p['cur'])
        if p and p['last']==Y-1 and p['cur']==0 and od.get(o,100)<=25:
            run=0
            for y in range(Y-1,2015,-1):
                if y in p['years']: run+=1
                else: break
            if run>=3: story('Streak in danger',[o],f"{nk(o)} has made {run} straight playoffs. At {od[o]:.0f}%, that run is in trouble.",74)
    champ='kyle'
    if od.get(champ,0)>=50: story('Repeat?',[champ],f"Kyle is the defending champ at {rec(champ)} with {od[champ]:.0f}% odds. Nobody but Charles (2019, 2020) has ever gone back-to-back.",65)
    # all-time wins chase
    tot={o:CW.get(o,0)+R[o]['w'] for o in OWN}
    allt=sorted(((CW.get(o,0)+(R[o]['w'] if o in R else 0),o) for o in set(CW)|set(OWN)),reverse=True)
    for i_,(wv,o) in enumerate(allt):
        if o not in OWN: continue
        for wa,a in allt[:i_]:
            g=wa-wv
            if 0<=g<=3 and wa>wv-1:
                rank=1+sum(1 for x,_ in allt if x>wa)
                story('All-time wins',[o,a],f"{nk(o)} ({wv}) is {'tied with' if g==0 else f'{g} win'+('s' if g>1 else '')+' behind'} {nk(a)} ({wa}) for No. {rank} in all-time wins.",58-g+(5 if rank<=3 else 0))
                break
    for o in OWN:
        nxt=(tot[o]//25+1)*25
        if nxt-tot[o]<=2 and nxt>=50: story('Milestone',[o],f"{nk(o)} is {nxt-tot[o]} win{'s' if nxt-tot[o]>1 else ''} from {nxt} career wins.",52)
stories.sort(key=lambda s:-s['p'])
at=[s for s in stories if s['tag']=='All-time wins'];stories=[s for s in stories if s['tag']!='All-time wins' or s in at[:2]]
seen=collections.Counter();keep=[]
for s in stories:
    if seen[s['o'][0]]>=2: continue
    seen[s['o'][0]]+=1;keep.append(s)
stories=keep[:10]

# ---- trade tracker: lineup points each side's new players scored for them since the deal ----
trades=[]
for t in LG['trades']:
    if t['s']!=Y or t['st']!='completed' or not t['a']['o'] or not t['b']['o']: continue
    d=datetime.date.fromisoformat(t['d']);w0=max(1,(d-datetime.date(Y,9,10)).days//7+1)
    sides=[]
    for me,op in (('a','b'),('b','a')):
        o=t[me]['o'];got=[p.split('|')[0] for p in t[op]['gave'] if p.split('|')[1] not in('Pick','Secret')]
        if not got and not t[op]['gave']: got=[]
        pts=0.0;st_=0;per={}
        for w in done:
            if w<w0: continue
            for g in LU[w]:
                for s in g:
                    if s['o']!=o: continue
                    for r in s['r']:
                        if r[0] in got and r[2] not in('BE','IR'): pts+=r[3];st_+=1;per[r[0]]=per.get(r[0],0)+r[3]
        sides.append(dict(o=o,got=[p.split('|')[0] for p in t[op]['gave']],pts=round(pts,1),starts=st_,best=max(per,key=per.get) if per else None))
    if any(s['got'] for s in sides) and w0<=last: trades.append(dict(id=t['id'],d=t['d'],w=w0,sides=sides))
trades.sort(key=lambda x:x['d'],reverse=True)

# ---- projected bracket from current seeds (byes for 1 and 2; 3v6 and 4v5; no reseeding) ----
seeds=sorted([dict(o=v['o'],team=v['team'],seed=v['seed'],div=DIVS.get(v['div'],''),rec=rec(v['o']),pf=round(R[v['o']]['pf'],1),odds=od.get(v['o']),bye=byes.get(last,{}).get(v['o'])) for v in T.values()],key=lambda x:x['seed'] or 99)
po=[m for m in SCHED if m.get('playoffTierType')=='WINNERS_BRACKET']
actual={}
for m in po:
    actual.setdefault(m['matchupPeriodId'],[]).append(dict(a=dict(o=OW[m['home']['teamId']],pts=score(m,'home')),b=dict(o=OW[m['away']['teamId']],pts=score(m,'away')) if 'away' in m else None,win={'HOME':'a','AWAY':'b'}.get(m.get('winner'))))
# Sacko bracket (loser advances): ESPN's losers ladder games, once the playoffs start
sacko={}
for m in [m for m in SCHED if m.get('playoffTierType')=='LOSERS_CONSOLATION_LADDER']:
    sacko.setdefault(m['matchupPeriodId'],[]).append(dict(a=dict(o=OW[m['home']['teamId']],pts=score(m,'home')),b=dict(o=OW[m['away']['teamId']],pts=score(m,'away')) if 'away' in m else None,win={'HOME':'a','AWAY':'b'}.get(m.get('winner'))))
bracket=dict(seeds=seeds[:NPO],bubble=seeds[NPO:NPO+2],actual={str(k):v for k,v in sorted(actual.items())},sacko={str(k):v for k,v in sorted(sacko.items())},weeks=[REG+1,REG+2,REG+3])

out=dict(updated=datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),year=Y,week=CUR,last=last,reg=REG,started=started,
    live=live,awards=awards,stories=stories,trades=trades,
    odds=dict(weeks=done,series={o:[odds[k][o] for k in done] for o in OWN}),
    standings=[dict(o=o,team=TEAM[o],rec=rec(o),pf=round(R[o]['pf'],1),pa=round(R[o]['pa'],1),streak=(R[o]['res'][-1]+str(len(R[o]['res'])-len(R[o]['res'].rstrip(R[o]['res'][-1])))) if R[o]['res'] else '',odds=od.get(o),seed=next(v['seed'] for v in T.values() if v['o']==o)) for o in sorted(OWN,key=lambda o:next(v['seed'] for v in T.values() if v['o']==o))],
    bracket=bracket)
try:   # keep the old timestamp when nothing changed, so the game-day refresh job only commits real updates
    old=json.load(open(D('data','dashboard.json')))
    if {k:v for k,v in old.items() if k!='updated'}=={k:v for k,v in out.items() if k!='updated'}: out['updated']=old['updated']
except Exception: pass
json.dump(out,open(D('data','dashboard.json'),'w'),separators=(',',':'),ensure_ascii=False)
print('week',CUR,'last done',last,'started',started,'awards',len(awards),'stories',len(stories),'trades',len(trades))
for s in stories: print(' -',s['tag'],'|',s['t'])
for a in awards: print(' *',a['k'],a['o'],a['v'],a['t'])
print('odds',{o:out['odds']['series'][o] for o in OWN})
