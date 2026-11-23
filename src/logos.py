# Pulls every team's ESPN logo for each season and writes ../data/logos.json:
#   {year: {owner: {"n": team name, "u": ESPN's logo link, "f": "img/logos/<file>" once a copy is saved}}}
# Usage: python3 logos.py [CACHE_DIR]. Needs ESPN_S2 for the private seasons. Run before build.py.
# It also tries to save a copy of each logo into ../img/logos (ESPN's vector logos as SVG, pictures shrunk to WebP), so
# the site doesn't depend on links that can die. A logo it can't download keeps only its link: the site loads it from
# there and shows the owner's face if that fails. Copies saved by an earlier run are kept.
# 2016 and 2017 have no logos: those ESPN leagues were deleted. Kyle asked for logos by season on 2026-11-23.
import json,os,re,sys,ast,hashlib,subprocess,io
here=os.path.dirname(os.path.abspath(__file__)); root=os.path.dirname(here)
CACHE=sys.argv[1] if len(sys.argv)>1 else os.path.join(root,'.espn-cache'); os.makedirs(CACHE,exist_ok=True)
OUT=os.path.join(root,'img','logos'); os.makedirs(OUT,exist_ok=True)
B='https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl'
LEAGUE={y:92604 for y in range(2018,2027)}; LEAGUE[2023]=604928347
MEMBER={'Charles Lorenzo':'charles','Jack Duffy':'fluff','Chris DiLapi':'dilapi','Sean Woram':'squirm','Tommy Curran':'quincy','Kyle Klugewicz':'kyle',
 'Andrew Woram':'peanut','Lucas Pace':'lucas','Sean Kelly':'skelly','Jordan Cruz':'jordan','Christian Rod':'rod','Jeremy Carroll':'jerry','Dylan Olivieri':'dylan','Adam Smith':'ghost','Mateus Toppin':'mateus'}
DEAD={'i66.tinypic.com'}   # TinyPic shut down in 2019 (Lucas's 2018 Staten Island Salvatores logo was hosted there)
# team name overrides live in build.py (RENAME); matched ignoring case and spacing, like moves.py does
src=open(os.path.join(here,'build.py')).read()
RENAME=ast.literal_eval(re.search(r'^RENAME=(\{.*\})$',src,re.M).group(1))
key=lambda n:' '.join((n or '').lower().replace('’',"'").split())
RN={key(k):v for k,v in RENAME.items()}
def tname(t):
    n=' '.join((t.get('name') or f"{t.get('location','')} {t.get('nickname','')}").split())
    return RN.get(key(n),n)

def get(y):   # same request and cache file as divisions.py
    f=os.path.join(CACHE,f'div_{y}.json')
    if not os.path.exists(f):
        cmd=['curl','-fsS','-o',f,f'{B}/seasons/{y}/segments/0/leagues/{LEAGUE[y]}?view=mSettings&view=mTeam']
        s2=os.environ.get('ESPN_S2','')
        if s2: cmd+=['-H',f'Cookie: espn_s2={s2}']
        subprocess.run(cmd,check=True)
    return json.load(open(f))

def save(u):
    """Save a copy of logo u into img/logos; returns its site path, or None if it can't be fetched."""
    h=hashlib.sha1(u.encode()).hexdigest()[:12]
    for ext in ('svg','webp'):
        if os.path.exists(os.path.join(OUT,f'{h}.{ext}')): return f'img/logos/{h}.{ext}'
    tmp=os.path.join(CACHE,'logo.tmp')
    r=subprocess.run(['curl','-fsSL','--max-time','30','-A','Mozilla/5.0','-o',tmp,'-w','%{url_effective}\t%{content_type}',u],capture_output=True,text=True)
    if r.returncode or not os.path.exists(tmp): return None
    final,_,ctype=r.stdout.partition('\t');b=open(tmp,'rb').read();os.remove(tmp)
    if not b or 'removed.png' in final or ctype.startswith('text/html'): return None   # imgur's "removed" stand-in, or a web page instead of an image
    if 'svg' in ctype or b.lstrip()[:5] in (b'<?xml',b'<svg ',b'<svg>') or u.lower().split('?')[0].endswith('.svg'):
        s=re.sub(rb'<script\b.*?</script>','',b,flags=re.S|re.I)
        if b'<svg' not in s: return None
        open(os.path.join(OUT,f'{h}.svg'),'wb').write(s); return f'img/logos/{h}.svg'
    try:
        from PIL import Image
        im=Image.open(io.BytesIO(b)); im.seek(0)
        im=im.convert('RGBA' if im.mode in ('RGBA','LA','P') else 'RGB')
        im.thumbnail((192,192),Image.LANCZOS)
        im.save(os.path.join(OUT,f'{h}.webp'),'WEBP',quality=84,method=6)
        return f'img/logos/{h}.webp'
    except Exception as e:
        print('could not read',u,e,file=sys.stderr); return None

out={};saved={};links=0;none=0
for y in sorted(LEAGUE):
    d=get(y)
    mem={m['id']:f"{m.get('firstName','')} {m.get('lastName','')}".strip() for m in d.get('members',[])}
    for t in d['teams']:
        o=MEMBER.get(mem.get((t.get('owners') or [''])[0]))
        if o is None: print('unmapped owner',y,t.get('owners'),file=sys.stderr); continue
        e={'n':tname(t)}
        u=(t.get('logo') or '').strip()
        if u.startswith('http://'): u='https://'+u[7:]   # the site is served over https
        if u and re.match(r'https://([^/]+)',u).group(1) not in DEAD:
            e['u']=u
            if u not in saved: saved[u]=save(u)
            if saved[u]: e['f']=saved[u]
            else: links+=1
        else: none+=1
        out.setdefault(str(y),{})[o]=e
json.dump(out,open(os.path.join(root,'data','logos.json'),'w'),ensure_ascii=False,separators=(',',':'))
kept=sum(1 for v in saved.values() if v)
print(f'{sum(len(v) for v in out.values())} team-seasons: {kept} of {len(saved)} logos saved to img/logos, {links} team-seasons use ESPN\'s link, {none} have no logo')
