const const $=id=>document.getElementById(id);

const j=async(url,opt={})=>{
  const r=await fetch(url,{headers:{'Content-Type':'application/json'},...opt});
  const d=await r.json();
  if(!r.ok) throw Error(d.error||'حدث خطأ');
  return d;
};

const foodNames={
  eggs:'البيض',
  oats:'الشوفان',
  almonds:'اللوز',
  sardines:'السردين',
  whole_wheat_bread:'خبز القمح الكامل',
  potato_boiled:'البطاطا المسلوقة',
  yogurt:'اللبن',
  apple:'التفاح',
  banana:'الموز',
  tuna:'التونة',
  rice_cooked:'الأرز المطبوخ',
  lean_beef:'لحم بقري قليل الدهن',
  vegetables:'الخضار',
  lentils_cooked:'العدس المطبوخ',
  chicken_breast:'صدر الدجاج'
};

const mealNames={
  Breakfast:'الفطور',
  Lunch:'الغداء',
  Snack:'وجبة خفيفة',
  Dinner:'العشاء'
};

const foodName=k=>foodNames[k]||k;

const formatNumber=n=>{
  const x=Number(n);
  return Number.isInteger(x)?x:x.toFixed(1);
};

const mealHTML=(name,foods)=>{
  const entries=Object.entries(foods||{});
  if(!entries.length) return '';

  return `
    <div class="meal">
      <h3>${mealNames[name]||name}</h3>
      <ul>
        ${entries.map(([food,g])=>
          `<li><span>${foodName(food)}</span><strong>${formatNumber(g)} غ</strong></li>`
        ).join('')}
      </ul>
    </div>
  `;
};

const dayHTML=(day,index)=>{
  const meals=Object.entries(day.meals||{})
    .map(([name,foods])=>mealHTML(name,foods))
    .join('');

  const t=day.totals||{};

  return `
    <div class="day-card">
      <h2>اليوم ${index+1}</h2>

      <div class="target">
        <div><b>السعرات</b><span>${formatNumber(t.kcal)} kcal</span></div>
        <div><b>البروتين</b><span>${formatNumber(t.protein)} غ</span></div>
        <div><b>الكربوهيدرات</b><span>${formatNumber(t.carbs)} غ</span></div>
        <div><b>الدهون</b><span>${formatNumber(t.fat)} غ</span></div>
      </div>

      <div class="meals">
        ${meals || '<p>لا توجد وجبات مسجلة لهذا اليوم.</p>'}
      </div>
    </div>
  `;
};

const renderPlan=data=>{
  const day=data.days?data.days[0]:data;
  $('out').innerHTML=dayHTML(day,0);
};

const renderWeek=data=>{
  const days=data.days||[];
  $('out').innerHTML=days.length
    ? days.map((day,i)=>dayHTML(day,i)).join('')
    : '<p>لم يتم إنشاء خطة أسبوعية.</p>';
};

$('calc').onclick=async()=>{
  try{
    const d=await j('/api/calculate',{
      method:'POST',
      body:JSON.stringify({
        weight:+$('weight').value,
        height:+$('height').value,
        age:+$('age').value,
        sex:$('sex').value,
        activity:+$('activity').value,
        goal:$('goal').value
      })
    });

    $('kcal').value=Math.round(d.calculation.target_kcal);
    $('protein').value=Math.round(d.target.protein);
    $('carbs').value=Math.round(d.target.carbs);
    $('fat').value=Math.round(d.target.fat);

    $('calcOut').textContent=
      `BMR: ${d.calculation.BMR} | TDEE: ${d.calculation.TDEE} | الهدف: ${d.calculation.target_kcal} kcal`;
  }catch(e){
    $('calcOut').textContent=e.message;
  }
};

const payload=()=>({
  kcal:+$('kcal').value,
  protein:+$('protein').value,
  carbs:+$('carbs').value,
  fat:+$('fat').value
});

$('plan').onclick=async()=>{
  try{
    $('out').textContent='جاري إنشاء الخطة...';

    const data=await j('/api/plan',{
      method:'POST',
      body:JSON.stringify(payload())
    });

    renderPlan(data);
  }catch(e){
    $('out').textContent=e.message;
  }
};

$('week').onclick=async()=>{
  try{
    $('out').textContent='جاري إنشاء الخطة الأسبوعية...';

    const data=await j('/api/week',{
      method:'POST',
      body:JSON.stringify({
        ...payload(),
        days:+$('days').value
      })
    });

    renderWeek(data);
  }catch(e){
    $('out').textContent=e.message;
  }
};

j('/api/health')
  .then(d=>$('status').textContent=d.version)
  .catch(()=>{});
