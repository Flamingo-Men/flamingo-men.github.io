# Pulls ESPN waiver, roster and box score history and writes ../data/moves.json.
# Usage: python3 moves.py CACHE_DIR   (raw ESPN responses are cached there; about 350 MB)
# 2018, 2019 and 2025 are private on ESPN: set ESPN_S2 and ESPN_SWID. 2016 and 2017 are reconstructed from data/drafts.json and the trade log.
import json,os,re,sys,subprocess,unicodedata,datetime,collections
here=os.path.dirname(os.path.abspath(__file__)); root=os.path.dirname(here)
CACHE=sys.argv[1] if len(sys.argv)>1 else os.path.join(root,'.espn-cache'); os.makedirs(CACHE,exist_ok=True)
B='https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl'
LEAGUE={2018:92604,2019:92604,2025:92604,2020:92604,2021:92604,2022:92604,2023:604928347,2024:92604,2026:92604}   # 2023 ran in its own ESPN league
ALL=list(range(2016,2027))
KICKOFF={2016:'2016-09-08',2017:'2017-09-07',2018:'2018-09-06',2019:'2019-09-05',2020:'2020-09-10',2021:'2021-09-09',2022:'2022-09-08',2023:'2023-09-07',2024:'2024-09-05',2025:'2025-09-04',2026:'2026-09-10'}
LASTWK=lambda y:16 if y<=2020 else 17         # fantasy championship week
MEMBER={'Charles Lorenzo':'charles','Jack Duffy':'fluff','Chris DiLapi':'dilapi','Sean Woram':'squirm','Tommy Curran':'quincy','Kyle Klugewicz':'kyle',
 'Andrew Woram':'peanut','Lucas Pace':'lucas','Sean Kelly':'skelly','Jordan Cruz':'jordan','Christian Rod':'rod','Jeremy Carroll':'jerry','Dylan Olivieri':'dylan','Adam Smith':'ghost','Mateus Toppin':'mateus'}
POS={1:'QB',2:'RB',3:'WR',4:'TE',5:'K',16:'D/ST'}
SLOT={0:'QB',2:'RB',4:'WR',6:'TE',16:'D/ST',17:'K',23:'FLX',20:'BE',21:'IR'}

def get(path,name,hdr=None):
    f=os.path.join(CACHE,name)
    if not os.path.exists(f):
        cmd=['curl','-sS','-o',f,B+path]+(['-H',hdr] if hdr else [])
        s2,sw=os.environ.get('ESPN_S2',''),os.environ.get('ESPN_SWID','')
        if s2.startswith('AE') and sw.startswith('{'): cmd+=['-H',f'Cookie: espn_s2={s2}; SWID={sw}']
        subprocess.run(cmd,check=True)
    return json.load(open(f))

# ---------- players: names, positions, PPR points (computed from raw stats) ----------
def ppr(s,rec):
    g=lambda k:s.get(str(k),0)
    return g(3)/25+4*g(4)-2*g(20)+g(24)/10+6*g(25)+g(42)/10+6*g(43)+rec*g(53)-2*g(72)+2*(g(19)+g(26)+g(44))+6*(g(63)+g(101)+g(102))
PL={}
def players(y):
    if y in PL: return PL[y]
    d=get(f'/seasons/{y}/players?scoringPeriodId=0&view=kona_player_info',f'pl_{y}.json','X-Fantasy-Filter: {"players":{"limit":10000}}')
    rec=0.5 if y>=2026 else 1
    out={}
    for p in d:
        pos=POS.get(p.get('defaultPositionId'))
        if not pos: continue
        tot=None;wk={}
        for s in p.get('stats',[]):
            if s['seasonId']!=y or s['statSourceId']!=0: continue
            if s['statSplitTypeId']==0 and s['scoringPeriodId']==0: tot=ppr(s['stats'],rec)
            elif s['statSplitTypeId']==1 and s['scoringPeriodId']>0: wk[s['scoringPeriodId']]=ppr(s['stats'],rec)
        if not p.get('fullName') or ' vs. ' in p['fullName']: continue
        out[p['id']]=dict(n=p['fullName'],pos=pos,tot=tot or 0.0,wk=wk)
    PL[y]=out;return out

def norm(n):
    n=unicodedata.normalize('NFKD',n).encode('ascii','ignore').decode().lower()
    n=re.sub(r"\b(jr|sr|ii|iii|iv|v)\b\.?","",n); n=re.sub(r"[^a-z ]","",n)
    return re.sub(r"\s+"," ",n).strip()
ALIAS={'cmc':'christian mccaffrey','amrs':'amonra st brown','jj':'justin jefferson','puka':'puka nacua','kenneth walker':'kenneth walker','dj moore':'dj moore',
 'odell beckham':'odell beckham','mitch trubisky':'mitchell trubisky','ben roethlisberger':'ben roethlisberger','steve smith':'steve smith sr',
 'marvin jones':'marvin jones','todd gurley':'todd gurley','will fuller':'will fuller','ted ginn':'ted ginn','duke johnson':'duke johnson',
 'melvin gordon':'melvin gordon','mark ingram':'mark ingram','gabe davis':'gabriel davis','hollywood brown':'marquise brown','josh palmer':'joshua palmer',
 'chig okonkwo':'chigoziem okonkwo','ken walker':'kenneth walker','bam knight':'zonovan knight','jeff wilson':'jeff wilson','darrell henderson':'darrell henderson',
 'robby anderson':'robbie chosen','robbie anderson':'robbie chosen','chris godwin':'chris godwin','deebo':'deebo samuel','mike williams':'mike williams',
 'kenneth gainwell':'kenny gainwell','brian robinson':'brian robinson','travis etienne':'travis etienne','michael pittman':'michael pittman','allen robinson':'allen robinson'}
def index(y):
    ix=collections.defaultdict(list)
    for pid,p in players(y).items():
        ix[norm(p['n'])].append(pid)
        if p['pos']=='D/ST': ix[norm(p['n'].replace(' D/ST',''))].append(pid)
    return ix
IX={}
def find(y,name,pos=None):
    if y not in IX: IX[y]=index(y)
    n=norm(name)
    c=IX[y].get(n) or IX[y].get(ALIAS.get(n,n),[])
    n=ALIAS.get(n,n) if not IX[y].get(n) else n
    if not c and pos in('D/ST','DST'):   # "Ravens" -> "Ravens D/ST"
        c=[i for k,v in IX[y].items() if k.endswith(n) for i in v if players(y)[i]['pos']=='D/ST']
    if not c:   # last name + first initial
        f,_,l=n.partition(' ')
        c=[i for k,v in IX[y].items() for i in v if k.split(' ')[-1]==l.split(' ')[-1] and k[:1]==f[:1]] if l else []
    if pos and len(c)>1:
        c=[i for i in c if players(y)[i]['pos']==pos.replace('DST','D/ST')] or c
    if len(c)>1: c.sort(key=lambda i:-players(y)[i]['tot'])
    return c[0] if c else None

# replacement level: weekly average of the QB12, RB30, WR30, TE12 that season
REPL={}
def repl(y,pos):
    if y not in REPL:
        by=collections.defaultdict(list)
        for p in players(y).values(): by[p['pos']].append(p['tot'])
        REPL[y]={k:sorted(by[k],reverse=True)[n-1]/17 for k,n in (('QB',12),('RB',30),('WR',30),('TE',12))}
    return REPL[y].get(pos,0)

# positional finish, QB/RB/WR/TE only
FIN={}
def finish(y,pid):
    if y not in FIN:
        by=collections.defaultdict(list)
        for i,p in players(y).items():
            if p['pos'] in('QB','RB','WR','TE'): by[p['pos']].append((p['tot'],i))
        FIN[y]={i:(pos,r+1) for pos,l in by.items() for r,(t,i) in enumerate(sorted(l,reverse=True))}
    return FIN[y].get(pid)

def week_of(y,d):
    k=datetime.date.fromisoformat(KICKOFF[y])-datetime.timedelta(days=2)
    return max(1,(datetime.date.fromisoformat(d)-k).days//7+1)

# ---------- ESPN seasons ----------
def espn(y):
    L=LEAGUE[y]
    full=get(f'/seasons/{y}/segments/0/leagues/{L}?view=mTeam&view=mRoster&view=mSettings&view=mDraftDetail&view=mStatus',f'full_{y}.json')
    mem={m['id']:f"{m['firstName']} {m['lastName']}" for m in full['members']}
    team={t['id']:dict(o=MEMBER.get(mem.get((t.get('owners') or [''])[0])),name=re.sub(r'\s+',' ',t.get('name') or (t.get('location','')+' '+t.get('nickname',''))).strip()) for t in full['teams']}
    P=players(y)
    last=min(LASTWK(y),full['status'].get('latestScoringPeriod',99))
    box=collections.defaultdict(dict)   # (teamId,week) -> {pid:(slot,pts)}
    for w in range(1,last+1):
        d=get(f'/seasons/{y}/segments/0/leagues/{L}?view=mBoxscore&view=mMatchupScore&scoringPeriodId={w}',f'box_{y}_{w}.json')
        for m in d['schedule']:
            if m['matchupPeriodId']!=w and not any(w in s.get('pointsByScoringPeriod',{}) for s in (m.get('home',{}),)): pass
            for side in ('home','away'):
                s=m.get(side)
                if not s or 'rosterForCurrentScoringPeriod' not in s: continue
                for e in s['rosterForCurrentScoringPeriod']['entries']:
                    pe=e['playerPoolEntry']
                    st=[x for x in pe['player'].get('stats',[]) if x.get('scoringPeriodId')==w and x.get('statSourceId')==0]
                    box[(s['teamId'],w)][e['playerId']]=(e['lineupSlotId'],round(st[0]['appliedTotal'],2) if st else 0.0,pe['player']['fullName'],POS.get(pe['player'].get('defaultPositionId'),''))
    started=lambda tid,pid,w0:round(sum(box[(tid,w)][pid][1] for w in range(w0,last+1) if pid in box.get((tid,w),{}) and box[(tid,w)][pid][0] not in(20,21)),2)
    name=lambda pid:(P.get(pid,{}).get('n') or next((v[2] for b in box.values() for k,v in b.items() if k==pid),str(pid)))
    pos=lambda pid:(P.get(pid,{}).get('pos') or next((v[3] for b in box.values() for k,v in b.items() if k==pid),''))
    # moves
    seen={};moves=[]
    for w in range(0,19):
        d=get(f'/seasons/{y}/segments/0/leagues/{L}?view=mTransactions2&scoringPeriodId={w}',f'tx_{y}_{w}.json')
        for t in d.get('transactions',[]):
            if t['id'] in seen or t.get('status')!='EXECUTED' or t['type'] not in('WAIVER','FREEAGENT'): continue
            seen[t['id']]=1
            adds=[i for i in t['items'] if i['type']=='ADD'];drops=[i for i in t['items'] if i['type']=='DROP']
            dt=datetime.datetime.utcfromtimestamp(t.get('processDate',t['proposedDate'])/1000)
            tid=t['teamId']; w0=max(1,t['scoringPeriodId'])
            if tid not in team: continue
            if dt.date()<datetime.date.fromisoformat(KICKOFF[y])-datetime.timedelta(days=2): w0=1
            for a in adds or [None]:
                mv=dict(y=y,d=dt.strftime('%Y-%m-%d'),w=w0,o=team[tid]['o'],team=team[tid]['name'],k='Waiver' if t['type']=='WAIVER' else 'Free agent')
                if a: mv.update(add=[name(a['playerId']),pos(a['playerId'])],pid=a['playerId'],pts=started(tid,a['playerId'],w0))
                if drops and (a is adds[0] if adds else True): mv['drop']=[name(drops[0]['playerId']),pos(drops[0]['playerId'])]
                moves.append(mv)
    moves.sort(key=lambda m:(m['d'],m.get('pid',0)))
    # a player counts once per team per season for pickup rankings (his first add)
    firsts=set()
    for m in moves:
        k=(m['o'],m.get('pid'))
        if 'pid' in m and k in firsts: m['again']=True
        firsts.add(k)
    # final rosters with how each player got there
    how={'DRAFT':'Drafted','ADD':'Pickup','TRADE':'Trade','FREEAGENT':'Pickup','WAIVER':'Pickup'}
    rosters={}
    for t in full['teams']:
        tid=t['id'];o=team[tid]['o']
        if not o: continue
        pl=[]
        for e in t['roster']['entries']:
            pid=e['playerId'];pts=round(sum(box[(tid,w)][pid][1] for w in range(1,last+1) if pid in box.get((tid,w),{}) and box[(tid,w)][pid][0] not in(20,21)),1)
            pl.append([SLOT.get(e['lineupSlotId'],'BE'),name(pid),pos(pid),how.get(e.get('acquisitionType'),''),pts,pid])
        order=['QB','RB','WR','TE','FLX','D/ST','K','BE','IR']
        pl.sort(key=lambda r:(order.index(r[0]) if r[0] in order else 9,-r[4]))
        rosters[o]=dict(team=team[tid]['name'],players=pl)
    # draft
    picks=[]
    for p in full.get('draftDetail',{}).get('picks',[]):
        if p['playerId']>0: picks.append(dict(pick=p['overallPickNumber'],pid=p['playerId'],n=name(p['playerId']),o=team[p['teamId']]['o']))
    return dict(team=team,rosters=rosters,moves=moves,picks=picks,box=box,started=started,last=last)

# ---------- reconstructed seasons ----------
DR=json.load(open(os.path.join(root,'data','drafts.json')))
def board_picks(y):
    D=DR.get(str(y))
    if not D: return []
    n=len(D['cols']);out=[]
    for c,col in enumerate(D['cols']):
        for r,v in enumerate(col):
            if not v: continue
            nm,_,ps=v.rpartition('/')
            spot=c+1 if r%2==0 else n-c        # snake
            out.append(dict(pick=r*n+spot,n=nm,pos=ps.replace('DST','D/ST'),o=D['teams'][c][1],pid=find(y,nm,ps)))
    return out

def main():
    league=json.load(open(os.path.join(root,'data','league.json')))
    # build.py adds the 2016/2017/2026 trades from emails; reuse its list so trade ids match the site
    ns={'league':league};src=open(os.path.join(here,'build.py')).read()
    exec(src[src.index('TEAM_OWNER='):src.index('flags={}')],ns)
    trades=league['trades']
    for tr in trades:
        for s in (tr['a'],tr['b']):
            if s['team'] in ns['TEAM_OWNER']: s['o']=ns['TEAM_OWNER'][s['team']]
    E={y:espn(y) for y in LEAGUE}
    out=dict(seasons={},rosters={},moves=[],trades={},drafts={})
    for y in ALL:
        out['seasons'][y]='espn' if y in E else 'rebuilt'
        out['drafts'][y]=[dict(pick=p['pick'],pid=p['pid'],n=p['n'],o=p['o']) for p in (E[y]['picks'] if y in E and E[y]['picks'] else board_picks(y))]
    # trade scores: points each side got from what it received, for the rest of that season
    wk=lambda tr:week_of(tr['s'],tr['d']) if tr['d'][5:7] not in('01','02','03','04','05','06','07','08') else 1
    done=sorted([t for t in trades if t['st']=='completed'],key=lambda t:(t['d'],t['id']))
    def until(tr,nm):   # a player flipped again only counts until his next trade
        for t in done:
            if t['s']==tr['s'] and (t['d'],t['id'])>(tr['d'],tr['id']) and any(g.partition('|')[0]==nm for s in('a','b') for g in t[s]['gave']): return wk(t)-1
        return LASTWK(tr['s'])
    for tr in trades:
        if tr['st']!='completed': continue
        y=tr['s'];w0=wk(tr)
        res={};ok=True
        for side,other in(('a','b'),('b','a')):
            got=tr[other]['gave'];tot=0;det=[]
            for g in got:
                nm,_,ps=g.partition('|')
                if ps in('Pick','Secret'): ok=False;continue
                pid=find(y,nm,ps)
                if pid is None: det.append([nm,ps,None]);continue
                P=players(y)[pid];end=until(tr,nm);wks=max(0,end-w0+1)
                if P['wk']: pts=sum(v for w,v in P['wk'].items() if w0<=w<=end)
                else: pts=P['tot']*wks/17       # 2016-2017: season total, prorated
                par=max(0,pts-repl(y,P['pos'])*wks)
                tot+=par;det.append([nm,ps,round(pts,1),round(par,1)])
            res[side]=dict(par=round(tot,1),got=det)
        if ok: out['trades'][tr['id']]=dict(w=w0,est=y<2018,**res)
    # moves + rosters
    for y,e in E.items():
        out['moves']+= [{k:v for k,v in m.items()} for m in e['moves']]
        out['rosters'][y]={o:dict(team=r['team'],src='espn',players=[p[:5]+[finish(y,p[5])] for p in r['players']]) for o,r in e['rosters'].items()}
    for y in ALL:
        if y in E: continue
        R=collections.defaultdict(dict)
        for p in board_picks(y):
            if p['o']: R[p['o']][norm(p['n'])]=['',p['n'],p['pos'],'Drafted',None,finish(y,p['pid']) if p['pid'] else None]
        for tr in sorted([t for t in trades if t['s']==y and t['st']=='completed'],key=lambda t:t['d']):
            for side,other in(('a','b'),('b','a')):
                for g in tr[side]['gave']:
                    nm,_,ps=g.partition('|')
                    if ps in('Pick','Secret'): continue
                    R[tr[side]['o']].pop(norm(nm),None)
                    if tr[other]['o']:
                        pid=find(y,nm,ps)
                        R[tr[other]['o']][norm(nm)]=['',nm,ps,'Trade',None,finish(y,pid) if pid else None]
        names={}
        for tr in trades:
            if tr['s']==y:
                for s in (tr['a'],tr['b']):
                    if s['o']: names[s['o']]=ns['RENAME'].get(s['team'],s['team'])
        D=DR.get(str(y))
        for c,(tn,o) in enumerate(D['teams'] if D else []):
            names.setdefault(o,tn)
        out['rosters'][y]={o:dict(team=names.get(o,''),src='rebuilt',players=list(v.values())) for o,v in R.items() if o}
    # roster snapshots for rebuilt seasons: champion/Sacko roster PDFs (template.html) and screenshots
    t=open(os.path.join(here,'template.html')).read()
    def jsobj(name):
        body=t[t.index('const '+name+' = ')+len('const '+name+' = '):]
        body=body[:body.index('\n};')+3].rstrip(';')
        body=re.sub(r'(?m)^(\s*)(\d{4}):',r'\1"\2":',body)
        body=re.sub(r'\b(roster|rosterNote|moves):',r'"\1":',body)
        return json.loads(re.sub(r',\s*}','}',body))
    CH={int(y):v for y,v in jsobj('CHAMP_DETAIL').items()};SK={int(y):v for y,v in jsobj('SACKO_DETAIL').items()}
    champs={2016:'duane',2017:'kyle',2018:'fluff',2019:'charles',2020:'charles',2021:'squirm',2022:'charles',2023:'kyle',2024:'dylan',2025:'kyle'}
    sackos={2016:'fluff',2017:'peanut',2018:'quincy',2019:'dilapi',2020:'dilapi',2021:'lucas',2022:'jordan',2023:'peanut',2024:'lucas',2025:'quincy'}
    SNAP=collections.defaultdict(dict)
    for y,v in CH.items(): SNAP[y][champs[y]]=(v['rosterNote'],v['roster'])
    for y,v in SK.items(): SNAP[y][sackos[y]]=(v['rosterNote'],v['roster'])
    SNAP[2016]['charles']=('Week 17 roster from a screenshot of Little Bills.',[['QB','Philip Rivers'],['RB',"Le'Veon Bell"],['RB','LeSean McCoy'],['WR','Antonio Brown'],['WR','Julio Jones'],['TE','Greg Olsen'],['FLX','Melvin Gordon'],['BE','A.J. Green'],['BE','Mike Evans'],['BE','Carlos Hyde'],['BE','Mark Ingram'],['BE','Jameis Winston'],['BE','Jordan Howard'],['BE','Michael Thomas'],['BE','Seahawks']])
    SNAP[2017]['charles']=('Week 3 roster from the Sensitive Lesbians box score.',[['QB','Marcus Mariota'],['RB','Ezekiel Elliott'],['RB','Kareem Hunt'],['WR','Demaryius Thomas'],['WR','Golden Tate'],['TE','Delanie Walker'],['FLX','Jay Ajayi'],['D/ST','Dolphins'],['K','Jake Elliott'],['BE','DeMarco Murray'],['BE','Joe Mixon'],['BE','Pierre Garcon'],['BE','Doug Martin'],['BE','Andrew Luck'],['BE','Javorius Allen'],['BE','T.Y. Hilton']])
    for y,snaps in SNAP.items():
        if y in E: continue
        for o,(note,ro) in snaps.items():
            pl=[]
            for slot,nm in ro:
                pos=slot if slot in('QB','RB','WR','TE','K','D/ST') else None
                pid=find(y,nm,pos) if pos!='D/ST' else find(y,nm,'D/ST')
                P=players(y).get(pid,{})
                pl.append([slot,nm,P.get('pos',pos or ''),'',None,finish(y,pid) if pid else None])
            r=out['rosters'][y].setdefault(o,dict(team='',src='rebuilt',players=[]))
            r['snap']=dict(note=note,players=pl)
    # top rosters: each player's positional finish plus where he went in our next draft
    def nextpick(y,nm):
        n=norm(nm)
        for p in out['drafts'].get(y+1,[]):
            if norm(p['n'])==n or (p['pid'] and players(y+1).get(p['pid'],{}).get('n') and norm(players(y+1)[p['pid']]['n'])==n): return p['pick']
        return None
    cands=[]
    for y,R in out['rosters'].items():
        if y>=2026: continue
        for o,r in R.items():
            pl=r['snap']['players'] if 'snap' in r else (r['players'] if r['src']=='espn' else None)
            if not pl: continue
            if 'snap' in r and y==2016 and o=='duane': pass
            rows=[];score=0
            for p in pl:
                slot,nm,pos,_,_,fin=p[:6]
                if pos in('K','D/ST') or slot in('K','D/ST'): continue
                fv=0
                if fin:
                    fp,rk=fin; fv=max(0,25-rk) if fp in('RB','WR') else max(0,13-rk)*2
                nx=nextpick(y,nm); dv=max(0,25-nx/4) if nx else 0
                rows.append([nm,fin[0]+str(fin[1]) if fin else pos,nx,round(fv+dv,1),fin[0] if fin else pos])
            rows.sort(key=lambda r:-r[3])
            # score the best possible lineup: QB, 2 RB, 2 WR, TE, FLEX
            need={'QB':1,'RB':2,'WR':2,'TE':1};flex=1
            for r_ in rows:
                p_=r_[4]
                if need.get(p_,0)>0: need[p_]-=1;r_.append(1);score+=r_[3]
                elif flex and p_ in('RB','WR','TE'): flex=0;r_.append(1);score+=r_[3]
                else: r_.append(0)
            rows=[r_[:4]+[r_[5]] for r_ in rows]
            cands.append(dict(y=y,o=o,team=r['team'],score=round(score,1),src='snap' if 'snap' in r else 'espn',note=r['snap']['note'] if 'snap' in r else 'Final ESPN roster',players=rows))
    cands.sort(key=lambda c:-c['score'])
    out['rosterRank']=cands
    # pickups: points the player scored in the lineup of the team that grabbed him
    # pickup score: lineup points, with RBs and WRs weighted above QBs (Kyle, 2026-09-29)
    WT={'RB':1.0,'WR':1.0,'TE':0.85,'QB':0.6,'K':0.4,'D/ST':0.4}
    mv=[m for m in out['moves'] if m.get('pts') and not m.get('again')]
    for m in mv: m['score']=round(m['pts']*WT.get(m['add'][1],0.5),1)
    out['topPickups']=sorted(mv,key=lambda m:-m['score'])[:5]
    out['pickupOfYear']={y:max((m for m in mv if m['y']==y),key=lambda m:m['score']) for y in LEAGUE if y<2026}
    # how each champion was built, and what sank each Sacko
    nteams=lambda y:len({p['o'] for p in out['drafts'][y]}) or 10
    def drafted(y,o):
        n=nteams(y);res=[]
        for p in out['drafts'][y]:
            if p['o']!=o or not p['pid']: continue
            f=finish(y,p['pid']);P=players(y).get(p['pid'],{})
            res.append(dict(n=P.get('n',p['n']),rd=(p['pick']-1)//n+1,fin=f))
        return res
    good=lambda f:f and f[1]<=(24 if f[0] in('RB','WR') else 12)
    def trades_of(y,o):
        res=[]
        for tr in trades:
            if tr['s']!=y or tr['st']!='completed' or str(tr['id']) not in out['trades'] and tr['id'] not in out['trades']: continue
            x=out['trades'].get(tr['id']) or out['trades'].get(str(tr['id']))
            for side,other in(('a','b'),('b','a')):
                if tr[side]['o']==o:
                    res.append(dict(id=tr['id'],got=[g.partition('|')[0] for g in tr[other]['gave']],gave=[g.partition('|')[0] for g in tr[side]['gave']],par=x[side]['par'],opp=x[other]['par']))
        return res
    out['champBuilt']={};out['sackoNotes']={}
    for y,o in champs.items():
        d=[p for p in drafted(y,o) if good(p['fin'])]
        fv=lambda p:(25-p['fin'][1]) if p['fin'][0] in('RB','WR') else (13-p['fin'][1])*2
        d.sort(key=lambda p:(-fv(p),p['rd']))
        gem=next((p for p in sorted(d,key=lambda p:-fv(p)) if p['rd']>=8 and p not in d[:2]),None)
        d=d[:2]+([gem] if gem else d[2:3])
        tr=sorted([t for t in trades_of(y,o) if t['par']>0],key=lambda t:-t['par'])[:3]
        pk=sorted([m for m in mv if m['y']==y and m['o']==o and m['add'][1] in('QB','RB','WR','TE')],key=lambda m:-m['pts'])[:3]
        out['champBuilt'][y]=dict(draft=d[:3],trades=tr,pickups=[dict(n=m['add'][0],pos=m['add'][1],w=m['w'],pts=m['pts']) for m in pk])
    for y,o in sackos.items():
        d=[p for p in drafted(y,o) if p['rd']<=5 and p['fin'] and not good(p['fin'])]
        d.sort(key=lambda p:p['rd'])
        tr=sorted([t for t in trades_of(y,o) if t['opp']-t['par']>=30],key=lambda t:t['par']-t['opp'])[:2]
        out['sackoNotes'][y]=dict(draft=d[:2],trades=tr)
    for m in out['moves']: m.pop('pid',None)
    # team name overrides from build.py (e.g. Pinky Sized Kyle -> The Yogurtlechefts), matched ignoring case and spacing
    RN={' '.join(k.lower().replace('’',"'").split()):v for k,v in ns['RENAME'].items()}
    fix=lambda n:RN.get(' '.join((n or '').lower().replace('’',"'").split()),n)
    for m in out['moves']: m['team']=fix(m['team'])
    for R in out['rosters'].values():
        for r in R.values(): r['team']=fix(r['team'])
    for c in out['rosterRank']: c['team']=fix(c['team'])
    out['rosterRank']=out['rosterRank'][:25]
    for m in out['topPickups']+list(out['pickupOfYear'].values()): m['team']=fix(m['team'])
    del out['drafts']
    json.dump(out,open(os.path.join(root,'data','moves.json'),'w'),ensure_ascii=False,separators=(',',':'))
    print('moves',len(out['moves']),'trades scored',len(out['trades']),{y:len(r) for y,r in out['rosters'].items()})
if __name__=='__main__': main()
