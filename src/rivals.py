# Builds ../data/rivals.json: every owner's biggest rival and every matchup between them, for the team pages (Kyle 2026-11-18).
# Matchups come from data/weeks/*.json (2018 on, finished weeks only): regular-season weeks, playoff rounds (a two-week
# round is one game, won on the two-week total; Kyle 2026-11-18) and the Sacko bracket (consolation games among non-playoff teams; the 3rd-place game
# between the semifinal losers is left out). 2016-17 playoff meetings come from the hand-set brackets (no scores saved).
# Rivalry score = regular-season and Sacko-bracket games + 1 per game decided by under 10 points
# + 6 per playoff meeting (a round, 9 for a final), times a balance factor (an even series counts more):
# 0.7 + 0.3 * (1 - |wins A - wins B| / decided games).
import json,os,glob,collections
here=os.path.dirname(os.path.abspath(__file__)); root=os.path.dirname(here)
PO=json.load(open(os.path.join(root,'data','playoffs.json')))
def po_teams(y):
    return {s['o'] for rd in PO.get(str(y),{}).get('rounds',[]) for m in rd for s in (m['a'],m['b']) if s.get('o')}
RD={}
G=[]  # y, w, k (reg/sacko/po/final), a, b, pa, pb, win, rd (playoff round id)
for f in sorted(glob.glob(os.path.join(root,'data','weeks','*.json'))):
    y=int(os.path.basename(f)[:4]);d=json.load(open(f));T=d['teams'];cur=d.get('cur')
    P=PO.get(str(y),{}).get('rounds',[]);pt=po_teams(y)
    for w,gs in d['weeks'].items():
        if cur and int(w)>=cur: continue
        for g in gs:
            a,b=g['a'],g['b']
            if a['p'] is None or b['p'] is None: continue
            oa,ob=T[str(a['t'])][0],T[str(b['t'])][0]
            if g['tier']=='': k='reg'
            elif g['tier']=='Playoffs':
                # the last round of the bracket is the final
                fin=P and any({m['a']['o'],m['b']['o']}=={oa,ob} for m in P[-1])
                k='final' if fin else 'po'
            else:
                if oa in pt and ob in pt: continue   # 3rd-place game, not the Sacko bracket
                k='sacko'
            if k=='reg':
                G.append(dict(y=y,w=int(w),k=k,a=oa,b=ob,pa=a['p'],pb=b['p'],rd=f"{y}-{g['mp']}",leg=''))
                continue
            # Kyle 2026-11-18: a two-week playoff or Sacko round is one game, decided by the two-week total
            key=(f"{y}-{g['mp']}",oa,ob);r=RD.get(key)
            if not r:
                r=RD[key]=dict(y=y,w=int(w),k=k,a=oa,b=ob,pa=0.0,pb=0.0,rd=key[0],leg='',wks=[]);G.append(r)
            r['pa']=round(r['pa']+a['p'],2);r['pb']=round(r['pb']+b['p'],2);r['wks'].append(int(w));r['w']=min(r['wks'])
            if len(r['wks'])>1: r['leg']=f"Weeks {min(r['wks'])}-{max(r['wks'])}"
# 2016 and 2017 brackets, same as BRACKET_MANUAL in template.html (Kyle); no scores except the 2016 final total
MAN={2016:[('charles','peanut','charles','po',None,None),('duane','squirm','duane','po',None,None),('duane','charles','duane','final',242,190)],
     2017:[('kyle','charles','kyle','po',None,None),('vicente','squirm',None,'po',None,None)]}
for y,L in MAN.items():
    for i,(a,b,win,k,pa,pb) in enumerate(L):
        G.append(dict(y=y,w=None,k=k,a=a,b=b,pa=pa,pb=pb,win=win,rd=f"{y}-m{i}",leg=''))
for x in G:
    if 'win' not in x: x['win']=x['a'] if x['pa']>x['pb'] else x['b'] if x['pb']>x['pa'] else None
pairs=collections.defaultdict(list)
for x in G: pairs[tuple(sorted((x['a'],x['b'])))].append(x)
def view(o,op,L):
    L=sorted(L,key=lambda x:(x['y'],x['w'] or 99))
    games=[];w=l=0;close=0;rounds={}
    for x in L:
        p,q=(x['pa'],x['pb']) if x['a']==o else (x['pb'],x['pa'])
        r=1 if x['win']==o else 0 if x['win']==op else None
        if r==1: w+=1
        elif r==0: l+=1
        if x['k'] in('reg','sacko') and p is not None and abs(p-q)<10: close+=1
        if x['k'] in('po','final'): rounds[x['rd']]=x['k']
        games.append([x['y'],x['w'],x['k'],p,q,r,x['leg']])
    n=len(L);dec=w+l;flat=sum(1 for x in L if x['k'] in('reg','sacko'))
    raw=flat+close+sum(9 if k=='final' else 6 for k in rounds.values())
    bal=0.7+0.3*(1-abs(w-l)/dec) if dec else 1
    return dict(o=op,score=round(raw*bal,2),w=w,l=l,n=n,po=len(rounds),fin=sum(k=='final' for k in rounds.values()),
                sk=sum(1 for x in L if x['k']=='sacko'),games=games)
out={}
for o in sorted({o for p in pairs for o in p}):
    R=[view(o,p[0] if p[1]==o else p[1],L) for p,L in pairs.items() if o in p]
    R.sort(key=lambda r:(-r['score'],-r['po'],-r['n']))
    out[o]=R[:3]
json.dump(out,open(os.path.join(root,'data','rivals.json'),'w'),separators=(',',':'))
for o,R in out.items():
    print(f"{o:8} "+" | ".join(f"{r['o']} {r['score']} {r['w']}-{r['l']} po{r['po']} sk{r['sk']}" for r in R))
print(os.path.getsize(os.path.join(root,'data','rivals.json')))
