# Pulls every team's ESPN logo for each season and writes ../data/logos.json:
#   {year: {owner: {"n": team name, "u": ESPN's logo link, "f": "img/logos/<file>" once a copy is saved,
#                   "x": "gone" (deleted from its host) or "login" (uploaded straight to ESPN, which wants a login) when it can't be shown}}}
# Usage: python3 logos.py [CACHE_DIR]. Needs ESPN_S2 for the private seasons. Run before build.py.
#        python3 logos.py --save   only saves copies of the links already in data/logos.json (no ESPN calls, no cookie),
#        for a machine that can reach the image hosts. Run build.py after it so the site uses the copies.
# A copy of each logo goes into ../img/logos (ESPN's vector logos as SVG, everything else cropped square to 192px WebP),
# so the site doesn't depend on links that can die. A logo that couldn't be downloaded for some other reason keeps only its
# link: the site loads it from there and shows the owner's face if that fails. Copies saved by an earlier run are kept.
# 2016 and 2017 ESPN leagues were deleted: only the hand-added logos in HAND. Kyle sent his lost 2018-2022 imgur logos on
# 2026-11-24; they're saved in img/logos under the old links' file names. Kyle asked for logos by season on 2026-11-23.
import json,os,re,sys,ast,hashlib,subprocess,io,urllib.parse
here=os.path.dirname(os.path.abspath(__file__)); root=os.path.dirname(here)
args=[a for a in sys.argv[1:] if not a.startswith('--')]; SAVE_ONLY='--save' in sys.argv[1:]
CACHE=args[0] if args else os.path.join(root,'.espn-cache'); os.makedirs(CACHE,exist_ok=True)
OUT=os.path.join(root,'img','logos'); os.makedirs(OUT,exist_ok=True)
LJ=os.path.join(root,'data','logos.json')
B='https://lm-api-reads.fantasy.espn.com/apis/v3/games/ffl'
LEAGUE={y:92604 for y in range(2018,2027)}; LEAGUE[2023]=604928347
MEMBER={'Charles Lorenzo':'charles','Jack Duffy':'fluff','Chris DiLapi':'dilapi','Sean Woram':'squirm','Tommy Curran':'quincy','Kyle Klugewicz':'kyle',
 'Andrew Woram':'peanut','Lucas Pace':'lucas','Sean Kelly':'skelly','Jordan Cruz':'jordan','Christian Rod':'rod','Jeremy Carroll':'jerry','Dylan Olivieri':'dylan','Adam Smith':'ghost','Mateus Toppin':'mateus'}
# logos (and names) owners sent in by hand for seasons ESPN can't give us; n2 = a second team name shown under the main one.
# Kyle, 2026-11-24: his 2017 hawk and Fluff's 2017 red backpack (2016-2017 ESPN leagues are deleted)
HAND={'2017':{'kyle':{'n':'NYC Klugeys','n2':'N Town Dolphins','f':'img/logos/hand-kyle-2017.webp'},
              'fluff':{'n':'Duane Bernard Jr','f':'img/logos/hand-fluff-2017.webp'}}}
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

UA='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36'
def fetch(u):
    """(HTTP code, final link, content type, bytes, curl's error); a dropped connection is tried once more."""
    tmp=os.path.join(CACHE,'logo.tmp')
    for attempt in (1,2):
        if os.path.exists(tmp): os.remove(tmp)
        r=subprocess.run(['curl','-sSL','--max-time','40','--max-filesize','20000000','-A',UA,'-H','Accept: image/avif,image/webp,image/apng,image/svg+xml,image/*,*/*;q=0.8',
                          '-o',tmp,'-w','%{http_code}\t%{url_effective}\t%{content_type}',u],capture_output=True,text=True)
        code,final,ctype=(r.stdout.split('\t')+['',''])[:3]
        if r.returncode==0 or code not in ('','000'): break   # an HTTP answer
    b=open(tmp,'rb').read() if os.path.exists(tmp) else b''
    if os.path.exists(tmp): os.remove(tmp)
    return code,final,ctype.lower(),b,(r.stderr.strip()[:160] if r.returncode else '')

def wayback(u):
    """The Wayback Machine's copy of a deleted image (its raw bytes, via the id_ form), or None."""
    code,_,_,b,_=fetch('https://archive.org/wayback/available?url='+urllib.parse.quote(u.split('://',1)[1],safe=''))
    try: s=json.loads(b)['archived_snapshots']['closest']
    except Exception: return None
    if not s or not s.get('available') or str(s.get('status'))!='200': return None
    return f"https://web.archive.org/web/{s['timestamp']}id_/{u}"

def keep(u,h,b,ctype):
    """Write image bytes b for link u as img/logos/<h>.svg or .webp; returns the site path or None."""
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

def save(u):
    """Save a copy of logo u into img/logos. Returns (site path, None), or (None, why): 'gone' when the image was deleted
    (404/410, imgur's "removed" stand-in, a web page instead of an image) and the Wayback Machine has no copy either,
    'login' when the host wants an ESPN login (pictures uploaded straight to ESPN: visitors can't load those either),
    'retry' for anything that may work next time. A copy put in img/logos by hand as <first 12 hex of sha1(link)>.webp
    (or .svg) is used as is: that's how the pictures uploaded to ESPN were saved, from Kyle's signed-in Chrome (2026-11-23)."""
    h=hashlib.sha1(u.encode()).hexdigest()[:12]
    for ext in ('svg','webp'):
        if os.path.exists(os.path.join(OUT,f'{h}.{ext}')): return f'img/logos/{h}.{ext}',None
    code,final,ctype,b,err=fetch(u)
    if code in ('401','403'): print('needs a login',u,file=sys.stderr); return None,'login'
    if code in ('404','410') or 'removed.png' in final or (code=='200' and ctype.startswith('text/html')):
        w=wayback(u)
        if w:
            code2,_,ctype2,b2,_=fetch(w)
            if code2=='200' and b2 and not ctype2.startswith('text/html'):
                f=keep(u,h,b2,ctype2)
                if f: print('saved from the Wayback Machine',u,file=sys.stderr); return f,None
        print('gone',code,u,file=sys.stderr); return None,'gone'
    if err or code!='200' or not b: print('could not download',code,u,err,file=sys.stderr); return None,'retry'
    f=keep(u,h,b,ctype)
    return (f,None) if f else (None,'retry')

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
for y,v in HAND.items():
    for o,e in v.items(): out.setdefault(y,{})[o]=dict(e)
# f = saved copy; x = the link can't be shown ('gone' or 'login'), so the site uses the owner's face (initials on the logo wall)
saved={};cnt={'f':0,'gone':0,'login':0,'retry':0,'none':0}
for y,v in out.items():
    for o,e in v.items():
        u=e.get('u')
        if not u: cnt['f' if e.get('f') else 'none']+=1; continue
        if u not in saved: saved[u]=save(u)
        f,why=saved[u]; e.pop('f',None); e.pop('x',None)
        if f: e['f']=f; cnt['f']+=1
        else:
            cnt[why]+=1
            if why!='retry': e['x']=why
json.dump(out,open(LJ,'w'),ensure_ascii=False,separators=(',',':'))
kept=sum(1 for f,_ in saved.values() if f)
print(f"{sum(len(v) for v in out.values())} team-seasons, {len(saved)} distinct logos ({kept} saved in img/logos). Team-seasons: {cnt['f']} saved, "
      f"{cnt['gone']} deleted from their host, {cnt['login']} need an ESPN login, {cnt['retry']} left on the link to try again, {cnt['none']} with no logo")
