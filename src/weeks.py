# Builds ../data/weeks/{year}.json: every week's matchups with both lineups and each player's points.
# Usage: python3 weeks.py CACHE_DIR   (reads the box_{y}_{w}.json and full_{y}.json files moves.py cached)
import json,os,re,sys
here=os.path.dirname(os.path.abspath(__file__)); root=os.path.dirname(here); CACHE=sys.argv[1]
MEMBER={'Charles Lorenzo':'charles','Jack Duffy':'fluff','Chris DiLapi':'dilapi','Sean Woram':'squirm','Tommy Curran':'quincy','Kyle Klugewicz':'kyle',
 'Andrew Woram':'peanut','Lucas Pace':'lucas','Sean Kelly':'skelly','Jordan Cruz':'jordan','Christian Rod':'rod','Jeremy Carroll':'jerry','Dylan Olivieri':'dylan','Adam Smith':'ghost','Mateus Toppin':'mateus'}
POS={1:'QB',2:'RB',3:'WR',4:'TE',5:'K',16:'D/ST'}
SLOT={0:'QB',2:'RB',4:'WR',6:'TE',16:'D/ST',17:'K',23:'FLX',20:'BE',21:'IR'}
ORDER=['QB','RB','WR','TE','FLX','D/ST','K','BE','IR']
TIER={'WINNERS_BRACKET':'Playoffs','WINNERS_CONSOLATION_LADDER':'Consolation','LOSERS_CONSOLATION_LADDER':'Consolation'}
ns={};src=open(os.path.join(here,'build.py')).read();exec(src[src.index('RENAME='):src.index('\n',src.index('RENAME='))],ns)
RN={' '.join(k.lower().split()):v for k,v in ns['RENAME'].items()}
os.makedirs(os.path.join(root,'data','weeks'),exist_ok=True)
for y in range(2018,2027):
    full=json.load(open(os.path.join(CACHE,f'full_{y}.json')))
    mem={m['id']:f"{m['firstName']} {m['lastName']}" for m in full['members']}
    T={}
    for t in full['teams']:
        nm=re.sub(r'\s+',' ',t.get('name') or (t.get('location','')+' '+t.get('nickname',''))).strip()
        T[t['id']]=[MEMBER.get(mem.get((t.get('owners') or [''])[0])),RN.get(' '.join(nm.lower().split()),nm)]
    MP={int(k):v for k,v in full['settings']['scheduleSettings']['matchupPeriods'].items()}
    weeks={}
    w=1
    while os.path.exists(os.path.join(CACHE,f'box_{y}_{w}.json')):
        d=json.load(open(os.path.join(CACHE,f'box_{y}_{w}.json')))
        out=[]
        for m in d['schedule']:
            if w not in MP.get(m['matchupPeriodId'],[]) or 'away' not in m: continue
            sides=[]
            for k in ('home','away'):
                s=m[k];pts=s.get('pointsByScoringPeriod',{}).get(str(w))
                ro=[]
                for e in (s.get('rosterForCurrentScoringPeriod') or {}).get('entries',[]):
                    p=e['playerPoolEntry']['player']
                    st=[x for x in p.get('stats',[]) if x.get('scoringPeriodId')==w and x.get('statSourceId')==0]
                    sl=SLOT.get(e['lineupSlotId'],'FLX')
                    ro.append([p['fullName'],POS.get(p.get('defaultPositionId'),''),sl,round(st[0]['appliedTotal'],2) if st else 0])
                ro.sort(key=lambda r:(ORDER.index(r[2]) if r[2] in ORDER else 9))
                if pts is None and ro: pts=round(sum(r[3] for r in ro if r[2] not in('BE','IR')),2)
                sides.append(dict(t=s['teamId'],p=pts,r=ro))
            if sides[0]['p'] is None and sides[1]['p'] is None: continue
            per=MP[m['matchupPeriodId']]
            tier=TIER.get(m.get('playoffTierType'),'')
            out.append(dict(a=sides[0],b=sides[1],tier=tier,leg=f"{per.index(w)+1} of {len(per)}" if len(per)>1 else "",mp=m['matchupPeriodId'],tot=[m['home'].get('totalPoints'),m['away'].get('totalPoints')] if len(per)>1 else None))
        if out and any((x['a']['p'] or 0)+(x['b']['p'] or 0)>0 for x in out): weeks[w]=out
        w+=1
    js=json.dumps(dict(teams=T,weeks=weeks),separators=(',',':'))
    open(os.path.join(root,'data','weeks',f'{y}.json'),'w').write(js)
    print(y,len(weeks),'weeks',sum(len(v) for v in weeks.values()),'games',len(js)//1024,'KB',sum(1 for v in weeks.values() for g in v for s in (g['a'],g['b']) if not s['r']),'empty rosters')
