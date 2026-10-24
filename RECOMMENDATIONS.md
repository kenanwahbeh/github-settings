# سياسة تجهيز مستودعات GitHub

مرجع لما يمكن ضبطه على أي مستودع جديد، وما يغطيه `apply.py` اليوم وما لا يغطيه. مصدره توثيق GitHub (docs.github.com) في تشرين الأول 2026. ما لم أتحقق منه بنفسي مكتوب «غير مؤكد».

الرموز: ✅ مطبَّق في `apply.py` · ➕ موصى به ولم يُطبَّق بعد · 🖐 يدوي (لا API) · ⚖ اختياري حسب الذوق.

## 1. حماية الفرع `main` (ruleset)

| القاعدة | الحالة | السياسة والنطاق |
|---|---|---|
| منع الحذف `deletion` | ✅ | |
| منع force push `non_fast_forward` | ✅ | |
| كل تغيير بـ pull request، بلا موافقات (0) | ✅ | العدد قابل للضبط لكل مستودع؛ لا تعمم صفر موافقات على جميع عملاء المنتج. تبقى الموافقة على الدمج منفصلة عن نتيجة الآلة. |
| فحوص CI مطلوبة `required_status_checks` | ✅ بأسماء فعلية | تُستبدل الأسماء عند --check مع حفظ السياسة الحية وربط المصادر للأسماء الباقية. الفرع يجب أن يكون محدثاً. |
| تواقيع موثّقة `required_signatures` | ✅ | تحققت في ruleset المرجع؛ يعاد التحقق في كل مستودع هدف بعد التطبيق. |
| تاريخ خطي `required_linear_history` | ⚖ | يفرض squash أو rebase فقط. يعطي سجلاً نظيفاً، ويتطلب أن يسمح المستودع بأحدهما. |
| نتائج code scanning `code_scanning` | ✅ قابلة للضبط | CodeQL للعام وفق السياسة الحالية، أخطاء وHigh/Critical؛ يلزم تحليل ناجح على الفرع الافتراضي قبل فرض الأداة. |
| حل تنبيهات الأسرار `secret_scanning` | ⚖ | معاينة عامة (public preview) في التوثيق. |
| `bypass_actors` | ✅ فارغ | حتى المالك لا يدفع مباشرة. وفي الطوارئ تعدّل الـ ruleset من الإعدادات ثم تعيده. |

**ruleset ثانٍ للوسوم (tags)** ✅: يطابق `v*` ويمنع الحذف والتحديث (`deletion` و`update`)، حتى لا يُعاد توجيه إصدار منشور.

## 2. إعدادات المستودع

| الإعداد | الحالة | ملاحظة |
|---|---|---|
| Dependabot alerts + الرسم البياني للاعتماديات | ✅ | مجاني للخاص والعام |
| Dependabot security updates | ✅ | |
| **Dependabot version updates** (`.github/dependabot.yml`) | ✅ قالب | `templates/dependabot.yml`، يُضاف بـ PR. أهمها نظام `github-actions` لتحديث الـ Actions، مع `groups` و`cooldown` لتقليل الضجيج. |
| Secret scanning + push protection | ✅ للعام، يُجرَّب للخاص | إضافة مدفوعة في الخاص، وبديله gitleaks |
| CodeQL (default setup) | ✅ للعام وفق الضبط | الخاص يحتاج أداة وخطة متاحتين؛ يمكن استخدام Semgrep كفحص CI |
| حذف الفرع بعد الدمج، والدمج التلقائي | ✅ | |
| السماح بطريقة دمج واحدة (squash فقط) | ✅ | `allow_squash_merge` و`allow_merge_commit` و`allow_rebase_merge` في `PATCH repos/{repo}` |
| تعطيل ما لا تستعمله (wiki، projects) | ⚖ | `has_wiki` و`has_projects` |
| `SECURITY.md` | ✅ قالب | `templates/SECURITY.md`، يُضاف بـ PR للعام. لا API. |
| Private vulnerability reporting | ✅ للعام فقط | `PUT repos/{repo}/private-vulnerability-reporting` (مؤكد من التوثيق، يتطلب صلاحية admin). |
| Dependency review (action) | ➕ للعام | مدفوع في الخاص |

## 3. GitHub Actions

نقاط نهاية REST موجودة (مؤكدة من التوثيق):

| الإعداد | الطلب | القيمة الموصى بها |
|---|---|---|
| صلاحيات `GITHUB_TOKEN` الافتراضية | `PUT repos/{repo}/actions/permissions/workflow` | `default_workflow_permissions: read` و`can_approve_pull_request_reviews: false` ✅ |
| موافقة تشغيل PR من الخارج | `PUT .../actions/permissions/fork-pr-contributor-approval` | `all_external_contributors` ✅ |
| فرض تثبيت Actions بـSHA | `PUT repos/{repo}/actions/permissions` | مبرمج في المرحلة الأولى؛ يُفعّل حياً بعد دمج الملفات المثبتة وفحصها في المرحلة الثانية. |
| قائمة الـ Actions المسموحة | `PUT .../actions/permissions/selected-actions` | ⚖ |

داخل ملفات الـ workflow:
- اكتب `permissions: contents: read` في أعلى كل ملف (القوالب هنا تفعل ذلك).
- تجنّب `pull_request_target`، وإن اضطررت فلا تسحب كود الـ fork.
- لا أسرار نصية في الملفات، وأدخل القيم الديناميكية في الإخفاء `::add-mask::`.
- لا تستخدم مدخلات `${{ github.event.* }}` داخل `run:` مباشرة (حقن أوامر).

## 4. الحساب (لا API، مرة واحدة) 🖐

- التحقق بخطوتين، والأفضل مفتاح مرور (passkey) أو مفتاح أمان، مع حفظ رموز الاسترداد.
- توقيع commits بمفتاح SSH (خطواته في `README.md`).
- Personal access tokens: استعمل fine-grained فقط، بصلاحية مستودع محدد ومدة قصيرة، وراجعها دورياً من https://github.com/settings/tokens
- راجع مفاتيح SSH والتطبيقات المرخَّصة (OAuth) والـ deploy keys وأزل ما لا تستعمل.
- فعّل الإعدادات الافتراضية للمستودعات الجديدة من https://github.com/settings/security_analysis (مذكور في `README.md`).
- Immutable releases (إصدارات لا تتغير بعد النشر): ميزة جديدة، وصفحة توثيقها لم أستطع قراءتها، فهي **غير مؤكدة**. ابحث عنها في إعدادات المستودع قبل الاعتماد عليها.

## 5. خطوات التطبيق والتحقق

1. شغّل `uv run apply.py <owner/repo> --dry-run` وراجع كل عملية كتابة في المعاينة.
2. تحقّق من أسماء checks في Pull Request حقيقي؛ لا تنسخ أسماء من وثيقة أو من تشغيل قديم.
3. عند تمرير `--check`، اذكر **كل** الفحوص المطلوبة في القائمة النهائية. لا تمرّر فحصاً واحداً على افتراض أن الأداة ستضيفه إلى الفحوص الحية؛ القائمة تُستبدل.
4. بعد التطبيق، افحص صفحة **Settings → Rules → ruleset** وتأكد من القواعد الفعلية، ثم افتح Pull Request تجريبياً للتأكد أن الفحوص المطلوبة تظهر وتمنع الدمج عند فشلها.
5. أضف `dependabot.yml` و`SECURITY.md` (للعام) بـ PR، وراجع عناصر الحساب اليدوية.

لهذا المستودع تحديداً، وبعد تأكيد الأسماء الفعلية، الأمر الكامل هو:

```bash
uv run apply.py kenanwahbeh/github-settings --dry-run --check gitleaks --check semgrep --check "Regression and consistency checks"
uv run apply.py kenanwahbeh/github-settings --check gitleaks --check semgrep --check "Regression and consistency checks"
```

## 6. ما هو مبرمج وما هو مطبّق فعلياً وما بقي

- **في الكود والإعدادات:** يبني `apply.py` قاعدة `required_signatures` عندما يكون `require_signed_commits: true`، ويبني فحوص CI المطلوبة فقط من الأسماء الممررة عبر `--check`.
- **الحالة الحية السابقة:** تحققت التواقيع والفحوص الثلاثة مع strict=true ومصدر GitHub Actions. إعدادات SHA وحل محادثات المراجعة وCode scanning الجديدة تحتاج تطبيق المرحلة الثانية والتحقق، ولا توصف بأنها مفعلة لمجرد وجودها في الملفات.
- **التوقيع:** إعداد مفتاح SSH يشرح طريقة الإعداد فقط؛ لا يثبت أن كل commits التاريخية موقعة. `required_signatures` يفرض شرط التوقيع على التحديثات التي يغطيها ruleset بعد تفعيله، ولا يغيّر توقيعات التاريخ السابق.
- **تثبيت Actions بـSHA:** مراجع القوالب والنسخ العاملة مثبتة، وأزيل استثناء Semgrep للوسوم. فحص دائم في CI يمنع عودة مراجع متحركة. يجب مزامنة القوالب عند تحديث Dependabot قبل دمج التحديث، وتفعيل سياسة المنع بعد وصول الملفات إلى main.
- **غير مؤكد:** توافر/تفعيل immutable releases في الحساب لم يُتحقق منه.
