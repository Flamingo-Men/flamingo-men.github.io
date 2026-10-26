# Tags draft-board picks who missed more than 8 games of that NFL season through injury, and keeps them off the
# "Worst picks" list. Writes "inj" ([round, column, games played]) into ../data/drafts.json, drops injured players
# from each year's busts and tops the list back up to four with the worst healthy picks of the first six rounds.
# Usage: python3 injuries.py CACHE_DIR   (same ESPN cache as moves.py; run after players.py, then build.py)
import json,os,sys,collections
here=os.path.dirname(os.path.abspath(__file__)); root=os.path.dirname(here); sys.path.insert(0,here)
import moves as M
F=os.path.join(root,'data','drafts.json');DR=json.load(open(F))
P=json.load(open(os.path.join(root,'data','players.json')))['p']
# missed time that wasn't injury: unsigned, cut, benched, retired, suspended, holdouts, personal leave
NOT_INJ={2016:{'Matt Jones','Arian Foster'},2017:{'Colin Kaepernick','Victor Cruz','Matt Moore','Jeremy Langford','Mike Davis'},
 2018:{'Eric Decker',"Le'Veon Bell"},2019:{'Antonio Brown','Eli Manning','Kapri Bibbs','Andrew Luck','Jordan Thomas'},2020:{'Reggie Bonnafon','Derrius Guice','Delanie Walker','Jordan Howard'},
 2021:{'Henry Ruggs III','Trey Sermon','Calvin Ridley',"Le'Veon Bell",'Deshaun Watson','Antonio Brown','Matt Breida'},
 2022:{'Deshaun Watson'},2023:{'Cam Akers','Leonard Fournette'},2024:{'Zamir White'},2025:{'Zay Jones','Jaydon Blue','Rashee Rice'}}
ORD=lambda n:f"{n}{'th' if 10<=n%100<=20 else {1:'st',2:'nd',3:'rd'}.get(n%10,'th')}"
for y in range(2016,2026):
    D=DR[str(y)];n=len(D['cols']);G=16 if y<=2020 else 17;PY=M.players(y)
    fin={};by=collections.defaultdict(list)
    for i,p in PY.items(): by[p['pos']].append((p['tot'],i))
    for l in by.values():
        for k,(_,i) in enumerate(sorted(l,reverse=True)): fin[i]=k+1
    inj=[];cand=[];taken=collections.Counter()
    picks=[]
    for c,col in enumerate(D['cols']):
        for r,v in enumerate(col):
            if v: nm,_,ps=v.rpartition('/');picks.append((r*n+(c+1 if r%2==0 else n-c),r+1,c,nm,ps))
    for pick,r,c,nm,ps in sorted(picks):
        if ps not in('QB','RB','WR','TE'): continue
        taken[ps]+=1;pid=M.find(y,nm,ps)
        if pid is None: continue
        s=P.get(str(pid),{}).get('y',{}).get(str(y),{});gp=(s.get('ln') or [None])[0]
        if gp is not None and not s.get('pts'): gp=0   # ESPN lists some season-long IR players with a full games count
        if gp is not None and G-gp>8 and nm not in NOT_INJ.get(y,()): inj.append([r,c,gp]);continue
        if r<=6 and gp is not None: cand.append((fin[pid]-taken[ps],r,c,nm,ps,taken[ps],fin[pid],PY[pid]['tot'],gp))
    D['inj']=inj;hurt={(r,c) for r,c,_ in inj}
    D['busts']=[b for b in D['busts'] if (b[1],b[2]) not in hurt]
    have={(b[1],b[2]) for b in D['busts']}
    for drop,r,c,nm,ps,t,f,tot,gp in sorted(cand,reverse=True):
        if len(D['busts'])>=4: break
        if (r,c) in have or drop<12: continue
        D['busts'].append([nm,r,c,f"Round {r} pick and the {ORD(t)} {ps} taken, but finished {ps}{f} with {round(tot)} points in {gp} games."])
    print(y,'injured',len(inj),'busts',[b[0] for b in D['busts']])
json.dump(DR,open(F,'w'),ensure_ascii=False,separators=(',',':'))
