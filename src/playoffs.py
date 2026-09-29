# Builds ../data/playoffs.json: the winners bracket for every season.
# Usage: python3 playoffs.py CACHE_DIR   (reads full_{y}.json from moves.py, or sched_{y}.json for 2018, 2019 and 2025, which need ESPN_S2/ESPN_SWID)
import json,os,re,sys,subprocess
here=os.path.dirname(os.path.abspath(__file__)); root=os.path.dirname(here); CACHE=sys.argv[1]
B='https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl'
LEAGUE={2018:92604,2019:92604,2020:92604,2021:92604,2022:92604,2023:604928347,2024:92604,2025:92604,2026:92604}
MEMBER={'Charles Lorenzo':'charles','Jack Duffy':'fluff','Chris DiLapi':'dilapi','Sean Woram':'squirm','Tommy Curran':'quincy','Kyle Klugewicz':'kyle',
 'Andrew Woram':'peanut','Lucas Pace':'lucas','Sean Kelly':'skelly','Jordan Cruz':'jordan','Christian Rod':'rod','Jeremy Carroll':'jerry','Dylan Olivieri':'dylan','Adam Smith':'ghost','Mateus Toppin':'mateus'}
ns={};src=open(os.path.join(here,'build.py')).read();exec(src[src.index('RENAME='):src.index('\n',src.index('RENAME='))],ns)
RN={' '.join(k.lower().split()):v for k,v in ns['RENAME'].items()}
def load(y):
    for n in (f'sched_{y}.json',f'full_{y}.json'):
        f=os.path.join(CACHE,n)
        if os.path.exists(f):
            d=json.load(open(f))
            if 'schedule' in d: return d
    f=os.path.join(CACHE,f'sched_{y}.json')
    s2,sw=os.environ.get('ESPN_S2',''),os.environ.get('ESPN_SWID','')
    subprocess.run(['curl','-sS','-o',f,f'{B}/seasons/{y}/segments/0/leagues/{LEAGUE[y]}?view=mMatchupScore&view=mTeam&view=mSettings','-H',f'Cookie: espn_s2={s2}; SWID={sw}'],check=True)
    return json.load(open(f))
out={}
for y in LEAGUE:
    d=load(y)
    mem={m['id']:f"{m['firstName']} {m['lastName']}" for m in d['members']}
    T={}
    for t in d['teams']:
        nm=re.sub(r'\s+',' ',t.get('name') or (t.get('location','')+' '+t.get('nickname',''))).strip()
        T[t['id']]=dict(o=MEMBER.get(mem.get((t.get('owners') or [''])[0])),team=RN.get(' '.join(nm.lower().split()),nm),seed=t.get('playoffSeed'))
    g=[x for x in d['schedule'] if x.get('playoffTierType')=='WINNERS_BRACKET']
    per=sorted({x['matchupPeriodId'] for x in g})
    rounds=[]
    for p in per:
        r=[]
        for x in g:
            if x['matchupPeriodId']!=p: continue
            side=lambda k:dict(T[x[k]['teamId']],pts=x[k].get('totalPoints')) if k in x else None
            a,b=side('home'),side('away')
            if a and b and (b['seed'] or 99)<(a['seed'] or 99): a,b=b,a;w={'HOME':'b','AWAY':'a'}.get(x.get('winner'))
            else: w={'HOME':'a','AWAY':'b'}.get(x.get('winner'))
            r.append(dict(a=a,b=b,win=w))
        rounds.append(sorted(r,key=lambda m:m['a']['seed'] or 99))
    n=d['settings']['scheduleSettings'].get('playoffTeamCount')
    out[y]=dict(teams=n,rounds=rounds,byes=[v for v in T.values() if v['seed'] and v['seed']<=n and not any(v['o'] in (m['a']['o'],m['b']['o']) for m in (rounds[0] if rounds else []))] if rounds and len(rounds[0])*2<n else [])
    if not rounds: out[y]['seeds']=sorted([v for v in T.values() if v['seed'] and v['seed']<=n],key=lambda v:v['seed'])
json.dump(out,open(os.path.join(root,'data','playoffs.json'),'w'),separators=(',',':'))
for y,v in out.items(): print(y,[[f"{m['a']['o']} {m['a']['pts']} v {m['b']['o']} {m['b']['pts']} {m['win']}" for m in r] for r in v['rounds']])
