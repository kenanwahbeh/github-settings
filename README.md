# github-settings — إعدادات GitHub ودليل وكيل البرمجة

هذا المستودع يؤدي وظيفتين منفصلتين:
1. **مستودع مرجعي لإعدادات GitHub**: يطبّق `settings.yml` عبر `apply.py` عند الطلب.
2. **مرجع لقواعد وكيل البرمجة**: يوفّر تعليمات عامة ومعايير للكود والأمان والاختبارات، مع تصور معماري لـ Cloudflare Workers AI.

## نقطة دخول الوكيل

ابدأ بقراءة [AGENTS.md](AGENTS.md) قبل تعديل الكود، ثم اقرأ الوثيقة المرتبطة بالمهمة:

- [قواعد البرمجة](docs/coding-standards.md)
- [خط أساس الأمان](docs/security.md)
- [الاختبارات وCI](docs/testing-and-ci.md)
- [مرجع الأدوات والمستودعات](docs/tooling.md)
- [تصميم وكيل باستخدام Cloudflare Workers AI](docs/cloudflare-workers-ai.md)

هذه القواعد إرشادات عامة؛ تعليمات المشروع نفسه وطلب المستخدم يحددان التفاصيل. خطوات تشغيل المستودع النموذج موثّقة في قسم "المستودع النموذج" أدناه، وهي محايدة لأي أداة وكيل. لا تفترض أن أداة مثبتة أو أن خدمة Cloudflare AI موصولة فعلياً.

## تطبيق إعدادات GitHub

يحتاج التطبيق إلى `gh` مسجّل الدخول و`uv`:

```bash
uv run apply.py kenanwahbeh/<repository> --dry-run
uv run apply.py kenanwahbeh/<repository>
uv run apply.py kenanwahbeh/<repository> --check test
```

ابدأ بـ `--dry-run` لمراجعة التغييرات؛ في هذا الوضع تنفّذ الأداة عمليات القراءة فقط وتعرض عمليات الكتابة دون تنفيذها (يتطلب اتصالاً و`gh` مصادقاً عليه وصلاحيات قراءة). أضف `--check` فقط باسم فحص CI يظهر فعلاً في المستودع؛ الاسم غير الموجود قد يمنع دمج الـ Pull Requests. إذا كان هناك ruleset باسم `main` يطلب فحوصاً، يحافظ التطبيق على الفحوص الحالية عند عدم تمرير `--check`. سياسة ملكية القواعد موثّقة في تعليقات `settings.yml`: الفرع يستثني `required_status_checks` فقط، وقواعد الوسوم تملكها `settings.yml` بالكامل.

**ملاحظة عن قوالب workflows:** `workflows/` هي القوالب التي تُنسخ إلى المستودعات المستهدفة، أما `.github/workflows/` فهي نسخة هذا المستودع العاملة لحماية نفسه بهما. يجب أن يبقى كل زوج متطابقاً؛ فحص `scripts/check-workflows-sync.sh` يمنع الانحراف. إصدارات الأدوات المكتوبة داخل أوامر shell (`GITLEAKS_VERSION`، ونسخة Semgrep في سطر `uvx`) لا يحدّثها Dependabot — تُحدَّث يدوياً في الملفين معاً عند الترقيات.

### المستودع النموذج: خطوات الوكيل الكاملة

إذا طُلب من وكيل البرمجة قراءة هذا المستودع النموذج وتكرار إعداده لمستودع آخر، عليه:

1. تشغيل `apply.py` على المستودع الهدف (`--dry-run` أولاً)، وتمرير `--check <name>` لأسماء فحوص CI تظهر فعلاً في الهدف فقط.
2. للمستودع **الخاص**: إضافة `workflows/secrets.yml` (Gitleaks) و`workflows/semgrep.yml` إلى `.github/workflows/` عبر Pull Request وفق الخطوات أدناه، ثم إعادة التطبيق بـ `--check gitleaks --check semgrep` مع بقية فحوص الهدف.
3. إضافة `templates/dependabot.yml` (باسم `.github/dependabot.yml` مع منظومات المشروع) و`templates/SECURITY.md` (للمستودعات العامة) في نفس الـ Pull Request.
4. الإبلاغ عن بنود "إعدادات حساب لا تتوفر لها API مناسبة" أدناه يدوياً بدل محاولة أتمتتها.

**اختبارات الأداة**: `uv run --with pyyaml python tests/test_apply.py` — بلا شبكة ولا حاجة لـ `gh`. (الأمر المباشر `python3 tests/test_apply.py` يعمل فقط إذا كانت PyYAML متوفرة في البيئة، لأن `apply.py` يستوردها؛ لا توجد ملفات متطلبات مثبّتة في هذا المستودع.)
**فحص التزامن**: `bash scripts/check-workflows-sync.sh` — يتأكد أن `workflows/` و`.github/workflows/` متطابقتان.

## ما الذي تضبطه الأداة؟

| الإعداد | المستودع العام | المستودع الخاص |
|---|---|---|
| Dependabot alerts وخريطة الاعتماديات | نعم | نعم |
| Dependabot security updates | نعم | نعم |
| Secret scanning وpush protection | نعم | قد تتطلب خطة مدفوعة؛ Gitleaks بديل |
| CodeQL default setup | حسب دعم GitHub | قد تتطلب خطة مدفوعة؛ Semgrep بديل |
| حذف الفرع بعد الدمج والدمج التلقائي | نعم | نعم |
| طريقة الدمج | squash فقط | squash فقط |
| ruleset للفرع الافتراضي ووسوم `v*` | نعم | نعم |
| صلاحيات GitHub Actions الافتراضية | قراءة فقط | قراءة فقط |
| Private vulnerability reporting | نعم | غير متاح بهذه السياسة |

القيم الفعلية في [settings.yml](settings.yml)، والتفاصيل والخيارات التي لم تُعتمد في [RECOMMENDATIONS.md](RECOMMENDATIONS.md). المستودعات المذكورة في `ruleset_exclude` مستثناة من ruleset الفرع الافتراضي فقط؛ تبقى بقية الإعدادات وقاعدة الوسوم مطبقة.

## ملفات تُضاف إلى المستودعات المستهدفة عند الحاجة

| الملف الهدف | المصدر داخل هذا المستودع | النطاق |
|---|---|---|
| `.github/workflows/secrets.yml` | `workflows/secrets.yml` | Gitleaks، للمستودعات الخاصة حسب الإعداد |
| `.github/workflows/semgrep.yml` | `workflows/semgrep.yml` | Semgrep، للمستودعات الخاصة حسب الإعداد |
| `.github/dependabot.yml` | `templates/dependabot.yml` | جميع المستودعات؛ أضف منظومة المشروع مثل pip أو npm |
| `SECURITY.md` | `templates/SECURITY.md` | المستودعات العامة حسب الإعداد |

### Gitleaks للمستودع الخاص

1. انسخ `workflows/secrets.yml` إلى `.github/workflows/secrets.yml` في المستودع المستهدف.
2. شغّل `gitleaks git --redact -v .` محلياً.
3. إذا ظهرت نتيجة ليست سراً، أضف بصمتها إلى `.gitleaksignore` مع التحقق من أنها آمنة.
4. أرسل التغييرات عبر Pull Request.

### Semgrep للمستودع الخاص

1. انسخ `workflows/semgrep.yml` إلى `.github/workflows/semgrep.yml`.
2. اختر حزم القواعد المناسبة للغات المستخدمة، مثل `p/python` أو `p/django` أو `p/javascript` أو `p/typescript`.
3. شغّل محلياً، مثلاً: `uvx semgrep scan --metrics off --error --config <الحزم> .`.
4. أصلح النتائج الصحيحة؛ لا تتجاهل نتيجة إلا بعد مراجعتها وتوثيق سبب الاستثناء.

لمشاريع Next.js، أضف إعداد `npm` إلى `.github/dependabot.yml` مع المسار الصحيح، مثل `/agent-web` أو `/`.

### جعل فحوص Gitleaks وSemgrep مطلوبة قبل الدمج

بعد إضافة ملفات الـ workflows إلى المستودع المستهدف، أعد تطبيق قواعد الحماية مع أسماء فحوص CI الفعلية. في هذا القالب اسم مهمة Gitleaks هو `gitleaks` واسم مهمة Semgrep هو `semgrep`:

```bash
uv run apply.py <owner/repo> --check gitleaks --check semgrep
```

أضف أيضًا أسماء الفحوص الأخرى التي يجب أن تمنع الدمج. تحقّق من ظهور هذه الأسماء فعلًا في نتائج Checks الخاصة بطلب الدمج قبل استخدامها؛ الاسم الخاطئ قد يمنع دمج كل طلبات الدمج في المستودع.


## إعدادات حساب لا تتوفر لها API مناسبة في هذا الإجراء

تُراجع هذه الإعدادات يدوياً من GitHub:

- **التحقق بخطوتين:** https://github.com/settings/security. يُفضّل مفتاح مرور أو مفتاح أمان، مع حفظ رموز الاسترداد.
- **Tokens:** استخدم fine-grained tokens لمستودعات وصلاحيات محددة ومدة قصيرة: https://github.com/settings/personal-access-tokens. راجع الرموز القديمة من https://github.com/settings/tokens.
- **المفاتيح والتطبيقات المصرّح لها:** https://github.com/settings/keys وhttps://github.com/settings/applications.
- **الإعدادات الافتراضية لتحليل الأمان للمستودعات الجديدة:** https://github.com/settings/security_analysis. راجع الخيارات المتاحة وفعّل التمكين التلقائي حيث يلائمك.
- **توقيع commits عبر SSH:** اتبع توثيق GitHub الرسمي، وتأكد أن بريد Git مضبوط على عنوان مسجل في الحساب كي يظهر التوقيع كـ Verified.

## مبدأ الأمان وحدود المستودع

لا تمنح وكيل البرمجة صلاحيات غير محدودة. افصل اقتراح التغيير عن تنفيذه، شغّل الفحوص، راجع diff، واجعل الدمج والنشر والعمليات المدمّرة بحاجة إلى موافقة صريحة.

هذا المستودع يوثّق قواعد مقترحة ويحتوي أداة إعدادات GitHub. وجود وثائق Cloudflare Workers AI لا يعني أن الوكيل أو تكامله قد أُنشئ أو نُشر.
