# Saves a photo for every player in data/players.json and packs them into sprite sheets:
# ESPN's headshot for each player (by ESPN id) and the NFL team logo for each D/ST.
#  - img/nfl/h{sheet}-{hash}.webp: the player card photo, 12 per sheet (4 x 3 cells of 264 x 192, ESPN's 600 x 436 cutout)
#  - img/nfl/faces-{hash}.webp: every player's face in one sheet (44 px cells), for player chips and search results
#  - data/heads.json: the slot order and each name's slot, embedded in index.html by build.py as HEADS
# Sheets keep the site to a few dozen image files, which the Claude artifact preview needs (at most 511 files,
# and it blocks images from other sites, so photos must ship with the site).
# Slots are append-only: players already packed keep their place and new players go at the end, so a weekly
# refresh only rewrites the last card sheet and the faces sheet. --repack downloads every photo again and
# rebuilds all sheets (to pick up new ESPN photos of players already on file).
# Players ESPN has no photo for are listed under "none"; their card shows initials instead.
# Usage: python3 src/headshots.py CACHE_DIR [--repack]   (run after players.py, before build.py; needs a.espncdn.com)
import json,os,sys,io,hashlib,subprocess,concurrent.futures
from PIL import Image
here=os.path.dirname(os.path.abspath(__file__)); root=os.path.dirname(here)
D=lambda *p:os.path.join(root,*p)
args=[a for a in sys.argv[1:] if not a.startswith('--')]
CACHE=os.path.join(args[0] if args else D('.espn-cache'),'heads')
REPACK='--repack' in sys.argv
os.makedirs(CACHE,exist_ok=True);os.makedirs(D('img','nfl'),exist_ok=True)
W,H,COLS,ROWS=264,192,4,3          # card photo cell and sheet grid
PER=COLS*ROWS
FC,FCOLS=44,40                     # face cell (2x a 22 px chip face) and faces sheet width (in cells)
# ESPN pro team ids, as in players.py (a D/ST's player id is -(16000 + team id)); logo file names on ESPN's CDN
TEAM={1:'atl',2:'buf',3:'chi',4:'cin',5:'cle',6:'dal',7:'den',8:'det',9:'gb',10:'ten',11:'ind',12:'kc',13:'lv',14:'lar',15:'mia',16:'min',17:'ne',18:'no',
      19:'nyg',20:'nyj',21:'phi',22:'ari',23:'pit',24:'lac',25:'sf',26:'sea',27:'tb',28:'wsh',29:'car',30:'jax',33:'bal',34:'hou'}

PJ=json.load(open(D('data','players.json')));P=PJ['p']
def url(pid):
    i=int(pid)
    if i<0: return f'https://a.espncdn.com/i/teamlogos/nfl/500/{TEAM[-i-16000]}.png'
    return f'https://a.espncdn.com/i/headshots/nfl/players/full/{pid}.png'
def fetch(pid):
    f=os.path.join(CACHE,f'{pid}.png');miss=f+'.404'
    if REPACK:
        for x in (f,miss):
            if os.path.exists(x): os.remove(x)
    if os.path.exists(f): return pid,f
    if os.path.exists(miss): return pid,None
    r=subprocess.run(['curl','-sS','-o',f+'.part','-w','%{http_code}','--retry','3','--max-time','60',url(pid)],capture_output=True,text=True)
    code=r.stdout.strip()
    if code=='200':
        os.replace(f+'.part',f);return pid,f
    if os.path.exists(f+'.part'): os.remove(f+'.part')
    if code=='404': open(miss,'w').close();return pid,None
    raise SystemExit(f'{pid}: HTTP {code} {r.stderr.strip()}')

def strip_text(data):
    # some ESPN headshots carry text chunks with bad checksums that browsers skip and Pillow refuses: drop them
    out,i=[data[:8]],8
    while i<len(data):
        n=int.from_bytes(data[i:i+4],'big');t=data[i+4:i+8]
        if t not in (b'tEXt',b'iTXt',b'zTXt'): out.append(data[i:i+12+n])
        i+=12+n
    return b''.join(out)
def load(path):
    try: im=Image.open(path);im.load()
    except Exception: im=Image.open(io.BytesIO(strip_text(open(path,'rb').read())))
    return im.convert('RGBA')
def fit(im,w,h,pad):
    # a team logo, centered in a w x h cell
    im=im.copy();im.thumbnail((w-2*pad,h-2*pad),Image.LANCZOS)
    c=Image.new('RGBA',(w,h),(0,0,0,0));c.paste(im,((w-im.width)//2,(h-im.height)//2),im);return c
def card(im,pid):
    return fit(im,W,H,8) if int(pid)<0 else im.resize((W,H),Image.LANCZOS)
def face(im,pid):
    if int(pid)<0: return fit(im,FC,FC,2)
    # ESPN frames every cutout the same way, so the face sits at the same height (tall hair would throw off a crop from the top
    # of the cutout); center it across on the opaque pixels of the face and neck band
    band=im.getchannel('A').crop((0,120,im.width,260)).resize((im.width,1),Image.BOX)
    v=band.tobytes();cx=sum(x*w for x,w in enumerate(v))/max(1,sum(v))
    s=240;y=45;x=int(min(max(cx-s/2,0),im.width-s))
    return im.crop((x,y,x+s,y+s)).resize((FC,FC),Image.LANCZOS)
def save(img,name):
    b=io.BytesIO();img.save(b,'WEBP',quality=66 if name=='faces' else 74,alpha_quality=80 if name=='faces' else 85,method=6);data=b.getvalue()
    h=hashlib.sha1(data).hexdigest()[:8];open(D('img','nfl',f'{name}-{h}.webp'),'wb').write(data);return h

old=json.load(open(D('data','heads.json'))) if os.path.exists(D('data','heads.json')) and not REPACK else {}
# D/ST logos first, then players by name (the order of a first pack; later players are appended)
want=sorted(P,key=lambda i:(int(i)>=0,P[i]['n']))
with concurrent.futures.ThreadPoolExecutor(6) as ex: got=dict(ex.map(fetch,want))
have={i for i,f in got.items() if f}
ids=[i for i in old.get('ids',[]) if i in have];packed=set(ids)
ids+=[i for i in want if i in have and i not in packed]
none=sorted(i for i in want if i not in have)

keep=set();oldids=old.get('ids',[]);oldv=old.get('v',[]);v=[]
for n in range(0,(len(ids)+PER-1)//PER):
    grp=ids[n*PER:(n+1)*PER]
    if n<len(oldv) and oldids[n*PER:(n+1)*PER]==grp and os.path.exists(D('img','nfl',f'h{n}-{oldv[n]}.webp')):
        v.append(oldv[n]);keep.add(f'h{n}-{oldv[n]}.webp');continue      # unchanged sheet
    sh=Image.new('RGBA',(W*COLS,H*ROWS),(0,0,0,0))
    for k,pid in enumerate(grp): sh.alpha_composite(card(load(got[pid]),pid),((k%COLS)*W,(k//COLS)*H))
    v.append(save(sh,f'h{n}'));keep.add(f'h{n}-{v[-1]}.webp')
fv=old.get('faces',{}).get('v')
if not(oldids==ids and fv and os.path.exists(D('img','nfl',f'faces-{fv}.webp'))):
    rows=(len(ids)+FCOLS-1)//FCOLS;sh=Image.new('RGBA',(FC*FCOLS,FC*rows),(0,0,0,0))
    for k,pid in enumerate(ids): sh.alpha_composite(face(load(got[pid]),pid),((k%FCOLS)*FC,(k//FCOLS)*FC))
    fv=save(sh,'faces')
keep.add(f'faces-{fv}.webp')
for f in os.listdir(D('img','nfl')):
    if f.endswith('.webp') and f not in keep: os.remove(D('img','nfl',f))
slot={p:i for i,p in enumerate(ids)}
names={n:slot[str(p)] for n,p in sorted(PJ['names'].items()) if str(p) in slot}    # pnorm(name) -> slot, so pages can show a face before players.json loads
json.dump(dict(cell=[W,H],cols=COLS,rows=ROWS,v=v,faces=dict(cell=FC,cols=FCOLS,rows=(len(ids)+FCOLS-1)//FCOLS,v=fv),ids=ids,names=names,none=none),
          open(D('data','heads.json'),'w'),separators=(',',':'))
tot=sum(os.path.getsize(D('img','nfl',f)) for f in keep)
print(f'photos {len(ids)} ({sum(int(i)<0 for i in ids)} team logos), no photo {len(none)}, {len(v)} card sheets + faces, {tot/1e6:.1f} MB')
for i in none: print('  no photo:',i,P[i]['n'],P[i]['pos'])
