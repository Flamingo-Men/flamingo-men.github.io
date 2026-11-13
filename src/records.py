# Builds ../data/records.json: single-week and streak records from data/weeks/*.json (ESPN, 2018 on).
import json,os,glob
here=os.path.dirname(os.path.abspath(__file__)); root=os.path.dirname(here)
G=[];P=[];res={}
for f in sorted(glob.glob(os.path.join(root,'data','weeks','*.json'))):
    y=int(os.path.basename(f)[:4]);d=json.load(open(f));T=d['teams']
    cur=d.get('cur')
    for w,gs in sorted(d['weeks'].items(),key=lambda x:int(x[0])):
        if cur and int(w)>=cur: continue  # skip the week in progress (and later)
        for g in gs:
            if g['tier'] not in ('','Playoffs'): continue
            a,b=g['a'],g['b']
            if a['p'] is None or b['p'] is None: continue
            A,B=T[str(a['t'])],T[str(b['t'])]
            G.append(dict(y=y,w=int(w),reg=g['tier']=='',a=dict(o=A[0],team=A[1],p=a['p']),b=dict(o=B[0],team=B[1],p=b['p'])))
            for s,S,O in ((a,A,B),(b,B,A)):
                for r in s['r']:
                    if r[2] not in('BE','IR'): P.append(dict(y=y,w=int(w),o=S[0],team=S[1],vs=O[0],n=r[0],pos=r[1],p=r[3]))
                P.append(dict(y=y,w=int(w),o=S[0],team=S[1],vs=O[0],n=None,bench=round(sum(r[3] for r in s['r'] if r[2]=='BE'),2)))
tm=[]
for g in G:
    for me,op in (('a','b'),('b','a')): tm.append(dict(y=g['y'],w=g['w'],o=g[me]['o'],team=g[me]['team'],p=g[me]['p'],vs=g[op]['o'],vsp=g[op]['p'],reg=g['reg']))
out={}
out['weekHigh']=max(tm,key=lambda x:x['p'])
out['weekLow']=min([x for x in tm if x['reg'] and x['p']>0],key=lambda x:x['p'])
reg=[g for g in G if g['reg']]
bl=max(reg,key=lambda g:abs(g['a']['p']-g['b']['p']));W,L=(bl['a'],bl['b']) if bl['a']['p']>bl['b']['p'] else (bl['b'],bl['a'])
out['blowout']=dict(y=bl['y'],w=bl['w'],o=W['o'],team=W['team'],p=W['p'],vs=L['o'],vsp=L['p'],m=round(W['p']-L['p'],2))
cl=min([g for g in reg if g['a']['p']!=g['b']['p']],key=lambda g:abs(g['a']['p']-g['b']['p']));W,L=(cl['a'],cl['b']) if cl['a']['p']>cl['b']['p'] else (cl['b'],cl['a'])
out['closest']=dict(y=cl['y'],w=cl['w'],o=W['o'],team=W['team'],p=W['p'],vs=L['o'],vsp=L['p'],m=round(W['p']-L['p'],2))
out['player']=max([x for x in P if x['n']],key=lambda x:x['p'])
out['bench']=max([x for x in P if not x['n']],key=lambda x:x['bench'])
lossHigh=max([x for x in tm if x['reg'] and x['p']<x['vsp']],key=lambda x:x['p']);out['unluckiest']=lossHigh
# streaks over regular-season games in order
seq={}
for x in sorted([x for x in tm if x['reg']],key=lambda x:(x['y'],x['w'])):
    seq.setdefault(x['o'],[]).append((x['y'],x['w'],x['p']>x['vsp']))
def streak(win):
    best=None
    for o,s in seq.items():
        run=0;start=None
        for y,w,r in s:
            if r==win: run+=1;start=start if run>1 else (y,w)
            else: run=0
            if run and (not best or run>best['n']): best=dict(o=o,n=run,start=start,end=(y,w))
    return best
out['winStreak']=streak(True);out['loseStreak']=streak(False)
# luck (Kyle made it an official stat, 2026-11-13): actual regular-season wins minus expected wins, where a week's
# expected wins is the share of the other teams you outscored that week (your record if you'd played everyone)
import collections
wk=collections.defaultdict(list)
for x in tm:
    if x['reg']: wk[(x['y'],x['w'])].append(x)
L=collections.defaultdict(lambda:[0.0,0.0,0])   # (o,y) -> [wins, expected, games]
for (y,w),xs in wk.items():
    for x in xs:
        others=[z['p'] for z in xs if z is not x]
        e=(sum(x['p']>q for q in others)+.5*sum(x['p']==q for q in others))/len(others)
        r=L[(x['o'],y)];r[0]+=1 if x['p']>x['vsp'] else .5 if x['p']==x['vsp'] else 0;r[1]+=e;r[2]+=1
out['luck']={}
for (o,y),(wn,e,g) in L.items(): out['luck'].setdefault(o,{})[str(y)]=dict(luck=round(wn-e,2),exp=round(e,2),w=wn,g=g)
json.dump(out,open(os.path.join(root,'data','records.json'),'w'),separators=(',',':'))
for k,v in out.items(): print(k,v)
