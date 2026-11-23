# Pulls every team's ESPN logo for each season and writes ../data/logos.json:
#   {year: {owner: {"n": team name, "u": ESPN's logo link, "f": "img/logos/<file>" once a copy is saved}}}
# Usage: python3 logos.py [CACHE_DIR]. Needs ESPN_S2 for the private seasons. Run before build.py.
#        python3 logos.py --save   only saves copies of the links already in data/logos.json (no ESPN calls, no cookie),
#        for a machine that can reach the image hosts. Run build.py after it so the site uses the copies.
# A copy of each logo goes into ../img/logos (ESPN's vector logos as SVG, everything else cropped square to 192px WebP),
# so the site doesn't depend on links that can die. A logo that can't be downloaded keeps only its link: the site loads
# it from there and shows the owner's face if that fails. Copies saved by an earlier run are kept.
# 2016 and 2017 have no logos: those ESPN leagues were deleted. Kyle asked for logos by season on 2026-11-23.
import json,os,re,sys,ast,hashlib,subprocess,io
here=os.path.dirname(os.path.abspath(__file__)); root=os.path.dirname(here)
args=[a for a in sys.argv[1:] if not a.startswith('--')]; SAVE_ONLY='--save' in sys.argv[1:]
CACHE=args[0] if args else os.path.join(root,'.espn-cache'); os.makedirs(CACHE,exist_ok=True)
OUT=os.path.join(root,'img','logos'); os.makedirs(OUT,exist_ok=True)
LJ=os.path.join(root,'data','logos.json')
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

def host(u): return (re.match(r'https?://([^/:?#]+)',u,re.I) or [None,''])[1].lower()

def clean_svg(b):
    """ESPN's logo-pack SVGs, with anything that could run code taken out (the file is served from the site's own domain)."""
    b=re.sub(rb'<script\b.*?</script\s*>|<script\b[^>]*/>|<foreignObject\b.*?</foreignObject\s*>',b'',b,flags=re.S|re.I)
    b=re.sub(rb'\s+on[a-z]+\s*=\s*("[^"]*"|\'[^\']*\'|[^\s>]+)',b'',b,flags=re.I)
    return re.sub(rb'(href\s*=\s*["\'])\s*javascript:[^"\']*',rb'\1#',b,flags=re.I)

def save(u):
    """Save a copy of logo u into img/logos; returns its site path, or None if it can't be fetched."""
    h=hashlib.sha1(u.encode()).hexdigest()[:12]
    for ext in ('svg','webp'):
        if os.path.exists(os.path.join(OUT,f'{h}.{ext}')): return f'img/logos/{h}.{ext}'
    tmp=os.path.join(CACHE,'logo.tmp')
    r=subprocess.run(['curl','-fsSL','--max-time','30','--max-filesize','20000000','-A','Mozilla/5.0','-o',tmp,'-w','%{url_effective}\t%{content_type}',u],capture_output=True,text=True)
    if r.returncode or not os.path.exists(tmp):
        print('could not download',u,r.stderr.strip()[:200],file=sys.stderr); return None
    final,_,ctype=r.stdout.partition('\t');b=open(tmp,'rb').read();os.remove(tmp)
    if not b or 'removed.png' in final or ctype.startswith('text/html'):   # imgur's "removed" stand-in, or a web page instead of an image
        print('not an image any more',u,file=sys.stderr); return None
    if 'svg' in ctype or b.lstrip()[:5] in (b'<?xml',b'<svg ',b'<svg>') or u.lower().split('?')[0].endswith('.svg'):
        if not (host(u)=='espncdn.com' or host(u).endswith('.espncdn.com')): print('skipping an SVG from outside ESPN',u,file=sys.stderr); return None
        s=clean_svg(b)
        if b'<svg' not in s: return None
        open(os.path.join(OUT,f'{h}.svg'),'wb').write(s); return f'img/logos/{h}.svg'
    try:
        from PIL import Image,ImageOps
        im=Image.open(io.BytesIO(b)); im.seek(0); im=ImageOps.exif_transpose(im)   # first frame of a GIF; phone photos the right way up
        im=im.convert('RGBA' if im.mode in ('RGBA','LA','P','PA') else 'RGB')
        im=ImageOps.fit(im,(192,192),Image.LANCZOS)   # the site shows logos as squares (object-fit: cover), so crop the same way
        im.save(os.path.join(OUT,f'{h}.webp'),'WEBP',quality=84,method=6)
        return f'img/logos/{h}.webp'
    except Exception as e:
        print('could not read',u,e,file=sys.stderr); return None

if SAVE_ONLY: out=json.load(open(LJ))
else:
    out={}
    for y in sorted(LEAGUE):
        d=get(y)
        mem={m['id']:f"{m.get('firstName','')} {m.get('lastName','')}".strip() for m in d.get('members',[])}
        for t in d['teams']:
            o=MEMBER.get(mem.get((t.get('owners') or [''])[0]))
            if o is None: print('unmapped owner',y,t.get('owners'),file=sys.stderr); continue
            e={'n':tname(t)}
            u=(t.get('logo') or '').strip()
            if u.startswith('http://'): u='https://'+u[7:]   # the site is served over https
            if u and host(u) not in DEAD: e['u']=u
            out.setdefault(str(y),{})[o]=e
saved={};links=0;none=0
for y,v in out.items():
    for o,e in v.items():
        u=e.get('u')
        if not u: none+=1; continue
        if u not in saved: saved[u]=save(u)
        if saved[u]: e['f']=saved[u]
        else: e.pop('f',None); links+=1
json.dump(out,open(LJ,'w'),ensure_ascii=False,separators=(',',':'))
kept=sum(1 for v in saved.values() if v)
print(f'{sum(len(v) for v in out.values())} team-seasons: {kept} of {len(saved)} logos saved to img/logos, {links} team-seasons use ESPN\'s link, {none} have no logo')
