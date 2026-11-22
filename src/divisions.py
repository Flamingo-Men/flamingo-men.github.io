# Pulls each season's divisions from ESPN and writes ../data/divisions.json:
# {year: {"names": [division names], "o": {owner: index into names}}}. 2016 and 2017 had no saved divisions.
# Usage: python3 divisions.py [CACHE_DIR]. Needs ESPN_S2 for the private seasons. Run before build.py.
import json,os,sys,subprocess
here=os.path.dirname(os.path.abspath(__file__)); root=os.path.dirname(here)
CACHE=sys.argv[1] if len(sys.argv)>1 else os.path.join(root,'.espn-cache'); os.makedirs(CACHE,exist_ok=True)
B='https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl'
LEAGUE={y:92604 for y in range(2018,2027)}; LEAGUE[2023]=604928347
MEMBER={'Charles Lorenzo':'charles','Jack Duffy':'fluff','Chris DiLapi':'dilapi','Sean Woram':'squirm','Tommy Curran':'quincy','Kyle Klugewicz':'kyle',
 'Andrew Woram':'peanut','Lucas Pace':'lucas','Sean Kelly':'skelly','Jordan Cruz':'jordan','Christian Rod':'rod','Jeremy Carroll':'jerry','Dylan Olivieri':'dylan','Adam Smith':'ghost','Mateus Toppin':'mateus'}
def get(y):
    f=os.path.join(CACHE,f'div_{y}.json')
    if not os.path.exists(f):
        cmd=['curl','-fsS','-o',f,f'{B}/seasons/{y}/segments/0/leagues/{LEAGUE[y]}?view=mSettings&view=mTeam']
        s2=os.environ.get('ESPN_S2','')
        if s2: cmd+=['-H',f'Cookie: espn_s2={s2}']
        subprocess.run(cmd,check=True)
    return json.load(open(f))
def title(n):
    n=' '.join(n.split())
    return n.title() if n.isupper() else n
out={}
for y in sorted(LEAGUE):
    d=get(y)
    divs=sorted(d['settings']['scheduleSettings'].get('divisions',[]),key=lambda x:x['id'])
    if len(divs)<2: continue
    idx={x['id']:i for i,x in enumerate(divs)}
    mem={m['id']:f"{m.get('firstName','')} {m.get('lastName','')}".strip() for m in d.get('members',[])}
    o={}
    for t in d['teams']:
        own=MEMBER.get(mem.get((t.get('owners') or [''])[0]))
        if own is None: print('unmapped owner',y,t.get('owners'),file=sys.stderr); continue
        o[own]=idx[t.get('divisionId',0)]
    out[str(y)]={'names':[title(x['name']) for x in divs],'o':o}
json.dump(out,open(os.path.join(root,'data','divisions.json'),'w'),separators=(',',':'))
for y,v in out.items(): print(y,v['names'],{n:sorted(k for k,i in v['o'].items() if i==j) for j,n in enumerate(v['names'])})
