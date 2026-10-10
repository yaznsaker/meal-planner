'use strict';

const $ = id => document.getElementById(id);

let currentPlan = null;

const j = async (url, opt = {}) => {
  const response = await fetch(url, {
    headers: {
      'Content-Type': 'application/json',
      ...opt.headers
    },
    ...opt
  });

  let data;

  try {
    data = await response.json();
  } catch {
    throw new Error('تعذر قراءة استجابة الخادم.');
  }

  if (!response.ok) {
    throw new Error(data.error || 'حدث خطأ أثناء تنفيذ الطلب.');
  }

  return data;
};

// قراءة أهداف السعرات والعناصر الغذائية
const payload = () => ({
  kcal: Number($('kcal').value),
  protein: Number($('protein').value),
  carbs: Number($('carbs').value),
  fat: Number($('fat').value)
});

// التحقق من صحة الأهداف
function validateTargets(target) {
  return Object.values(target).every(
    value => Number.isFinite(value) && value > 0
  );
}

// تسميات الوجبات بالعربية
const labels = {
  Breakfast: 'الفطور',
  Lunch: 'الغداء',
  Snack: 'وجبة خفيفة',
  Dinner: 'العشاء'
};

// أسماء الأطعمة بالعربية
const foodLabels = {
  chicken_breast: 'صدر دجاج',
  lean_beef: 'لحم بقري قليل الدهن',
  eggs: 'بيض',
  tuna: 'تونة',
  sardines: 'سردين',
  lentils_cooked: 'عدس مطبوخ',
  rice_cooked: 'أرز مطبوخ',
  potato_boiled: 'بطاطا مسلوقة',
  oats: 'شوفان',
  whole_wheat_bread: 'خبز قمح كامل',
  banana: 'موز',
  apple: 'تفاح',
  olive_oil: 'زيت زيتون',
  almonds: 'لوز',
  yogurt: 'لبن',
  vegetables: 'خضار'
};

// تنسيق الأرقام
function number(value) {
  const result = Number(value);

  return Number.isFinite(result)
    ? Math.round(result)
    : 0;
}

// عرض خطة الوجبات
function renderPlan(data) {
  if (!data || typeof data !== 'object') {
    throw new Error('بيانات خطة الوجبات غير صحيحة.');
  }

  const meals = data.meals || {};
  let html = '<div class="plan-grid">';

  for (const meal of [
    'Breakfast',
    'Lunch',
    'Snack',
    'Dinner'
  ]) {
    const items = meals[meal] || {};

    html += `
      <article class="meal">
        <h3>${labels[meal]}</h3>
    `;

    if (Object.keys(items).length === 0) {
      html += '<p class="muted">لا توجد أطعمة في هذه الوجبة.</p>';
    } else {
      for (const [name, grams] of Object.entries(items)) {
        html += `
          <div class="food">
            <span>${foodLabels[name] || name}</span>
            <strong>${number(grams)} غ</strong>
          </div>
        `;
      }
    }

    html += '</article>';
  }

  html += '</div>';

  const totals = data.totals || {};

  html += `
    <div class="totals">
      <strong>المجموع اليومي:</strong>
      ${number(totals.kcal)} سعرة حرارية
      · بروتين ${number(totals.protein)} غ
      · كربوهيدرات ${number(totals.carbs)} غ
      · دهون ${number(totals.fat)} غ
    </div>
  `;

  if (data.validation && !data.validation.valid) {
    html += `
      <p class="muted">
        ملاحظة: قد تختلف القيم الغذائية الفعلية عن الأهداف المحددة.
      </p>
    `;
  }

  return html;
}

// حساب الاحتياجات اليومية
$('calc').onclick = async () => {
  const profile = {
    weight: Number($('weight').value),
    height: Number($('height').value),
    age: Number($('age').value),
    sex: $('sex').value,
    activity: Number($('activity').value),
    goal: $('goal').value
  };

  if (
    !Number.isFinite(profile.weight) ||
    !Number.isFinite(profile.height) ||
    !Number.isFinite(profile.age) ||
    profile.weight < 20 ||
    profile.weight > 400 ||
    profile.height < 100 ||
    profile.height > 230 ||
    profile.age < 10 ||
    profile.age > 100
  ) {
    $('calcOut').textContent =
      'يرجى إدخال وزن وطول وعمر صحيح.';
    return;
  }

  $('calcOut').textContent = 'جارٍ حساب الاحتياجات...';

  try {
    const data = await j('/api/calculate', {
      method: 'POST',
      body: JSON.stringify(profile)
    });

    $('kcal').value = number(
      data.calculation.target_kcal
    );

    $('protein').value = number(
      data.target.protein
    );

    $('carbs').value = number(
      data.target.carbs
    );

    $('fat').value = number(
      data.target.fat
    );

    $('calcOut').textContent =
      `معدل الأيض الأساسي BMR: ${number(data.calculation.BMR)} سعرة` +
      ` | الاحتياج اليومي TDEE: ${number(data.calculation.TDEE)} سعرة` +
      ` | السعرات المستهدفة: ${number(data.calculation.target_kcal)} سعرة`;
  } catch (error) {
    $('calcOut').textContent = error.message;
  }
};

// إنشاء خطة يومية
$('plan').onclick = async () => {
  const target = payload();

  if (!validateTargets(target)) {
    $('out').textContent =
      'يرجى إدخال أهداف صحيحة للسعرات والبروتين والكربوهيدرات والدهون.';
    return;
  }

  $('out').textContent = 'جارٍ إنشاء الخطة اليومية...';

  try {
    const plan = await j('/api/plan', {
      method: 'POST',
      body: JSON.stringify(target)
    });

    currentPlan = {
      type: 'daily',
      target,
      plan
    };

    $('out').innerHTML = renderPlan(plan);
  } catch (error) {
    currentPlan = null;
    $('out').textContent = error.message;
  }
};

// إنشاء خطة أسبوعية
$('week').onclick = async () => {
  const target = payload();
  const days = Number($('days').value);

  if (!validateTargets(target)) {
    $('out').textContent =
      'يرجى إدخال أهداف صحيحة للسعرات والعناصر الغذائية.';
    return;
  }

  if (!Number.isInteger(days) || days < 1 || days > 7) {
    $('out').textContent =
      'يرجى اختيار عدد أيام من يوم إلى سبعة أيام.';
    return;
  }

  $('out').textContent = 'جارٍ إنشاء الخطة الأسبوعية...';

  try {
    const data = await j('/api/week', {
      method: 'POST',
      body: JSON.stringify({
        ...target,
        days
      })
    });

    if (!Array.isArray(data.days) || data.days.length === 0) {
      throw new Error('لم يُرجع الخادم أي خطط.');
    }

    currentPlan = {
      type: 'weekly',
      target,
      days: data.days.length,
      plans: data.days
    };

    $('out').innerHTML = data.days
      .map((day, index) => `
        <section class="day">
          <h2>اليوم ${index + 1}</h2>
          ${renderPlan(day)}
        </section>
      `)
      .join('');
  } catch (error) {
    currentPlan = null;
    $('out').textContent = error.message;
  }
};

// طباعة الخطة الحالية
$('print').onclick = () => {
  if (!currentPlan) {
    alert('أنشئ خطة يومية أو أسبوعية أولاً.');
    return;
  }

  window.print();
};

// تصدير الخطة الحالية إلى ملف JSON
$('export').onclick = () => {
  if (!currentPlan) {
    alert('أنشئ خطة يومية أو أسبوعية أولاً.');
    return;
  }

  const exportData = {
    app: 'Meal Planner',
    version: '1.1-production',
    exportedAt: new Date().toISOString(),
    ...currentPlan
  };

  const blob = new Blob(
    [JSON.stringify(exportData, null, 2)],
    { type: 'application/json;charset=utf-8' }
  );

  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');

  link.href = url;

  link.download = currentPlan.type === 'weekly'
    ? 'meal-plan-weekly.json'
    : 'meal-plan-daily.json';

  document.body.appendChild(link);
  link.click();
  link.remove();

  setTimeout(() => URL.revokeObjectURL(url), 1000);
};

// عرض إصدار الخادم
j('/api/health')
  .then(data => {
    if (data.version) {
      $('status').textContent = data.version;
    }
  })
  .catch(() => {
    $('status').textContent = 'v1.1';
  });
