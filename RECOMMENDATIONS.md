# توصيات GitHub لمطوّر يعمل وحده

مرجع لما يمكن ضبطه على أي مستودع جديد، وما يغطيه `apply.py` اليوم وما لا يغطيه. مصدره توثيق GitHub (docs.github.com) في تشرين الأول 2026. ما لم أتحقق منه بنفسي مكتوب «غير مؤكد».

الرموز: ✅ مطبَّق في `apply.py` · ➕ موصى به ولم يُطبَّق بعد · 🖐 يدوي (لا API) · ⚖ اختياري حسب الذوق.

## 1. حماية الفرع `main` (ruleset)

| القاعدة | الحالة | ملاحظة لمن يعمل وحده |
|---|---|---|
| منع الحذف `deletion` | ✅ | |
| منع force push `non_fast_forward` | ✅ | |
| كل تغيير بـ pull request، بلا موافقات (0) | ✅ | الموافقة على عملك مستحيلة وحدك، فتبقى 0. فائدة الـ PR هنا هي تشغيل الفحوص قبل الدمج. |
| فحوص CI مطلوبة `required_status_checks` | تتطلب مزامنة حية | `apply.py --check` يستبدل قائمة الفحوص كاملة؛ يجب تمرير كل الأسماء المطلوبة والتحقق منها في Pull Request. في التدقيق الحي الأخير لم يكن فحص الاختبارات/الاتساق مطلوباً. |
| تواقيع موثّقة `required_signatures` | مفعّلة في الحالة المطلوبة؛ غير متحققة في ruleset الحي | `settings.yml` و`apply.py` يطلبان القاعدة، لكن التدقيق الحي لم يجدها في ruleset `main`. إعداد مفتاح التوقيع في README لا يثبت أن كل commit موقّع، والقاعدة لا تعيد توقيع التاريخ السابق؛ يجب تطبيقها والتحقق منها. |
| تاريخ خطي `required_linear_history` | ⚖ | يفرض squash أو rebase فقط. يعطي سجلاً نظيفاً، ويتطلب أن يسمح المستودع بأحدهما. |
| نتائج code scanning `code_scanning` | ➕ للعام فقط | يمنع الدمج إن وُجدت ثغرة بدرجة محددة. CodeQL مجاني للمستودع العام فقط. |
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
| CodeQL (default setup) | ✅ للعام، يُجرَّب للخاص | بديله في الخاص Semgrep |
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
| فرض تثبيت الـ Actions بـ SHA | `PUT repos/{repo}/actions/permissions` (`sha_pinning_required`) | ⚖ انتبه: قالب Semgrep هنا يقبل التثبيت بالوسم عمداً. فعّله فقط إن ثبّتَّ بالـ SHA وتركت Dependabot يحدّثها. |
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
- **حالة GitHub الحية التي فُحصت في 2026-10-24:** ruleset `main` لا يحتوي `required_signatures`؛ كما أن `Regression and consistency checks` ليس ضمن الفحوص المطلوبة، رغم نجاحه في التشغيل. كانت الفحوص المطلوبة الظاهرة هي `gitleaks` و`semgrep`. لذلك لا يصح وصف هاتين الحمايتين بأنهما مطبقتان بالكامل قبل إعادة التطبيق والتحقق.
- **التوقيع:** إعداد مفتاح SSH يشرح طريقة الإعداد فقط؛ لا يثبت أن كل commits التاريخية موقعة. `required_signatures` يفرض شرط التوقيع على التحديثات التي يغطيها ruleset بعد تفعيله، ولا يغيّر توقيعات التاريخ السابق.
- **تثبيت Actions بـ SHA:** لم يُفرض حتى الآن؛ القوالب تقبل وسوم الإصدارات وتستثني قاعدة Semgrep الخاصة بالوسوم المتحركة. هذا قرار مخاطرة مقصود لتسهيل التحديث، وليس ضماناً مكافئاً للتثبيت بـ SHA. إذا تقرر فرض SHA لاحقاً، يجب تثبيت كل Actions في القوالب والنسخ العاملة وتحديث Dependabot وفحوص الاتساق معاً.
- **غير مؤكد:** توافر/تفعيل immutable releases في الحساب لم يُتحقق منه.
