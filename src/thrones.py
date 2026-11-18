# Builds ../data/thrones.json: the facts behind the Game of Thrones title stories (Champions plaques) and the
# walk-of-shame Sacko stories (Sacko toilets), Kyle 2026-11-18. One entry per finished season from 2018 on,
# with a block for that year's champion (c) and Sacko loser (s):
#   reg  [[week, opponent, points for, points against]] regular season
#   rk   standing after each regular-season week (wins, then points), so a story can find the low point
#   post [[kind, opponent, points for, points against, [[week, for, against], ...]]] playoff or Sacko-bracket rounds,
#        kind 'po' (playoff round), 'final' (title game) or 'cons' (Sacko bracket). A two-week round is one game.
#   top  [[player, pos, lineup points, starts]] the team's top scorers, regular season and postseason
#   star [player, pos, points, week] the best single game by one of its starters in its postseason
#   zero [player, pos, points, week] its lowest-scoring starter (no K or D/ST) in its last postseason round
#   seed playoff seed (champions)
# Run after weeks.py and playoffs.py, before build.py (which embeds the file as /*THRONES*/).
import json,os,re,glob,collections
here=os.path.dirname(os.path.abspath(__file__)); root=os.path.dirname(here)
tpl=open(os.path.join(here,'template.html'),encoding='utf-8').read()
def owners(name):
    line=tpl[tpl.index(f'const {name} = {{'):]; line=line[:line.index('\n')]
    return {int(y):o for y,o in re.findall(r'(\d{4}):\{o:"(\w+)"',line)}
CH,SK=owners('CHAMPS'),owners('SACKOS')
PO=json.load(open(os.path.join(root,'data','playoffs.json')))
out={}
for f in sorted(glob.glob(os.path.join(root,'data','weeks','*.json'))):
    y=int(os.path.basename(f)[:4])
    if y not in CH or y not in SK: continue
    d=json.load(open(f));T=d['teams'];W=d['weeks']
    own=lambda s:T[str(s['t'])][0]
    # standings after each regular-season week, for every team
    rec=collections.defaultdict(lambda:[0,0.0]);rk=collections.defaultdict(list)
    for w in sorted(W,key=int):
        gs=[g for g in W[w] if g['tier']=='']
        if not gs: continue
        for g in gs:
            a,b=g['a'],g['b']
            if a['p'] is None or b['p'] is None: continue
            rec[own(a)][1]+=a['p'];rec[own(b)][1]+=b['p']
            if a['p']>b['p']: rec[own(a)][0]+=1
            elif b['p']>a['p']: rec[own(b)][0]+=1
        order=sorted(rec,key=lambda o:(-rec[o][0],-rec[o][1]))
        for i,o in enumerate(order): rk[o].append(i+1)
    seeds={s['o']:s.get('seed') for rd in PO.get(str(y),{}).get('rounds',[]) for m in rd for s in (m['a'],m['b']) if s.get('o')}
    last=PO.get(str(y),{}).get('rounds',[[]])[-1]
    finals={frozenset((m['a']['o'],m['b']['o'])) for m in last}
    def block(o):
        reg=[];post={};top=collections.Counter();st=collections.Counter();star=None;rounds=[]
        for w in sorted(W,key=int):
            for g in W[w]:
                for me,op in (('a','b'),('b','a')):
                    if own(g[me])!=o: continue
                    p,q=g[me]['p'],g[op]['p'];oo=own(g[op])
                    for r in g[me]['r']:
                        if r[2] in ('BE','IR'): continue
                        top[(r[0],r[1])]+=r[3];st[(r[0],r[1])]+=1
                        if g['tier'] and (star is None or r[3]>star[2]): star=[r[0],r[1],round(r[3],2),int(w)]
                    if g['tier']=='':
                        reg.append([int(w),oo,round(p,2),round(q,2)]);continue
                    key=(g['mp'],oo)
                    if key not in post:
                        k='cons' if g['tier']=='Consolation' else 'final' if frozenset((o,oo)) in finals else 'po'
                        post[key]=[k,oo,0.0,0.0,[]];rounds.append(key)
                    R=post[key];R[2]=round(R[2]+p,2);R[3]=round(R[3]+q,2);R[4].append([int(w),round(p,2),round(q,2)])
        # its lowest-scoring starter (no K or D/ST) in a single week of its last postseason round
        zero=None
        if rounds:
            for wk in post[rounds[-1]][4]:
                for g in W[str(wk[0])]:
                    for me in ('a','b'):
                        if own(g[me])!=o: continue
                        for r in g[me]['r']:
                            if r[2] in ('BE','IR') or r[1] in ('K','D/ST'): continue
                            if zero is None or r[3]<zero[2]: zero=[r[0],r[1],round(r[3],2),wk[0]]
        P=[post[k][:5] for k in rounds]
        return dict(reg=reg,rk=rk[o],post=P,top=[[n,pos,round(v,1),st[(n,pos)]] for (n,pos),v in top.most_common(9)],star=star,zero=zero,seed=seeds.get(o))
    out[y]=dict(n=len(rec),c=block(CH[y]),s=block(SK[y]))
p=os.path.join(root,'data','thrones.json')
json.dump(out,open(p,'w'),separators=(',',':'),ensure_ascii=False)
for y,v in out.items():
    c,s=v['c'],v['s']
    print(y,CH[y],'seed',c['seed'],[(r[0],r[1],r[2],r[3]) for r in c['post']],'star',c['star'],'|',SK[y],[(r[0],r[1],r[2],r[3]) for r in s['post']],'zero',s['zero'],'low rk',max(s['rk']),min(c['rk']),max(c['rk']))
print(os.path.getsize(p),'bytes')
