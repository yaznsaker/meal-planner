from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse
from pathlib import Path
import json, os, sys

BASE = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE))
import core

HOST = '0.0.0.0'
PORT = int(os.environ.get('PORT', '8000'))

FOOD_CATALOG = [
    {'name': f.name, 'group': f.group, 'kcal': f.kcal, 'protein': f.protein,
     'carbs': f.carbs, 'fat': f.fat, 'min_g': f.min_g, 'max_g': f.max_g,
     'step_g': f.step_g, 'tags': list(f.tags)} for f in core.FOODS
]

MIME = {
    '.html':'text/html; charset=utf-8', '.css':'text/css; charset=utf-8',
    '.js':'application/javascript; charset=utf-8', '.json':'application/json; charset=utf-8',
    '.webmanifest':'application/manifest+json; charset=utf-8', '.png':'image/png',
    '.ico':'image/x-icon', '.svg':'image/svg+xml'
}

class Handler(BaseHTTPRequestHandler):
    server_version = 'MealPlanner/1.0'

    def security_headers(self):
        self.send_header('X-Content-Type-Options','nosniff')
        self.send_header('X-Frame-Options','SAMEORIGIN')
        self.send_header('Referrer-Policy','strict-origin-when-cross-origin')
        self.send_header('Permissions-Policy','geolocation=(), microphone=(), camera=()')

    def send_json(self, data, status=200):
        raw = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status); self.security_headers(); self.send_header('Content-Type','application/json; charset=utf-8'); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)

    def send_file(self, path):
        path = Path(path)
        if not path.exists() or not path.is_file(): self.send_error(404); return
        raw = path.read_bytes(); self.send_response(200); self.security_headers(); self.send_header('Content-Type',MIME.get(path.suffix,'application/octet-stream')); self.send_header('Content-Length',str(len(raw))); self.end_headers(); self.wfile.write(raw)

    def do_GET(self):
        p = urlparse(self.path).path
        routes = {
            '/': BASE/'web/templates/index.html', '/app.js': BASE/'web/static/app.js',
            '/styles.css': BASE/'web/static/styles.css', '/manifest.webmanifest': BASE/'web/static/manifest.webmanifest',
            '/sw.js': BASE/'web/static/sw.js', '/icon-192.png': BASE/'web/static/icon-192.png',
            '/icon-512.png': BASE/'web/static/icon-512.png'
        }
        if p.startswith('/static/'):
            rel = p[len('/static/'):]
            self.send_file(BASE/'web/static'/rel); return
        if p in routes:
            self.send_file(routes[p]); return
        if p == '/api/foods': return self.send_json({'foods':FOOD_CATALOG,'version':core.VERSION})
        if p in ('/api/health','/health'): return self.send_json({'ok':True,'version':core.VERSION})
        self.send_error(404)

    def read_json(self):
        length = int(self.headers.get('Content-Length','0'))
        if length > 2_000_000: raise ValueError('Request too large')
        body = self.rfile.read(length)
        data = json.loads(body or '{}')
        if not isinstance(data, dict): raise ValueError('Invalid JSON body')
        return data

    def do_POST(self):
        p = urlparse(self.path).path
        try:
            d = self.read_json()
            if p == '/api/calculate': return self.calculate(d)
            if p == '/api/plan': return self.plan(d)
            if p == '/api/week': return self.week(d)
            if p == '/api/alternatives': return self.alts(d)
            self.send_error(404)
        except ValueError as e: self.send_json({'error':str(e)},400)
        except Exception:
            self.send_json({'error':'حدث خطأ غير متوقع في الخادم'},500)

    def calculate(self,d):
        required=['weight','height','age','sex','activity','goal']
        if any(k not in d for k in required): raise ValueError('Missing required profile fields')
        w=float(d['weight']); h=float(d['height']); age=int(d['age']); activity=float(d['activity']); sex=d['sex']; goal=d['goal']
        if not (20<=w<=400 and 100<=h<=230 and 10<=age<=100 and 1.0<=activity<=2.5): raise ValueError('Profile values are outside supported ranges')
        if sex not in ('male','female') or goal not in ('lose','maintain','gain'): raise ValueError('Invalid sex or goal')
        b=core.bmr_mifflin(w,h,age,sex); td=core.tdee(b,activity); kcal=core.calorie_target(td,goal,float(d.get('deficit_pct',20)),float(d.get('surplus_pct',10)))
        mt=core.macro_targets(kcal,w,float(d.get('protein_gkg',1.8)),float(d.get('fat_gkg',.8)))
        return self.send_json({'calculation':{'BMR':round(b,1),'TDEE':round(td,1),'target_kcal':round(kcal,1),'goal':goal,'activity_factor':activity},'target':{k:round(v,1) for k,v in mt.items()}})

    def common(self,d):
        target={k:float(d[k]) for k in ('kcal','protein','carbs','fat')}
        if any(v<=0 for v in target.values()): raise ValueError('Targets must be positive')
        forbidden=[x for x in d.get('forbidden',[]) if x in core.BYNAME]
        preferred=[x for x in d.get('preferred',[]) if x in core.BYNAME and x not in forbidden]
        ratios=d.get('ratios') or core.DEFAULT_RATIOS; allowed=d.get('allowed') or None
        return target,allowed,forbidden,preferred,ratios

    def plan(self,d):
        target,allowed,forbidden,preferred,ratios=self.common(d)
        return self.send_json(core.build_plan(target,allowed,forbidden,preferred,ratios,int(d.get('seed',7)),min(int(d.get('iterations',2500)),2500)))

    def week(self,d):
        target,allowed,forbidden,preferred,ratios=self.common(d); days=max(1,min(7,int(d.get('days',7))))
        return self.send_json(core.weekly_plan(target,days,allowed,forbidden,preferred,ratios,int(d.get('seed',7))))

    def alts(self,d):
        food=d.get('food');
        if food not in core.BYNAME: raise ValueError('Unknown food')
        return self.send_json({'food':food,'alternatives':core.alternatives(food,d.get('forbidden',[]),int(d.get('limit',8)))})

    def log_message(self,fmt,*args):
        if os.environ.get('QUIET')!='1': super().log_message(fmt,*args)

if __name__ == '__main__':
    print(f'Meal Planner {core.VERSION} — listening on 0.0.0.0:{PORT}')
    ThreadingHTTPServer((HOST,PORT),Handler).serve_forever()
