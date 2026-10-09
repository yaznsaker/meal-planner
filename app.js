const $=id=>document.getElementById(id);
const j=async(url,opt={})=>{
  const r=await fetch(url,{headers:{'Content-Type':'application/json',...opt.headers},...opt});
  const d=await r.json();
  if(!r.ok) throw Error(d.error||'خطأ');
  return d;
};

$('calc').onclick=async()=>{
  try{
    const d=await j('/api/calculate',{
      method:'POST',
      body:JSON.stringify({
        weight:+$('weight').value,height:+$('height').value,age:+$('age').value,
        sex:$('sex').value,activity:+$('activity').value,goal:$('goal').value
      })
    });
    $('kcal').value=Math.round(d.calculation.target_kcal);
    $('protein').value=Math.round(d.target.protein);
    $('carbs').value=Math.round(d.target.carbs);
    $('fat').value=Math.round(d.target.fat);
    $('calcOut').textContent=`BMR: ${d.calculation.BMR} | TDEE: ${d.calculation.TDEE} | الهدف: ${d.calculation.target_kcal} kcal`;
  }catch(e){$('calcOut').textContent=e.message}
};
let currentPlan = null;
const payload=()=>{
  kcal:+$('kcal').value,protein:+$('protein').value,
  carbs:+$('carbs').value,fat:+$('fat').value
});

const labels={Breakfast:'الفطور',Lunch:'الغداء',Snack:'وجبة خفيفة',Dinner:'العشاء'};
const foodLabels={
  chicken_breast:'صدر دجاج',lean_beef:'لحم بقري قليل الدهن',eggs:'بيض',tuna:'تونة',
  sardines:'سردين',lentils_cooked:'عدس مطبوخ',rice_cooked:'أرز مطبوخ',
  potato_boiled:'بطاطا مسلوقة',oats:'شوفان',whole_wheat_bread:'خبز قمح كامل',
  banana:'موز',apple:'تفاح',olive_oil:'زيت زيتون',almonds:'لوز',
  yogurt:'لبن',vegetables:'خضار'
};

function renderPlan(data){
  let html='<div class="plan-grid">';
  for(const meal of ['Breakfast','Lunch','Snack','Dinner']){
    const items=data.meals?.[meal]||{};
    html+=`<article class="meal"><h3>${labels[meal]}</h3>`;
    if(Object.keys(items).length===0) html+='<p class="muted">لا توجد أطعمة</p>';
    else for(const [name,g] of Object.entries(items))
      html+=`<div class="food"><span>${foodLabels[name]||name}</span><strong>${g} غ</strong></div>`;
    html+='</article>';
  }
  html+='</div>';
  const t=data.totals||{};
  html+=`<div class="totals"><strong>المجموع:</strong> ${Math.round(t.kcal)} kcal · بروتين ${Math.round(t.protein)}غ · كربوهيدرات ${Math.round(t.carbs)}غ · دهون ${Math.round(t.fat)}غ</div>`;
  return html;
}

week').onclick=async()=>{
  try{
    const d=await j('/api/week',{
      method:'POST',
      body:JSON.string$('plan').onclick=async()=>{
  try{
    currentPlan={
      type:'daily',
      target:payload(),
      plan:await j('/api/plan',{
        method:'POST',
        body:JSON.stringify(payload())
      })
    };
    $('out').innerHTML=renderPlan(currentPlan.plan);
  }catch(e){
    $('out').textContent=e.message;
  }
};
{...payload(),days:+$('days').value})
    });
    $('out').innerHTML=d.days.map((day,i)=>`<section class="day"><h2>اليوم ${i+1}</h2>${renderPlan(day)}</section>`).join('');
  }catch(e){$('out').textContent=e.message}
};

j('/api/health').then(d=>$('status').textContent=d.version).catch(()=>{});
