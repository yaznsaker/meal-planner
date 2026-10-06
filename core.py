from dataclasses import dataclass
from typing import Tuple, Dict, List, Optional
import argparse, json, math, random

VERSION = '1.1-production'

@dataclass(frozen=True)
class Food:
    name: str
    group: str
    kcal: float
    protein: float
    carbs: float
    fat: float
    min_g: int
    max_g: int
    step_g: int
    tags: Tuple[str, ...] = ()

FOODS = [
 Food('chicken_breast','protein',165,31,0,3.6,80,300,10,('lean','lunch','dinner')),
 Food('lean_beef','protein',170,26,0,7,80,250,10,('lean','lunch','dinner')),
 Food('eggs','protein',143,12.6,.7,9.5,50,200,50,('breakfast','protein','dinner')),
 Food('tuna','protein',132,29,0,1,60,250,10,('lean','lunch','dinner')),
 Food('sardines','protein',208,25,0,11,60,250,10,('omega3','lunch','dinner')),
 Food('lentils_cooked','plant',116,9,20,.4,100,350,50,('plant','fiber','lunch','dinner')),
 Food('rice_cooked','carb',130,2.7,28,.3,100,350,25,('carb','lunch','dinner')),
 Food('potato_boiled','carb',87,1.9,20,.1,100,400,25,('carb','lunch','dinner')),
 Food('oats','carb',389,16.9,66.3,6.9,30,120,5,('breakfast','fiber')),
 Food('whole_wheat_bread','carb',247,13,41,4.2,40,180,20,('breakfast','carb','lunch')),
 Food('banana','mixed',89,1.1,22.8,.3,50,250,25,('breakfast','snack')),
 Food('apple','mixed',52,.3,14,.2,50,300,25,('snack','fiber')),
 Food('olive_oil','fat',884,0,0,100,5,30,5,('fat','lunch','dinner')),
 Food('almonds','fat',579,21.2,21.6,49.9,10,40,5,('fat','snack','breakfast')),
 Food('yogurt','mixed',61,3.5,4.7,3.3,100,300,50,('breakfast','snack')),
 Food('vegetables','veg',35,1.5,7,.2,100,500,50,('veg','lunch','dinner')),
]
BYNAME={f.name:f for f in FOODS}
MEALS=('Breakfast','Lunch','Snack','Dinner')
DEFAULT_RATIOS=(.25,.30,.15,.30)
DEFAULT_TARGET={'kcal':2290.0,'protein':162.0,'carbs':248.5,'fat':72.0}


def _finite(x, name):
    x=float(x)
    if not math.isfinite(x): raise ValueError(f'{name} must be finite')
    return x

def bmr_mifflin(weight_kg,height_cm,age,sex):
    weight_kg=_finite(weight_kg,'weight'); height_cm=_finite(height_cm,'height'); age=_finite(age,'age')
    sex=str(sex).lower()
    if not (20<=weight_kg<=400 and 100<=height_cm<=230 and 10<=age<=100): raise ValueError('Profile values are outside supported ranges')
    if sex not in ('male','female'): raise ValueError('Invalid sex')
    return 10*weight_kg+6.25*height_cm-5*age+(5 if sex=='male' else -161)

def tdee(bmr,activity_factor):
    bmr=_finite(bmr,'BMR'); activity_factor=_finite(activity_factor,'activity')
    if not 1.0<=activity_factor<=2.5: raise ValueError('Activity factor must be between 1.0 and 2.5')
    return bmr*activity_factor

def calorie_target(tdee_value,goal,deficit_pct=20,surplus_pct=10):
    tdee_value=_finite(tdee_value,'TDEE'); goal=str(goal).lower()
    deficit_pct=_finite(deficit_pct,'deficit_pct'); surplus_pct=_finite(surplus_pct,'surplus_pct')
    if not 0<=deficit_pct<=50 or not 0<=surplus_pct<=50: raise ValueError('Adjustment percentages must be between 0 and 50')
    if goal in ('lose','loss','weight_loss'): return tdee_value*(1-deficit_pct/100)
    if goal in ('gain','weight_gain'): return tdee_value*(1+surplus_pct/100)
    if goal=='maintain': return tdee_value
    raise ValueError('Invalid goal')

def macro_targets(kcal,weight_kg,protein_gkg=1.8,fat_gkg=.8):
    kcal=_finite(kcal,'kcal'); weight_kg=_finite(weight_kg,'weight'); protein_gkg=_finite(protein_gkg,'protein_gkg'); fat_gkg=_finite(fat_gkg,'fat_gkg')
    if min(kcal,weight_kg,protein_gkg,fat_gkg)<=0: raise ValueError('Macro inputs must be positive')
    protein=weight_kg*protein_gkg; fat=weight_kg*fat_gkg
    carbs=(kcal-protein*4-fat*9)/4
    if carbs<0: raise ValueError('Protein/fat targets exceed available calories')
    return {'kcal':kcal,'protein':protein,'carbs':carbs,'fat':fat}

def nutrients(name,g):
    if name not in BYNAME: raise ValueError(f'Unknown food: {name}')
    f=BYNAME[name]; x=float(g)/100
    return {k:getattr(f,k)*x for k in ('kcal','protein','carbs','fat')}

def totals(items):
    out={k:0.0 for k in ('kcal','protein','carbs','fat')}
    for n,g in items.items():
        for k,v in nutrients(n,g).items(): out[k]+=v
    return out

def valid_amount(name,g):
    f=BYNAME[name]; return f.min_g<=g<=f.max_g and (g-f.min_g)%f.step_g==0

def nearest_valid(name,g):
    f=BYNAME[name]; g=max(f.min_g,min(f.max_g,float(g))); q=round((g-f.min_g)/f.step_g); return int(f.min_g+q*f.step_g)

def _allowed(allowed,forbidden):
    forbidden=set(forbidden or [])
    unknown=[x for x in forbidden if x not in BYNAME]
    if unknown: raise ValueError('Unknown forbidden foods: '+', '.join(unknown))
    if allowed is None: names=list(BYNAME)
    else:
        names=list(dict.fromkeys(allowed)); unknown=[x for x in names if x not in BYNAME]
        if unknown: raise ValueError('Unknown allowed foods: '+', '.join(unknown))
    names=[x for x in names if x not in forbidden]
    if not names: raise ValueError('No foods remain after restrictions')
    return names

def _meal_candidates(meal,names):
    tag=meal.lower()
    return [n for n in names if tag in BYNAME[n].tags] or names

def _score(items,target):
    t=totals(items); return sum(((t[k]-target[k])/max(target[k],1))**2 for k in ('kcal','protein','carbs','fat'))

def optimize_daily(target, allowed=None, forbidden=None, preferred=None, ratios=DEFAULT_RATIOS, seed=7, iterations=2500):
    names=_allowed(allowed,forbidden); preferred=[x for x in (preferred or []) if x in names]
    if len(ratios)!=4 or any(float(x)<=0 for x in ratios): raise ValueError('ratios must contain four positive values')
    s=sum(ratios); ratios=tuple(float(x)/s for x in ratios)
    rng=random.Random(seed); best=None
    # Start with meal-oriented random food selection, then optimize gram amounts.
    for _ in range(max(100,min(int(iterations),10000))):
        items={}
        for i,meal in enumerate(MEALS):
            pool=_meal_candidates(meal,names)
            if preferred and rng.random()<.35: pool=[x for x in preferred if x in pool] or preferred
            # each meal gets 2-4 foods; ensure a protein source when possible
            picks=[]
            if any(BYNAME[x].group=='protein' for x in pool): picks.append(rng.choice([x for x in pool if BYNAME[x].group=='protein']))
            while len(picks)<min(3,len(pool)):
                x=rng.choice(pool)
                if x not in picks: picks.append(x)
            meal_target={k:target[k]*ratios[i] for k in target}
            for n in picks:
                f=BYNAME[n]
                desired=meal_target['kcal']/(f.kcal/100)/max(1,len(picks))
                items[n]=nearest_valid(n,desired)
        # Local random improvements.
        current=_score(items,target)
        for _j in range(8):
            n=rng.choice(list(items)); f=BYNAME[n]; old=items[n]
            new=nearest_valid(n,old+rng.choice((-2,-1,1,2))*f.step_g)
            items[n]=new
            sc=_score(items,target)
            if sc<=current: current=sc
            else: items[n]=old
        if best is None or current<best[0]: best=(current,items.copy())
    return best[1]

def meal_targets(target,ratios=DEFAULT_RATIOS):
    if len(ratios)!=4: raise ValueError('ratios must contain four values')
    s=sum(ratios)
    if s<=0: raise ValueError('ratios sum must be positive')
    r=[x/s for x in ratios]
    return [{k:target[k]*r[i] for k in target} for i in range(4)]

def distribute(items,ratios=DEFAULT_RATIOS):
    # Distribute foods across compatible meals while keeping all four meals usable.
    out={m:{} for m in MEALS}

    total_target={
        k:sum(nutrients(n,g)[k] for n,g in items.items())
        for k in ('kcal','protein','carbs','fat')
    }
    targets=meal_targets(total_target,ratios)
    current=[0.0,0.0,0.0,0.0]

    def meal_index(name):
        return MEALS.index(name)

    remaining=[]

    # Foods that belong to only one meal are fixed first.
    for n,g in items.items():
        compatible=[m for m in MEALS if m.lower() in BYNAME[n].tags]

        if len(compatible)==1:
            i=meal_index(compatible[0])
            out[compatible[0]][n]=g
            current[i]+=nutrients(n,g)['kcal']
        else:
            remaining.append((n,g,compatible))

    # Distribute foods with multiple possible meals
    # toward the meal that is furthest below its calorie target.
    for n,g,compatible in sorted(
        remaining,
        key=lambda x:-nutrients(x[0],x[1])['kcal']
    ):
        kcal=nutrients(n,g)['kcal']
        choices=compatible or ['Lunch']

        i=min(
            (meal_index(m) for m in choices),
            key=lambda j:current[j]/max(targets[j]['kcal'],1)
        )

        out[MEALS[i]][n]=g
        current[i]+=kcal

    # Guarantee that dinner is represented whenever
    # there is at least one dinner-compatible food.
    if not out['Dinner']:
        candidates=[]

        for m in ('Lunch','Breakfast','Snack'):
            for n,g in out[m].items():
                if 'dinner' in BYNAME[n].tags:
                    candidates.append(
                        (nutrients(n,g)['kcal'],m,n,g)
                    )

        if candidates:
            _,m,n,g=min(candidates)
            del out[m][n]
            out['Dinner'][n]=g

    return out    
    def alternativesfoodforbiddenonelimit=8):
    if food not in BYNAME: raise ValueError('Unknown food')
    forbidden=set(forbidden or [])
    if any(x not in BYNAME for x in forbidden): raise ValueError('Unknown forbidden food')
    f=BYNAME[food]
    scored=[]
    for x in FOODS:
        if x.name==food or x.name in forbidden: continue
        # Favor same group and similar protein/fat profile.
        group=0 if x.group==f.group else 1
        macro=abs(x.protein-f.protein)/max(f.protein,1)+abs(x.fat-f.fat)/max(f.fat,1)
        scored.append((group+macro,x.name))
    return [x for _,x in sorted(scored)[:max(1,min(int(limit),20))]]

def validate(plan,target,tolerance=.12):
    t=totals(plan)
    errors={}
    for k in ('kcal','protein','carbs','fat'):
        if abs(t[k]-target[k])/max(target[k],1)>tolerance: errors[k]=round(t[k]-target[k],2)
    return {'valid':not errors,'totals':{k:round(v,2) for k,v in t.items()},'errors':errors}

def build_plan(target,allowed=None,forbidden=None,preferred=None,ratios=DEFAULT_RATIOS,seed=7,iterations=2500):
    target={k:_finite(target[k],k) for k in ('kcal','protein','carbs','fat')}
    if any(v<=0 for v in target.values()): raise ValueError('Targets must be positive')
    items=optimize_daily(target,allowed,forbidden,preferred,ratios,seed,iterations)
    meals=distribute(items,ratios)
    return {'version':VERSION,'target':{k:round(v,1) for k,v in target.items()},'foods':{n:int(g) for n,g in items.items()},'meals':{m:{n:int(g) for n,g in d.items()} for m,d in meals.items()},'totals':{k:round(v,1) for k,v in totals(items).items()},'validation':validate(items,target)}

def weekly_plan(target,days=7,allowed=None,forbidden=None,preferred=None,ratios=DEFAULT_RATIOS,seed=7):
    days=max(1,min(7,int(days))); return {'version':VERSION,'days':[build_plan(target,allowed,forbidden,preferred,ratios,seed+i,1800) for i in range(days)]}

def save(data,path):
    with open(path,'w',encoding='utf-8') as f: json.dump(data,f,ensure_ascii=False,indent=2)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--output',default='meal_plan.json'); a=p.parse_args(); save(build_plan(DEFAULT_TARGET),a.output); print(json.dumps(build_plan(DEFAULT_TARGET),ensure_ascii=False,indent=2))

if __name__=='__main__': main()
