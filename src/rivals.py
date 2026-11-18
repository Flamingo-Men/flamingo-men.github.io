# Builds ../data/rivals.json: every owner's biggest rival, for the boxing-match rivalry story on team pages (Kyle 2026-11-18).
# Bouts: regular-season games from data/weeks/*.json (2018 on, finished weeks only) plus playoff meetings
# (data/playoffs.json for 2018 on, two-week rounds counted as one bout on total points; 2016-17 from the hand-set brackets).
# Consolation games are left out, like the other all-time records.
# Rivalry score = regular-season games + 1 per game decided by under 10 points + 6 per playoff meeting (9 for a final),
# times a balance factor (an even series counts for more than a one-sided one): 0.7 + 0.3 * (1 - |wins A - wins B| / decided bouts).
import json,os,glob,collections
here=os.path.dirname(os.path.abspath(__file__)); root=os.path.dirname(here)
B=[]  # bouts: y, w (week or None), kind reg/semi/final, a, b, pa, pb (None if not saved), win (owner or None)
for f in sorted(glob.glob(os.path.join(root,'data','weeks','*.json'))):
    y=int(os.path.basename(f)[:4]);d=json.load(open(f));T=d['teams'];cur=d.get('cur')
    for w,gs in d['weeks'].items():
        if cur and int(w)>=cur: continue
        for g in gs:
            if g['tier']!='': continue
            a,b=g['a'],g['b']
            if a['p'] is None or b['p'] is None: continue
            oa,ob=T[str(a['t'])][0],T[str(b['t'])][0]
            B.append(dict(y=y,w=int(w),k='reg',a=oa,b=ob,pa=a['p'],pb=b['p'],ta=T[str(a['t'])][1],tb=T[str(b['t'])][1]))
PO=json.load(open(os.path.join(root,'data','playoffs.json')))
# 2016 and 2017 brackets, same as BRACKET_MANUAL in template.html (Kyle)
PO['2016']={'rounds':[[{'a':{'o':'charles'},'b':{'o':'peanut'},'win':'a'},{'a':{'o':'duane','team':'Emmustangs'},'b':{'o':'squirm'},'win':'a'}],
                      [{'a':{'o':'duane','team':'Emmustangs','pts':242},'b':{'o':'charles','pts':190},'win':'a'}]]}
PO['2017']={'rounds':[[{'a':{'o':'kyle','team':'NYC Klugeys'},'b':{'o':'charles'},'win':'a'},{'a':{'o':'vicente','team':'Quleefie Beefies'},'b':{'o':'squirm'},'win':None}],[]]}
for y,P in PO.items():
    R=[r for r in P.get('rounds',[]) if r];n=len(P.get('rounds',[]))
    for ri,rd in enumerate(P.get('rounds',[])):
        for m in rd:
            a,b=m['a'],m['b']
            if not a.get('o') or not b.get('o'): continue
            k='final' if ri==n-1 else ('semi' if ri==n-2 else 'qf')
            B.append(dict(y=int(y),w=None,k=k,a=a['o'],b=b['o'],pa=a.get('pts'),pb=b.get('pts'),ta=a.get('team'),tb=b.get('team'),
                          win=(m[m['win']]['o'] if m.get('win') else None)))
for x in B:
    if 'win' not in x: x['win']=x['a'] if x['pa']>x['pb'] else x['b'] if x['pb']>x['pa'] else None
    x['m']=round(abs(x['pa']-x['pb']),2) if x['pa'] is not None and x['pb'] is not None else None
pairs=collections.defaultdict(list)
for x in B: pairs[tuple(sorted((x['a'],x['b'])))].append(x)
order=lambda x:(x['y'],x['w'] if x['w'] is not None else 30)
def series(p,L):
    L=sorted(L,key=order);a,b=p
    reg=[x for x in L if x['k']=='reg'];po=[x for x in L if x['k']!='reg']
    wa=sum(x['win']==a for x in L);wb=sum(x['win']==b for x in L);dec=wa+wb
    close=sum(1 for x in reg if x['m'] is not None and x['m']<10)
    raw=len(reg)+close+sum(9 if x['k']=='final' else 6 for x in po)
    bal=0.7+0.3*(1-abs(wa-wb)/dec) if dec else 1
    return L,dict(score=round(raw*bal,2),wa=wa,wb=wb,n=len(L),reg=len(reg),po=len(po),close=close)
def view(o,op,L,s):
    me=lambda x:(x['pa'],x['pb']) if x['a']==o else (x['pb'],x['pa'])
    g=[]
    for x in L:
        p,q=me(x);g.append(dict(y=x['y'],w=x['w'],k=x['k'],p=p,q=q,win=1 if x['win']==o else 0 if x['win']==op else None,
                                team=x['ta'] if x['a']==o else x['tb'],vt=x['tb'] if x['a']==o else x['ta']))
    w,l=(s['wa'],s['wb']) if o<op else (s['wb'],s['wa'])
    sc=[x for x in g if x['p'] is not None]
    pf=round(sum(x['p'] for x in sc if x['k']=='reg'),2);pa=round(sum(x['q'] for x in sc if x['k']=='reg'),2)
    # longest win streak for each side within the series, and the current belt holder (winner of the last decided bout)
    def streak(v):
        best=cur=0;end=None
        for x in g:
            if x['win']==v: cur+=1
            elif x['win'] is not None: cur=0
            if cur>best: best=cur;end=x
        return best,end and [end['y'],end['w']]
    dec=[x for x in g if x['win'] is not None];belt=None
    if dec:
        h=dec[-1]['win'];k=0
        for x in reversed(dec):
            if x['win']==h: k+=1
            else: break
        belt=dict(o=o if h==1 else op,n=k,y=dec[-1]['y'],w=dec[-1]['w'],k=dec[-1]['k'],since=dict(y=dec[-k]['y'],w=dec[-k]['w'],k=dec[-k]['k']))
    return dict(o=op,score=s['score'],w=w,l=l,n=s['n'],reg=s['reg'],po=s['po'],close=s['close'],pf=pf,pa=pa,
                streak=streak(1)[0],ostreak=streak(0)[0],belt=belt,games=g)
owners=sorted({o for p in pairs for o in p})
out={}
for o in owners:
    R=[]
    for p,L in pairs.items():
        if o not in p: continue
        L,s=series(p,L);op=p[0] if p[1]==o else p[1]
        R.append(view(o,op,L,s))
    R.sort(key=lambda r:(-r['score'],-r['po'],-r['n']))
    top=R[0]
    out[o]=dict(top=top,next=[dict(o=r['o'],score=r['score'],w=r['w'],l=r['l'],po=r['po']) for r in R[1:3]],
                more={r['o']:r for r in R[1:3]})
json.dump(out,open(os.path.join(root,'data','rivals.json'),'w'),separators=(',',':'))
for o in owners:
    t=out[o]['top'];print(f"{o:8} -> {t['o']:8} score {t['score']:5} {t['w']}-{t['l']} po {t['po']} close {t['close']}  next: "+", ".join(f"{r['o']} {r['score']}" for r in out[o]['next']))
print(os.path.getsize(os.path.join(root,'data','rivals.json')))
