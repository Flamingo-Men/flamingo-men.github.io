# Builds ../data/sacko.json: each season's Sacko bracket (ESPN consolation games among the non-playoff teams), for the
# Playoffs / Sacko toggle on History brackets (Kyle 2026-11-22). Reads data/weeks/*.json and data/playoffs.json.
# Each two-week round is one game decided by the two-week total. The 3rd-place game between semifinal losers is left out.
# Run after weeks.py and playoffs.py, before build.py.
import json,os,glob
here=os.path.dirname(os.path.abspath(__file__)); root=os.path.dirname(here)
PO=json.load(open(os.path.join(root,'data','playoffs.json')))
out={}
for f in sorted(glob.glob(os.path.join(root,'data','weeks','*.json'))):
    y=int(os.path.basename(f)[:4]);d=json.load(open(f));T=d['teams'];cur=d.get('cur')
    pt={s['o'] for rd in PO.get(str(y),{}).get('rounds',[]) for m in rd for s in (m['a'],m['b']) if s.get('o')}
    R={}
    for w,gs in d['weeks'].items():
        if cur and int(w)>=cur: continue
        for g in gs:
            if g['tier'] in ('','Playoffs'): continue
            a,b=g['a'],g['b']
            if a['p'] is None or b['p'] is None: continue
            oa,ob=T[str(a['t'])][0],T[str(b['t'])][0]
            if oa in pt and ob in pt: continue
            rd=R.setdefault(g['mp'],{})
            m=rd.setdefault((oa,ob),dict(a=dict(o=oa,team=T[str(a['t'])][1],pts=0.0),b=dict(o=ob,team=T[str(b['t'])][1],pts=0.0),wk=[]))
            m['a']['pts']=round(m['a']['pts']+a['p'],2);m['b']['pts']=round(m['b']['pts']+b['p'],2);m['wk'].append(int(w))
    if not R: continue
    rounds=[]
    for mp in sorted(R):
        L=[]
        for m in R[mp].values():
            m['win']='a' if m['a']['pts']>m['b']['pts'] else 'b' if m['b']['pts']>m['a']['pts'] else None
            m['wk']=sorted(m['wk']);L.append(m)
        rounds.append(L)
    out[y]=dict(rounds=rounds)
json.dump(out,open(os.path.join(root,'data','sacko.json'),'w'),separators=(',',':'))
print('sacko',{y:[len(r) for r in v['rounds']] for y,v in out.items()})
