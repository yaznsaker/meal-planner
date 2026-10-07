import json, subprocess, sys, time, urllib.request
from pathlib import Path
ROOT=Path(__file__).parent
sys.path.insert(0,str(ROOT)); import core

def req(url, method='GET', data=None):
    body=None if data is None else json.dumps(data).encode()
    r=urllib.request.Request(url,data=body,method=method,headers={'Content-Type':'application/json'} if body else {})
    with urllib.request.urlopen(r,timeout=5) as x: return json.loads(x.read())

def main():
    assert core.VERSION=='1.1-production'
    assert round(core.bmr_mifflin(90,180,30,'male'),1)==1880.0
    c=core.macro_targets(2240,85,1.8,.8); assert c['carbs']>0
    p=core.build_plan({'kcal':2240,'protein':153,'carbs':254,'fat':68},seed=11,iterations=400)
    assert set(p['totals'])=={'kcal','protein','carbs','fat'}
    assert p['validation']['valid'] or p['validation']['errors']
    proc=subprocess.Popen([sys.executable,'app.py'],cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    try:
        time.sleep(.7)
        h=req('http://127.0.0.1:8000/api/health'); assert h['ok']
        f=req('http://127.0.0.1:8000/api/foods'); assert len(f['foods'])==16
        calc=req('http://127.0.0.1:8000/api/calculate','POST',{'weight':85,'height':180,'age':30,'sex':'male','activity':1.55,'goal':'lose'}); assert calc['calculation']['BMR']>0
        plan=req('http://127.0.0.1:8000/api/plan','POST',{'kcal':2240,'protein':153,'carbs':254,'fat':68}); assert 'meals' in plan
        week=req('http://127.0.0.1:8000/api/week','POST',{'kcal':2240,'protein':153,'carbs':254,'fat':68,'days':3}); assert len(week['days'])==3
        assert all(all(week['days'][i]['meals'][m] for m in ('Breakfast','Lunch','Snack','Dinner')) for i in range(3))
        assert all(week['days'][i]['validation']['valid'] for i in range(3))
        alt=req('http://127.0.0.1:8000/api/alternatives','POST',{'food':'chicken_breast'}); assert alt['alternatives']
        try: req('http://127.0.0.1:8000/static/../core.py')
        except Exception: pass
        else: raise AssertionError('path traversal was not rejected')
    finally:
        proc.terminate(); proc.wait(timeout=3)
    print('ALL V1.1 TESTS PASSED')
if __name__=='__main__': main()
