# Builds ../data/stories.json: a short storyline for every owner's season, from the weekly results,
# playoff brackets, trades and pickups. Run after weeks.py, playoffs.py and moves.py, and after build.py
# has produced index.html (it reads the built trade list for owner names).
import json,os,re,collections
here=os.path.dirname(os.path.abspath(__file__)); root=os.path.dirname(here)
D=lambda *p:os.path.join(root,*p)
tpl=open(os.path.join(here,'template.html')).read()
SHORT={}
for m in re.finditer(r'^  (\w+):\{name:"([^"]+)",nick:"([^"]*)"(?:,short:"([^"]+)")?',tpl,re.M):
    o,n,nick,sh=m.groups();SHORT[o]=sh or (nick.split(' / ')[0] if nick else n.split(' ')[0])
def js(name):
    i=tpl.index(f'const {name} = ');j=tpl.index('\n',i);src=tpl[i:j].split('=',1)[1].strip().rstrip(';')
    return json.loads(re.sub(r'(\{|,)(\w+):',r'\1"\2":',src))
CHAMPS,SACKOS=js('CHAMPS'),js('SACKOS')
idx=open(D('index.html')).read();i=idx.index('const LEAGUE');LEAGUE=json.loads(idx[i:idx.index('\n',i)].split('=',1)[1].strip().rstrip(';'))
TR={t['id']:t for t in LEAGUE['trades']};STATS=LEAGUE['stats']
MV=json.load(open(D('data','moves.json')));PO=json.load(open(D('data','playoffs.json')))
ord_=lambda n:f"{n}{'th' if 10<=n%100<=20 else {1:'st',2:'nd',3:'rd'}.get(n%10,'th')}"
f1=lambda x:f"{x:.1f}".rstrip('0').rstrip('.') if x is not None else '?'
sh=lambda o:SHORT.get(o,'someone')
def names(l):
    l=[x for x in l if x]
    return l[0] if len(l)==1 else ', '.join(l[:-1])+' and '+l[-1] if l else 'nothing'
out=collections.defaultdict(dict)

def trade_bits(y,o,res=None):
    bits=[]
    tl=[]
    for tid,x in MV['trades'].items():
        t=TR.get(int(tid))
        if not t or t['s']!=y or t['st']!='completed' or o not in (t['a']['o'],t['b']['o']): continue
        me='a' if t['a']['o']==o else 'b';op='b' if me=='a' else 'a'
        tl.append((x[me]['par']-x[op]['par'],x[me]['par'],x[op]['par'],x['w'],t,me,op,x))
    if not tl: return bits,len(tl)
    best=max(tl,key=lambda z:z[0]);worst=min(tl,key=lambda z:z[0])
    def desc(z,good):
        gap,mp,opp,w,t,me,op,x=z
        got=[g[0] for g in sorted(x[me]['got'],key=lambda g:-(g[3] or 0))][:2];gave=[p.split('|')[0] for p in t[me]['gave']][:4]
        when=f"a week {w} trade" if y>=2018 else "a trade"
        s=(f"The move that paid off was {when} with {sh(t[op]['o'])} for {names(got)}" if good else f"The deal that hurt was {when} sending {names(gave)} to {sh(t[op]['o'])}")
        s+=(f", giving up {names(gave)}" if good and gave else "")+(f" for {names(got)}" if not good and got else "")
        s+=f" ({f1(mp)} points over replacement for them, {f1(opp)} for the other side)"
        if res and y>=2018 and good:
            b=[r for r in res if r[0]<w];a=[r for r in res if r[0]>=w]
            if len(b)>=2 and len(a)>=2:
                bw,aw=sum(r[4] for r in b),sum(r[4] for r in a)
                s+=f". They were {bw}-{len(b)-bw} before it and {aw}-{len(a)-aw} after"
        return s+"."
    if best[0]>=40 and best[1]>=40: bits.append(desc(best,True))
    if worst[0]<=-40 and worst is not best: bits.append(desc(worst,False))
    return bits,len(tl)

def pickup_bit(y,o):
    # judge a pickup only by what it did for this team: starts during the stint right after the add
    # (moves.py stops counting once he leaves the roster), at least 3 starts, a real per-start average
    ok=lambda m:m.get('add') and m['add'][1] in('QB','RB','WR','TE') and (m.get('st') or 0)>=3 and (m.get('pts') or 0)>=60 and m['pts']/m['st']>=(15 if m['add'][1]=='QB' else 11)
    pk=[m for m in MV['moves'] if m['y']==y and m['o']==o and ok(m)]
    if not pk: return None
    p=max(pk,key=lambda m:m['pts']);nm=p['add'][0]
    drop=next((m for m in MV['moves'] if m['y']==y and m['o']==o and m.get('drop',[None])[0]==nm and m['w']>p['w']),None)
    end_w=p['w']+p['held']-1
    if drop: tail=f" They dropped him in week {drop['w']}."
    elif end_w<15: tail=f" They traded him away after week {end_w}."
    else: tail=" He stayed on the roster the rest of the year."
    return f"Their best pickup was {nm} ({p['add'][1]}), added in week {p['w']}, who started {p['st']} games for them and scored {f1(p['pts'])} points.{tail}"

def playoff_bit(y,o,seed_rank,n):
    P=PO.get(str(y))
    if not P or not P['rounds']: return None
    r1,fin=P['rounds'][0],P['rounds'][-1][0]
    sf=next((m for m in r1 if o in (m['a']['o'],m['b']['o'])),None)
    if not sf: return None
    me,op=('a','b') if sf['a']['o']==o else ('b','a')
    s=f"As the {ord_(sf[me]['seed'])} seed they "
    if sf['win']!=me: return s+f"lost their semifinal to {sh(sf[op]['o'])}, {f1(sf[me]['pts'])} to {f1(sf[op]['pts'])}."
    s+=f"beat {sh(sf[op]['o'])} in the semifinal, {f1(sf[me]['pts'])} to {f1(sf[op]['pts'])}, "
    fm,fo=('a','b') if fin['a']['o']==o else ('b','a')
    if fin['win']==fm: return s+f"then won the title over {sh(fin[fo]['o'])}, {f1(fin[fm]['pts'])} to {f1(fin[fo]['pts'])}."
    return s+f"then lost the final to {sh(fin[fo]['o'])}, {f1(fin[fm]['pts'])} to {f1(fin[fo]['pts'])}."

for y in range(2018,2027):
    W=json.load(open(D('data','weeks',f'{y}.json')));T=W['teams']
    n=len(T);pc=(PO.get(str(y)) or {}).get('teams') or 4;live=y==2026
    games=collections.defaultdict(list)   # o -> [(w,pts,opp,oppPts,win)]
    for w,gs in sorted(W['weeks'].items(),key=lambda x:int(x[0])):
        for g in gs:
            if g['tier']: continue
            a,b=g['a'],g['b'];ao,bo=T[str(a['t'])][0],T[str(b['t'])][0]
            if a['p'] is None or b['p'] is None: continue
            games[ao].append((int(w),a['p'],bo,b['p'],a['p']>b['p']));games[bo].append((int(w),b['p'],ao,a['p'],b['p']>a['p']))
    weeks=sorted({g[0] for v in games.values() for g in v})
    def rank_after(k):
        tab=[(sum(g[4] for g in v if g[0]<=k),sum(g[1] for g in v if g[0]<=k),o) for o,v in games.items()]
        tab.sort(key=lambda t:(-t[0],-t[1]));return {t[2]:i+1 for i,t in enumerate(tab)}
    ranks={k:rank_after(k) for k in weeks}
    ptsrank={o:i+1 for i,o in enumerate(sorted(games,key=lambda o:-sum(g[1] for g in games[o])))}
    for o,res in games.items():
        if not o: continue
        team=next(v[1] for v in T.values() if v[0]==o)
        N=len(res);wins=sum(r[4] for r in res);L=N-wins
        rec=lambda k:(sum(r[4] for r in res[:k]),k-sum(r[4] for r in res[:k]))
        S=[]
        k0=min(4,N);a0,b0=rec(k0)
        open_=("flew out of the gate at" if a0==k0 and k0>=3 else "started in a hole at" if a0==0 and k0>=3 else "opened")
        S.append(f"{team} {open_} {a0}-{b0}.")
        if live:
            s=f"Through week {weeks[-1]} they are {wins}-{L} and sit {ord_(ranks[weeks[-1]][o])} of {n}"
            s+=f", with {f1(sum(r[1] for r in res))} points so far ({ord_(ptsrank[o])} in the league)." if N>1 else "."
            if N>k0: S.append(s)
            else: S[-1]=S[-1][:-1]+f", {ord_(ranks[weeks[-1]][o])} of {n} so far."
            tb,_=trade_bits(y,o,res);S+=tb
            pb=pickup_bit(y,o)
            if pb: S.append(pb)
            out[o][y]=' '.join(S);continue
        # streaks
        def longest(v):
            best=(0,0,0);run=0
            for i,r in enumerate(res):
                run=run+1 if r[4]==v else 0
                if run>best[0]: best=(run,res[i-run+1][0],r[0])
            return best
        ws,ls=longest(True),longest(False)
        half=N//2;h1=sum(r[4] for r in res[:half]);h2=sum(r[4] for r in res[half:])
        if ws[0]>=4: S.append(f"They won {ws[0]} straight from week {ws[1]} to week {ws[2]}.")
        if ls[0]>=4: S.append(f"They {'also ' if ws[0]>=4 else ''}lost {ls[0]} in a row from week {ls[1]} to week {ls[2]}.")
        if ws[0]<4 and ls[0]<4:
            if h2-h1>=2: S.append(f"They got stronger as the year went on, going {h2}-{N-half-h2} over the second half.")
            elif h1-h2>=2: S.append(f"They cooled off after that, going {h2}-{N-half-h2} over the second half.")
            else: S.append(f"They were {h1}-{half-h1} at the midpoint.")
        fr=ranks[weeks[-1]][o]
        P=PO.get(str(y)) or {};PT={s['o'] for m in (P.get('rounds') or [[]])[0] for s in (m['a'],m['b'])}|{b['o'] for b in P.get('byes',[])}
        made=o in PT if PT else fr<=pc
        low=max(((k,ranks[k][o]) for k in weeks if k>=5 and k<=weeks[-1]-2),key=lambda z:z[1],default=None)
        high=min(((k,ranks[k][o]) for k in weeks if k>=half+1 and k<=weeks[-1]-1),key=lambda z:z[1],default=None)
        if made and low and low[1]>pc+1:
            a,b=rec(sum(1 for r in res if r[0]<=low[0]))
            S.append(f"At {a}-{b} after week {low[0]} they were {ord_(low[1])} of {n} and on the outside looking in, but they fought back into the playoffs.")
        if not made and high and high[1]<=pc:
            a,b=rec(sum(1 for r in res if r[0]<=high[0]))
            S.append(f"They were {a}-{b} and in playoff position after week {high[0]}, then slipped out of it down the stretch.")
        tb,nt=trade_bits(y,o,res);S+=tb
        pb=pickup_bit(y,o)
        if pb: S.append(pb)
        close=[r for r in res if not r[4] and r[3]-r[1]<5]
        pr=ptsrank[o]
        if not made and pr<=3: S.append(f"They scored the {'most' if pr==1 else ord_(pr)+'-most'} points in the league and still missed the playoffs"+(f", with {len(close)} losses by less than five points." if len(close)>=2 else "."))
        elif made and pr>=n-3: S.append(f"They got there despite scoring only the {ord_(pr)}-most points.")
        elif len(close)>=3: S.append(f"{len(close)} of their losses came by less than five points.")
        best=max(res,key=lambda r:r[1])
        if best[1]>=170: S.append(f"Their best week was {f1(best[1])} points against {sh(best[2])} in week {best[0]}.")
        end=f"They finished the regular season {wins}-{L}"+("" if made else f", {ord_(fr)} of {n}")
        if made:
            pb=playoff_bit(y,o,fr,n);S.append(end+"." if not pb else end+". "+pb)
        else:
            cw=min(sum(r[4] for r in games[x]) for x in PT) if PT else wins
            gap=cw-wins
            miss=" and missed the playoffs"+(" on points" if gap==0 else " by one win" if gap==1 else "")
            S.append(end+miss+".")
        if SACKOS.get(str(y),{}).get('o')==o: S.append("It ended with the Sacko.")
        out[o][y]=' '.join(S)

# 2016 and 2017: no weekly results saved
MAN={2016:{'charles':"Charles went 12-1 with a super team and beat Peanut in the first round, then lost the two-week final to Duane, 242 to 190.",
           'duane':"The Emmustangs went 7-6, beat Squirm in the first round, then beat Charles in the two-week final, 242 to 190, to win the first title.",
           'peanut':"Made the playoffs and lost to Charles in the first round.",'squirm':"Made the playoffs and lost to Duane in the first round.",
           'fluff':"Finished last and took the league's first Sacko.",
           'kyle':"The Salty Andres went 6-7 and finished 7th of 8, with 52 pickups and 4 trades on ESPN (the three-team deal with Fluff and Charles went in as two ESPN trades)."},
     2017:{'kyle':"The NYC Klugeys went 10-2, beat Charles in the first round and won the title.",'charles':"Made the playoffs and lost to Kyle in the first round.",
           'vicente':"Made the playoffs in his only season and played Squirm in the first round.",'squirm':"Made the playoffs and played Vicente in the first round.",
           'peanut':"Finished last and took the Sacko.",
           'fluff':"Duane Bernard Jr went 9-3, with David Johnson, Jordy Nelson and Cam Newton on the roster."}}
for y in (2016,2017):
    owners={o for o in (MV['rosters'].get(str(y)) or {})}|set(MAN[y])
    for o in owners:
        if not o: continue
        S=[f"Week-by-week results for {y} weren't saved."]
        r=STATS.get(o,{}).get('seasons',{}).get(str(y))
        tn=((MV['rosters'].get(str(y)) or {}).get(o) or {}).get('team')
        if tn and not MAN[y].get(o): S.append(f"They played as {tn}.")
        if MAN[y].get(o): S.append(MAN[y][o])
        elif r and r.get('w') is not None: S.append(f"They went {r['w']}-{r['l']}.")
        tb,_=trade_bits(y,o);S+=tb
        out[o][y]=' '.join(S)
json.dump(out,open(D('data','stories.json'),'w'),ensure_ascii=False,separators=(',',':'))
for o,y in (('kyle',2025),('dilapi',2021),('charles',2022),('jordan',2025),('quincy',2022),('kyle',2020),('dylan',2024),('kyle',2026),('fluff',2016)): print(o,y,':',out[o].get(y),'\n')
