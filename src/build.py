# Builds ../index.html from template.html + ../data/league.json, applying the owner corrections Kyle gave.
import json,os
here=os.path.dirname(os.path.abspath(__file__)); root=os.path.dirname(here)
t=open(os.path.join(here,'template.html')).read()
league=json.load(open(os.path.join(root,'data','league.json')))

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
 ('2016-10-24',('Team Duffy','fluff',['Tyler Lockett|WR']),('NYC Klugeys','kyle',['Jonathan Stewart|RB'])),
 ('2016-10-24',('Team Duffy','fluff',['Greg Olsen|TE']),('Little Bills','charles',['Coby Fleener|TE'])),
 ('2016-10-25',('NYC Klugeys','kyle',[]),('Little Bills','charles',['Jordan Reed|TE'])),
 ('2016-11-03',('Team Duffy','fluff',['Amari Cooper|WR','Chiefs D/ST|D/ST']),('NYC Klugeys','kyle',['Terrance West|RB','Ravens D/ST|D/ST','Carson Palmer|QB','Stephen Gostkowski|K'])),
 ('2017-08-08',('Heaven Peanus','peanut',['Jameis Winston|QB']),('The Dominican DS','rod',['Andrew Luck|QB'])),
 ('2017-08-08',('The Brooklyn Noses','dilapi',['Justin Tucker|K']),('N Town Dolphins','kyle',['Wil Lutz|K','Mike Gillislee|RB'])),
 ('2017-09-01',('Heaven Peanus','peanut',['Andrew Luck|QB']),('Sensitive Lesbians','charles',['Willie Snead|WR'])),
 # 2026 trades Kyle reported on 2026-09-29 (pick numbers checked against the 2026 board: Dylan drafted 4th, DiLapi 9th)
 ('2026-08-24',('Sultans of Squirm','dylan',['No. 9 overall pick, 2026 draft|Pick']),('New York Noses','dilapi',['No. 4 overall pick, 2026 draft|Pick'])),
 ('2026-09-25',('THE MONGLERS','kyle',['Hunter Henry|TE','Sam Darnold|QB']),('Galaxy Liberators','jordan',['Romeo Doubs|WR'])),
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
live={}
for o,(w,l,pts,team,moves) in S2026.items():
    league['stats'].setdefault(o,{'seasons':{},'titles':0,'sackos':0})['seasons']['2026']=dict(w=w,l=l,pts=pts,live=True)
    live[o]=dict(team=team,moves=moves)
imgs={os.path.splitext(f)[0]:'img/'+f for f in os.listdir(os.path.join(root,'img')) if os.path.isfile(os.path.join(root,'img',f)) and not f.startswith(('draft-','roster-','awards-'))}
# transparent cutouts for the Champions and Sackos cards
cuts={os.path.splitext(f)[0]:'img/cut/'+f for f in os.listdir(os.path.join(root,'img','cut'))}
t=t.replace('/*DATA*/',json.dumps(league,ensure_ascii=False,separators=(',',':'))).replace('/*IMGS*/',json.dumps(imgs)).replace('/*FLAGS*/',json.dumps(flags)).replace('/*LIVE*/',json.dumps(live)).replace('/*CUTS*/',json.dumps(cuts)).replace('/*DRAFTS*/',open(os.path.join(root,'data','drafts.json')).read())
open(os.path.join(root,'index.html'),'w').write(t)
print('ok',len(t))
