# Builds ../index.html from template.html + ../data/league.json, applying the owner corrections Kyle gave.
import json,os
here=os.path.dirname(os.path.abspath(__file__)); root=os.path.dirname(here)
t=open(os.path.join(here,'template.html')).read()
league=json.load(open(os.path.join(root,'data','league.json')))
# Kyle, 2026-09-29: Charles's 2016 regular season (12-1) is the only 2016 record saved
league['stats']['charles']['seasons'].setdefault('2016',dict(w=12,l=1,pts=None))

# Team name -> owner, from Kyle (2026-09-28) or by elimination against the stats sheet
TEAM_OWNER={
 'Bittersweet Distract0rs':'kyle',            # Kyle: the 2019 Zeke deal with Skelly was his
 'Sal’s 12 Chickens':'charles',"Sal's 12 Chickens":'charles',"Sal's 34 Chickens":'charles',
 "Sal's Chickens":'charles','Jerry Jewdys':'jordan',  # Jerry Jewdys = Jordan per 2022 ESPN page; Los Stogies = Lucas per 2021 ESPN page
 'Taylor Top Kyle Bottom':'charles','Texas A and M Aggies':'charles',
 'Chicago Titysquashers':'jerry','Chicago Tïttysquashers':'jerry',
 # from Kyle's filled-in clarifications sheet
 'DilapiSTILLaint Makingthe yoffs':'kyle','Pinky Sized Kyle':'peanut','The Yogurtlechefts':'peanut',
 'The Neurotic yogurtlechafts':'peanut','The Squimps':'peanut','busty hips chunky chips':'peanut',
 'Harlem Brown Men':'jordan','Let Dalvin Cook':'jordan','Let Russ Carry My Team':'jordan','Oh My BJ':'fluff',
 'Bishop Sycamore JV':'jordan',"Kelce's Kiddies":'jordan','Galaxy Liberators':'jordan',
 "Drake Maye's Aura":'quincy','FLOOFS RED TAINT':'peanut','RED ZONE':'peanut','THE LAND DOWN UNDER':'peanut','THE SOUTH':'peanut',
}
RENAME={'The Virgin Chucks':'The Monglers','busty hips chunky chips':'The Yogurtlechefts','The Neurotic yogurtlechafts':'The Yogurtlechefts','Texas A and M Aggies':"Sal's 12 Chickens",'Sal’s 12 Chickens':"Sal's 12 Chickens",'Taylor Top Kyle Bottom':"Sal's 12 Chickens",'Pinky Sized Kyle':'The Yogurtlechefts'}
STATUS={22:('completed','Veto overturned by league vote')}   # Kyle: vetoed, then overturned by a league vote
# 2016 (ESPN "The LI League") and 2017 trade emails, forwarded by Charles on 2026-09-28
EARLY=[
 ('2016-10-05',('NYC Klugeys','kyle',['Julio Jones|WR','Jordan Reed|TE','Mark Ingram|RB']),('Little Bills','charles',['Calvin Johnson|WR','Marshawn Lynch|RB','Alshon Jeffery|WR'])),
 # Kyle, 2026-10-03: these three are legs of one three-team trade (Kyle, Fluff, Charles); the site groups them (TRI in template.html)
 ('2016-10-24',('NYC Klugeys','kyle',['Tyler Lockett|WR']),('Team Duffy','fluff',['Jonathan Stewart|RB'])),
 ('2016-10-24',('Team Duffy','fluff',['Greg Olsen|TE']),('Little Bills','charles',['Coby Fleener|TE'])),
 ('2016-10-24',('NYC Klugeys','kyle',[]),('Little Bills','charles',['Jordan Reed|TE'])),
 ('2016-11-03',('Team Duffy','fluff',['Amari Cooper|WR','Chiefs D/ST|D/ST']),('NYC Klugeys','kyle',['Terrance West|RB','Ravens D/ST|D/ST','Carson Palmer|QB','Stephen Gostkowski|K'])),
 ('2017-08-08',('Heaven Peanus','peanut',['Jameis Winston|QB']),('The Dominican DS','rod',['Andrew Luck|QB'])),
 ('2017-08-08',('The Brooklyn Noses','dilapi',['Justin Tucker|K']),('N Town Dolphins','kyle',['Wil Lutz|K','Mike Gillislee|RB'])),
 ('2017-09-01',('Heaven Peanus','peanut',['Andrew Luck|QB']),('Sensitive Lesbians','charles',['Willie Snead|WR'])),
 # 2026 trades Kyle reported on 2026-09-29 (pick numbers checked against the 2026 board: Dylan drafted 4th, DiLapi 9th)
 ('2026-08-24',('Sultans of Squirm','dylan',['No. 9 overall pick, 2026 draft|Pick']),('New York Noses','dilapi',['No. 4 overall pick, 2026 draft|Pick'])),
 ('2026-09-25',('THE MONGLERS','kyle',['Hunter Henry|TE','Sam Darnold|QB']),('Galaxy Liberators','jordan',['Romeo Doubs|WR'])),
 # Kyle, 2026-09-29: before the 2017 draft Charles traded Peanut a secret for his pick (exact date not saved; dated to draft day)
 ('2017-08-06',('Little Bills','charles',['A secret|Secret']),('Team Peanus','peanut',["Peanut's 2017 draft pick|Pick"])),
 # 2018 trades from ESPN's transaction history (pulled 2026-09-29 with Kyle's cookies; none were in the email archive)
 ('2018-08-18', ('Hempstead Cummings', 'peanut', ['Mike Evans|WR', 'Cam Newton|QB']), ('The Sal Claps On Planes', 'charles', ['Demaryius Thomas|WR', 'Sony Michel|RB', 'Matt Ryan|QB'])),
 ('2018-09-21', ('New York Noses', 'dilapi', ['Kareem Hunt|RB', 'Patrick Mahomes|QB']), ('The Sal Claps On Planes', 'charles', ['James Conner|RB', 'Matt Breida|RB'])),
 ('2018-09-25', ('New York Noses', 'dilapi', ['Quincy Enunwa|WR']), ('Dilapi aint Makingthe yoffs', 'kyle', ['DeSean Jackson|WR'])),
 ('2018-10-05', ('Dilapi aint Makingthe yoffs', 'kyle', ['James White|RB']), ('Hempstead Cummings', 'peanut', ['JuJu Smith-Schuster|WR'])),
 ('2018-10-27', ('Team Quincy', 'quincy', ['Tevin Coleman|RB']), ('Dilapi aint Makingthe yoffs', 'kyle', ['Kenny Golladay|WR', 'Stephen Gostkowski|K'])),
 ('2018-11-02', ('Hempstead Cummings', 'peanut', ['Phillip Lindsay|RB', 'Demaryius Thomas|WR']), ('The Sal Claps On Planes', 'charles', ['O.J. Howard|TE', 'Mark Ingram II|RB'])),
 ('2018-11-09', ('Dilapi aint Makingthe yoffs', 'kyle', ['Todd Gurley II|RB']), ('The Sal Claps On Planes', 'charles', ['Nick Chubb|RB'])),
 ('2018-11-15', ('The Sal Claps On Planes', 'charles', ['Sony Michel|RB', 'Phillip Lindsay|RB']), ('Dilapi aint Makingthe yoffs', 'kyle', [])),
 ('2018-11-22', ('Hempstead Cummings', 'peanut', ['Saquon Barkley|RB']), ('The Sal Claps On Planes', 'charles', ['Todd Gurley II|RB'])),
]
for d,(ta,oa,ga),(tb,ob,gb) in EARLY:
    league['trades'].append(dict(id=len(league['trades']),d=d,s=int(d[:4]),st='completed',a=dict(team=ta,o=oa,gave=ga),b=dict(team=tb,o=ob,gave=gb)))
flags={}
for tr in league['trades']:
    for s in (tr['a'],tr['b']):
        if s['team'] in TEAM_OWNER: s['o']=TEAM_OWNER[s['team']]
        s['team']=RENAME.get(s['team'],s['team'])
    if tr['id'] in STATUS:
        tr['st'],flags[tr['id']]=STATUS[tr['id']]

# 2026 in progress: standings screenshot after week 2 (owner names from the ESPN season stats table)
S2026={'jordan':(2,0,285.9,'Galaxy Liberators',4),'lucas':(2,0,269.64,'Student Ath-o-letes',3),'dylan':(2,0,243.76,'Sultans of Squirm',1),
 'kyle':(1,1,290.48,'THE MONGLERS',12),'dilapi':(1,1,258.46,'New York Noses',6),'charles':(1,1,234.04,"Sal's 4 Chickens",7),
 'jerry':(1,1,232.38,'Chicago Tiddysquashers',12),'rod':(1,1,210.0,'2girls 1Kupp',5),'fluff':(1,1,187.76,'SQUIRMYS SLUTZS',7),
 'squirm':(0,2,223.08,'#dicksoutfor Dolan',3),'ghost':(0,2,175.86,"Vick's Vet Clinic",2),'quincy':(0,2,136.04,"Quincy Jonesin' for a TD",8)}
# newer: rebuild the 2026 table from ESPN's weekly results (data/weeks/2026.json, completed weeks only)
wf=os.path.join(root,'data','weeks','2026.json')
if os.path.exists(wf):
    W=json.load(open(wf));cur=W.get('cur') or 99;mv=json.load(open(os.path.join(root,'data','moves.json')))
    new={}
    for wk,gs in W['weeks'].items():
        if int(wk)>=cur: continue
        for g in gs:
            for me,op in ((g['a'],g['b']),(g['b'],g['a'])):
                o,tn=W['teams'][str(me['t'])];r=new.setdefault(o,[0,0,0.0,tn,0])
                r[0 if me['p']>op['p'] else 1]+=1;r[2]=round(r[2]+me['p'],2)
    for m in mv['moves']:
        if m['y']==2026 and m['o'] in new: new[m['o']][4]+=1
    if new: S2026={o:tuple(v) for o,v in new.items()}
live={}
for o,(w,l,pts,team,moves) in S2026.items():
    league['stats'].setdefault(o,{'seasons':{},'titles':0,'sackos':0})['seasons']['2026']=dict(w=w,l=l,pts=pts,live=True)
    live[o]=dict(team=team,moves=moves)
imgs={os.path.splitext(f)[0]:'img/'+f for f in os.listdir(os.path.join(root,'img')) if os.path.isfile(os.path.join(root,'img',f)) and not f.startswith(('draft-','roster-','awards-'))}
# transparent cutouts for the Champions and Sackos cards
cuts={os.path.splitext(f)[0]:'img/cut/'+f for f in os.listdir(os.path.join(root,'img','cut'))}
t=t.replace('/*DATA*/',json.dumps(league,ensure_ascii=False,separators=(',',':'))).replace('/*IMGS*/',json.dumps(imgs)).replace('/*FLAGS*/',json.dumps(flags)).replace('/*LIVE*/',json.dumps(live)).replace('/*CUTS*/',json.dumps(cuts)).replace('/*DRAFTS*/',open(os.path.join(root,'data','drafts.json')).read())
# ESPN waiver/roster history and the rebuilt seasons, from src/moves.py
t=t.replace('/*MOVES*/',open(os.path.join(root,'data','moves.json')).read())
t=t.replace('/*PLAYOFFS*/',open(os.path.join(root,'data','playoffs.json')).read())
t=t.replace('/*RECORDS*/',open(os.path.join(root,'data','records.json')).read())
t=t.replace('/*RANKINGS*/',open(os.path.join(root,'data','rankings.json')).read() if os.path.exists(os.path.join(root,'data','rankings.json')) else '{}')
t=t.replace('/*STORIES*/',open(os.path.join(root,'data','stories.json')).read() if os.path.exists(os.path.join(root,'data','stories.json')) else '{}')
open(os.path.join(root,'index.html'),'w').write(t)
print('ok',len(t))
