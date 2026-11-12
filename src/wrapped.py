# Builds ../data/wrapped.json: a Spotify Wrapped style recap for every owner's finished season,
# shown on that owner's team page. Uses data/weeks (lineups with bench points), playoffs.json,
# moves.json and drafts.json. Seasons still being played are skipped (Kyle: never count a live week),
# so 2026 shows up automatically once its weeks file has no current week and the final is in.
# Run after weeks.py, playoffs.py, moves.py and build.py (needs index.html for the trade list).
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
TR={t['id']:t for t in LEAGUE['trades']}
MV=json.load(open(D('data','moves.json')));PO=json.load(open(D('data','playoffs.json')));DR=json.load(open(D('data','drafts.json')))
sh=lambda o:SHORT.get(o,'someone')
f1=lambda x:f"{x:.1f}".rstrip('0').rstrip('.') if x is not None else '?'
ord_=lambda n:f"{n}{'th' if 10<=n%100<=20 else {1:'st',2:'nd',3:'rd'}.get(n%10,'th')}"
FLEX={'FLX':('RB','WR','TE'),'OP':('QB','RB','WR','TE')}
def optimal(roster):
    """Best legal lineup from everyone on the roster that week (IR excluded). Fixed slots first, then flex."""
    slots=[p[2] for p in roster if p[2] not in ('BE','IR')]
    pool=sorted([p for p in roster if p[2]!='IR'],key=lambda p:-(p[3] or 0));used=set();tot=0
    for s in sorted(slots,key=lambda s:s in FLEX):
        ok=FLEX.get(s,(s,))
        for i,p in enumerate(pool):
            if i not in used and p[1] in ok: used.add(i);tot+=p[3] or 0;break
    return tot
def pct_rank(v,allv,high=True):
    s=sorted(allv,reverse=high);return s.index(v)+1

out=collections.defaultdict(dict)
for y in range(2018,2027):
    fn=D('data','weeks',f'{y}.json')
    if not os.path.exists(fn): continue
    W=json.load(open(fn));T=W['teams']
    if W.get('cur') or not any(g['tier']=='Playoffs' for gs in W['weeks'].values() for g in gs) or str(y) not in CHAMPS: continue
    n=len(T);own=lambda t:T[str(t)][0];tname={v[0]:v[1] for v in T.values()}
    reg=collections.defaultdict(list)          # o -> [(w,pts,opp,oppPts,win,optimal,roster)]
    allg=collections.defaultdict(list)         # every game played, incl. playoffs/consolation
    wkscores=collections.defaultdict(dict)     # w -> o -> pts (regular season)
    for w,gs in sorted(W['weeks'].items(),key=lambda x:int(x[0])):
        for g in gs:
            a,b=g['a'],g['b']
            if a['p'] is None or b['p'] is None: continue
            for me,op in ((a,b),(b,a)):
                rec=(int(w),me['p'],own(op['t']),op['p'],me['p']>op['p'],optimal(me['r']),me['r'],g['tier'])
                allg[own(me['t'])].append(rec)
                if not g['tier']: reg[own(me['t'])].append(rec);wkscores[int(w)][own(me['t'])]=me['p']
    owners=[o for o in reg if o]
    pf={o:sum(r[1] for r in reg[o]) for o in owners};pa={o:sum(r[3] for r in reg[o]) for o in owners}
    wins={o:sum(r[4] for r in reg[o]) for o in owners}
    eff={o:sum(r[1] for r in reg[o])/max(1,sum(r[5] for r in reg[o])) for o in owners}
    bench={o:sum(r[5]-r[1] for r in reg[o]) for o in owners}
    # all-play: how often you'd win if you played everybody every week
    ap={}
    for o in owners:
        w_=t_=0
        for wk,sc in wkscores.items():
            if o not in sc: continue
            for p,v in sc.items():
                if p!=o: t_+=1;w_+=(sc[o]>v)+0.5*(sc[o]==v)
        ap[o]=(w_/t_ if t_ else 0)
    adds={o:[m for m in MV['moves'] if m['y']==y and m['o']==o and m.get('add')] for o in owners}
    trades={o:[(int(tid),x) for tid,x in MV['trades'].items() if (t:=TR.get(int(tid))) and t['s']==y and t['st']=='completed' and o in (t['a']['o'],t['b']['o'])] for o in owners}
    standing=sorted(owners,key=lambda o:(-wins[o],-pf[o]));srank={o:i+1 for i,o in enumerate(standing)}
    P=PO.get(str(y)) or {};rounds=P.get('rounds') or []
    dr=DR.get(str(y)) or {};dcol={tm[1]:i for i,tm in enumerate(dr.get('teams',[]))}
    # league-wide player lineup points per team this season
    for o in owners:
        R=reg[o];A=allg[o];N=len(R);w=wins[o];l=N-w;short=sh(o);team=tname.get(o,'')
        slides=[]
        slides.append(dict(k='intro',kicker=f'{y} Wrapped',big=short,sub=team,
            text=f"{N} regular season weeks. {len(adds[o])} pickups. {len(trades[o])} trade{'s' if len(trades[o])!=1 else ''}. Let's see how it went."))
        # top players by points scored in your starting lineup (all games played)
        pp=collections.Counter();starts=collections.Counter();pos={};boom=None
        for r in A:
            for p in r[6]:
                if p[2] in ('BE','IR'): continue
                pp[p[0]]+=p[3] or 0;starts[p[0]]+=1;pos[p[0]]=p[1]
                if p[1] not in ('D/ST','K') and (boom is None or (p[3] or 0)>boom[1]): boom=(p[0],p[3] or 0,r[0],r[2])
        totp=sum(r[1] for r in A) or 1
        top=[(p,v) for p,v in pp.most_common() if pos[p] not in ('D/ST','K')][:5]
        if top:
            p0,v0=top[0]
            slides.append(dict(k='top',kicker='Your top player',big=p0,sub=f"{pos[p0]} · {f1(v0)} points in your lineup",
                text=f"{p0} carried {round(100*v0/totp)}% of everything you scored. {starts[p0]} starts, {f1(v0/max(1,starts[p0]))} a game.",
                list=[[p,pos[p],round(v,1)] for p,v in top]))
        if boom:
            slides.append(dict(k='boom',kicker='Your biggest single game',big=f1(boom[1]),sub=f"{boom[0]} · week {boom[2]}",
                text=f"The best one-week performance anyone gave your lineup all year, against {sh(boom[3])}."))
        # season in numbers
        slides.append(dict(k='numbers',kicker='Your season in numbers',big=f"{w}-{l}",sub=f"{ord_(srank[o])} of {len(owners)} in the regular season",
            stats=[[f1(pf[o]),'points for',f"{ord_(pct_rank(pf[o],list(pf.values())))} in the league"],
                   [f1(pa[o]),'points against',f"{ord_(pct_rank(pa[o],list(pa.values())))} most"],
                   [f1(pf[o]/max(1,N)),'per week','']]))
        # best and worst week
        bw=max(R,key=lambda r:r[1]);ww=min(R,key=lambda r:r[1])
        wkrank=lambda r:sorted(wkscores[r[0]].values(),reverse=True).index(r[1])+1
        slides.append(dict(k='weeks',kicker='Highs and lows',
            stats=[[f1(bw[1]),f'week {bw[0]} vs {sh(bw[2])}',('won' if bw[4] else 'lost')+f" · {'top score of the week' if wkrank(bw)==1 else ord_(wkrank(bw))+' best that week'}"],
                   [f1(ww[1]),f'week {ww[0]} vs {sh(ww[2])}',('somehow won' if ww[4] else 'lost')+f" · {'worst score of the week' if wkrank(ww)==len(wkscores[ww[0]]) else ord_(wkrank(ww))+' best that week'}"]]))
        # luck: all-play vs real record, close games
        exp=ap[o]*N;luck=w-exp
        close=[r for r in R if abs(r[1]-r[3])<10];cw=sum(r[4] for r in close)
        lr=sorted(owners,key=lambda q:-(wins[q]-ap[q]*len(reg[q]))).index(o)+1
        apw=round(ap[o]*N*1)
        if luck>=1.5: lt=f"Against the whole league every week you'd have gone about {apw}-{N-apw}. You went {w}-{l}. The schedule loved you: {ord_(lr)} luckiest in the league."
        elif luck<=-1.5: lt=f"Against the whole league every week you'd have gone about {apw}-{N-apw}. You went {w}-{l}. Robbed: {ord_(len(owners)-lr+1)} unluckiest in the league."
        else: lt=f"Against the whole league every week you'd have gone about {apw}-{N-apw}. You went {w}-{l}. The record was about fair."
        slides.append(dict(k='luck',kicker='Luck check',big=('+' if luck>=0 else '−')+f1(abs(luck)),sub='wins compared with what your scores earned',
            text=lt+(f" In games decided by under 10 points you went {cw}-{len(close)-cw}." if close else " You didn't play a single game decided by under 10 points.")))
        # bench
        blown=[r for r in R if not r[4] and r[5]>r[3]]
        blunder=None
        for r in R:
            st=[p for p in r[6] if p[2] not in ('BE','IR')];be=[p for p in r[6] if p[2]=='BE']
            for b in be:
                for s in st:
                    if s[1]==b[1] and (b[3] or 0)-(s[3] or 0)>(blunder[0] if blunder else 0): blunder=((b[3] or 0)-(s[3] or 0),b,s,r)
        br=pct_rank(bench[o],list(bench.values()))
        bt=f"Your best possible lineup every week would have scored {f1(bench[o])} more points. Lineup efficiency {round(100*eff[o])}%, {ord_(pct_rank(eff[o],list(eff.values())))} in the league."
        if blown: bt+=f" {len(blown)} loss{'es' if len(blown)!=1 else ''} could have been win{'s' if len(blown)!=1 else ''} with the right guys in."
        slides.append(dict(k='bench',kicker='Left on the bench',big=f1(bench[o]),sub='points you never got to use',text=bt,
            note=(f"Worst call: week {blunder[3][0]}, {blunder[1][0]} scored {f1(blunder[1][3])} on your bench while {blunder[2][0]} gave you {f1(blunder[2][3])}." if blunder and blunder[0]>=10 else None)))
        # waiver wire
        A_=adds[o];arank=pct_rank(len(A_),[len(v) for v in adds.values()])
        good=[m for m in A_ if (m.get('st') or 0)>=2 and m['add'][1] not in ('D/ST','K')]
        bp=max(good,key=lambda m:m.get('pts') or 0,default=None)
        wt=f"{len(A_)} adds, {ord_(arank)} most in the league."
        if bp and (bp.get('pts') or 0)>=25: wt+=f" Best find: {bp['add'][0]} ({bp['add'][1]}), picked up before week {bp['w']}, gave you {f1(bp['pts'])} points in {bp['st']} starts."
        elif A_: wt+=" None of them really moved the needle."
        slides.append(dict(k='waivers',kicker='The waiver wire',big=str(len(A_)),sub='pickups',text=wt))
        # trades
        tl=trades[o]
        if tl:
            def net(tid,x):
                t=TR[tid];me='a' if t['a']['o']==o else 'b';op='b' if me=='a' else 'a'
                return x[me]['par']-x[op]['par'],x[me]['par'],t,me,op,x
            nets=[net(*z) for z in tl];best=max(nets,key=lambda z:z[0]);tot=sum(z[0] for z in nets)
            got=[g[0] for g in sorted(best[5][best[3]]['got'],key=lambda g:-(g[3] or 0))][:2]
            gave=[p.split('|')[0] for p in best[2][best[3]]['gave']][:3]
            tt=(f"Best deal: {' and '.join(got) or 'nothing'} from {sh(best[2][best[4]]['o'])} for {' and '.join(gave) or 'nothing'}, {'+' if best[0]>=0 else '−'}{f1(abs(best[0]))} points over replacement." if best[0]>0
                else f"Not one of them came out ahead. The closest was with {sh(best[2][best[4]]['o'])}, {f1(best[0])} points over replacement.")
            slides.append(dict(k='trades',kicker='The trade desk',big=str(len(tl)),sub=f"trade{'s' if len(tl)!=1 else ''} · net {'+' if tot>=0 else '−'}{f1(abs(tot))} pts",text=tt))
        else:
            slides.append(dict(k='trades',kicker='The trade desk',big='0',sub='trades',text="Not a single trade all year. You rode with what you had."))
        # draft
        if o in dcol:
            col=dr['cols'][dcol[o]];pk=[(i+1,c.split('/')[0]) for i,c in enumerate(col)]
            r1=pk[0];r1p=pp.get(r1[1],0)
            late=max([(r,p) for r,p in pk if r>=6 and pos.get(p) not in ('D/ST','K',None)],key=lambda z:pp.get(z[1],0),default=None)
            dt=f"Round 1: {r1[1]}, who gave your lineup {f1(r1p)} points."
            if late and pp.get(late[1],0)>=60: dt+=f" Late-round hero: {late[1]} from round {late[0]}, {f1(pp[late[1]])} points."
            stl=[s for s in dr.get('steals',[]) if s[2]==dcol[o]]
            if stl: dt+=f" One of the steals of the {y} draft: {stl[0][0]}."
            slides.append(dict(k='draft',kicker='Draft day',big=r1[1],sub='your first-round pick',text=dt))
        # rivals: all games incl. playoffs
        h2h=collections.defaultdict(lambda:[0,0,0.0])
        for r in A:
            h=h2h[r[2]];h[0 if r[4] else 1]+=1;h[2]+=r[3]
        nem=max(h2h.items(),key=lambda z:(z[1][1]-z[1][0],z[1][2]))
        vic=max(h2h.items(),key=lambda z:(z[1][0]-z[1][1],-z[1][2]))
        rt=[]
        if nem[1][1]>=2: rt.append([sh(nem[0]),'nemesis',f"{nem[1][0]}-{nem[1][1]} against them",nem[0]])
        if vic[1][0]>=2 and vic[0]!=nem[0]: rt.append([sh(vic[0]),'favorite victim',f"{vic[1][0]}-{vic[1][1]} against them",vic[0]])
        if rt: slides.append(dict(k='rivals',kicker='Your rivals',faces=rt))
        # finish
        seed=None;path=[]
        for ri,rd in enumerate(rounds):
            for m in rd:
                for me,op in (('a','b'),('b','a')):
                    if m[me]['o']==o:
                        seed=m[me]['seed'];path.append((ri,m['win']==me,m[op]['o'],m[me]['pts'],m[op]['pts']))
        champ=CHAMPS[str(y)]['o']==o;sacko=SACKOS.get(str(y),{}).get('o')==o
        if champ:
            f=path[-1] if path else None
            ft=f"The {ord_(seed)} seed went all the way"+(f", beating {sh(f[2])} {f1(f[3])} to {f1(f[4])} in the final." if f else ".")
            slides.append(dict(k='champ',kicker='How it ended',big='Champion',sub=f'{y} Flamingo Men champion',text=ft))
        elif sacko:
            slides.append(dict(k='sacko',kicker='How it ended',big='Sacko',sub=f'the {y} Sacko',text=f"{w}-{l}. The Sacko is yours for a year. There's always next season."))
        elif path:
            last=path[-1]
            if last[0]==len(rounds)-1 and not last[1]: big,txt='Runner-up',f"One game short. {sh(last[2])} beat you {f1(last[4])} to {f1(last[3])} in the final."
            else: big,txt='Playoffs',f"The {ord_(seed)} seed lost in the semifinal to {sh(last[2])}, {f1(last[3])} to {f1(last[4])}."
            slides.append(dict(k='playoffs',kicker='How it ended',big=big,sub=f'{ord_(seed)} seed',text=txt))
        else:
            slides.append(dict(k='missed',kicker='How it ended',big=f'{ord_(srank[o])} place',sub='missed the playoffs',text=f"{w}-{l} and on the outside looking in. "+("So close." if srank[o]==5 else "Next year.")))
        # archetype: the trait where this owner stood out most
        cand=[]
        if champ: cand.append((9,'The Closer','Won the whole thing. Nothing else matters.'))
        if sacko: cand.append((3,'The Sacko','Somebody had to.'))
        if luck>=2: cand.append((5+luck,'The Lucky Charm','Your record beat your scores. Do not question it.'))
        if luck<=-2: cand.append((5-luck,'Snakebitten','You scored like a contender and got paid like a rebuilder.'))
        if arank==1 and len(A_)>=15: cand.append((6,'The Tinkerer','Lived on the waiver wire. The most adds in the league.'))
        if len(tl)>=4 and len(tl)==max(len(v) for v in trades.values()): cand.append((6.5,'The Dealer','Nobody worked the phones harder.'))
        if pct_rank(eff[o],list(eff.values()))==1: cand.append((6,'The Lineup Whisperer','The fewest points left on the bench in the league.'))
        if pct_rank(eff[o],list(eff.values()))==len(owners): cand.append((5.5,'The Benchwarmer','The most points left on the bench in the league.'))
        if pct_rank(pf[o],list(pf.values()))==1: cand.append((7,'The Juggernaut','Scored more than anyone.'))
        if top and top[0][1]/totp>=.2: cand.append((5,'One-Man Band',f"{top[0][0]} did a fifth of the work."))
        if not tl and len(A_)<=8: cand.append((4.5,'Set and Forget','Barely touched the roster. Drafted it and let it ride.'))
        rk=lambda d,hi=True:pct_rank(d[o],list(d.values()),hi)
        if rk(pf)==2: cand.append((4.2,'The Contender','Second-most points in the league. Built to win.'))
        if rk(pa)==1: cand.append((4.4,'The Punching Bag','Nobody had more points scored against them. Every week was somebody\'s best week.'))
        if rk(pa)==len(owners): cand.append((4.1,'The Easy Schedule','Faced the fewest points in the league. Opponents went quiet against you.'))
        if 2<=arank<=2 and len(A_)>=20: cand.append((4,'The Tinkerer','Second-most adds in the league. The waiver wire was your second home.'))
        if close and len(close)-cw>=3 and cw<=1: cand.append((4.6,'The Heartbreak Kid',f"{len(close)-cw} losses by under 10 points."))
        if close and cw>=3 and len(close)-cw<=1: cand.append((4.6,'Clutch',f"{cw} wins by under 10 points. Ice in the veins."))
        sd={q:(sum((r[1]-pf[q]/len(reg[q]))**2 for r in reg[q])/len(reg[q]))**.5 for q in owners}
        if rk(sd)==1: cand.append((3.8,'Boom or Bust','The wildest week-to-week swings in the league.'))
        if rk(sd)==len(owners): cand.append((3.8,'Mr. Consistent','The steadiest scorer in the league. You always knew what you were getting.'))
        if top and top[0][1]/totp>=.15 and not any(c[1]=='One-Man Band' for c in cand): cand.append((3.5,'One-Man Band',f"{top[0][0]} carried {round(100*top[0][1]/totp)}% of the load."))
        if not cand: cand.append((1,'The Grinder','No gimmicks. Just showed up every week.'))
        a=max(cand)
        slides.append(dict(k='aura',kicker=f'Your {y} fantasy aura',big=a[1],text=a[2]))
        # summary card
        fin=('♛ Champion' if champ else 'Sacko' if sacko else slides[-2]['big'])
        slides.append(dict(k='summary',kicker=f'{short} · {y} Wrapped',sub=team,
            stats=[['Record',f"{w}-{l}"],['Finish',fin],['Points',f1(pf[o])],['Top player',top[0][0] if top else '–'],['Pickups',str(len(A_))],['Trades',str(len(tl))],['Bench pts',f1(bench[o])],['Aura',a[1]]]))
        out[o][y]=slides
json.dump(out,open(D('data','wrapped.json'),'w'),ensure_ascii=False,separators=(',',':'))
print('wrapped',sum(len(v) for v in out.values()),'owner-seasons')
