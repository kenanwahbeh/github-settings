# توصيات GitHub لمطوّر يعمل وحده

مرجع لما يمكن ضبطه على أي مستودع جديد، وما يغطيه `apply.py` اليوم وما لا يغطيه. مصدره توثيق GitHub (docs.github.com) في تشرين الأول 2026. ما لم أتحقق منه بنفسي مكتوب «غير مؤكد».

الرموز: ✅ مطبَّق في `apply.py` · ➕ موصى به ولم يُطبَّق بعد · 🖐 يدوي (لا API) · ⚖ اختياري حسب الذوق.

## 1. حماية الفرع `main` (ruleset)

| القاعدة | الحالة | ملاحظة لمن يعمل وحده |
|---|---|---|
| منع الحذف `deletion` | ✅ | |
| منع force push `non_fast_forward` | ✅ | |
| كل تغيير بـ pull request، بلا موافقات (0) | ✅ | الموافقة على عملك مستحيلة وحدك، فتبقى 0. فائدة الـ PR هنا هي تشغيل الفحوص قبل الدمج. |
| فحوص CI مطلوبة `required_status_checks` | ✅ بـ `--check` | باسم فحص يظهر فعلاً، وإلا يتعطل الدمج. |
| تواقيع موثّقة `required_signatures` | ✅ | أنت توقّع كل commits أصلاً (README). commits واجهة GitHub وDependabot موقّعة من GitHub فلا تنكسر. أما commits وكلاء الذكاء الاصطناعي على جهازك فتُوقَّع بمفتاحك. |
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

## 5. ترتيب العمل لمستودع جديد

1. `uv run apply.py kenanwahbeh/<repo> --dry-run` ثم بدون `--dry-run`.
2. مستودع خاص: أضف `secrets.yml` و`semgrep.yml` بـ PR، ثم أعد التطبيق مع `--check gitleaks --check semgrep` وفحوص CI الأخرى.
3. أضف `dependabot.yml` و`SECURITY.md` (العام) بـ PR.
4. راجع القائمة اليدوية أعلاه إن كان جهازاً أو حساباً جديداً.

## 6. ما نُفِّذ وما بقي

نُفِّذ في `apply.py` و`settings.yml`: التواقيع، ruleset الوسوم، صلاحيات الـ Actions وموافقة الـ forks، طريقة دمج واحدة (squash)، Private vulnerability reporting للعام. وأُضيف قالبا `templates/dependabot.yml` و`templates/SECURITY.md`.

لم يُنفَّذ عمداً: `sha_pinning_required` (يتعارض مع قالب Semgrep الذي يقبل التثبيت بالوسم)، و`required_linear_history` (squash فقط يعطي النتيجة نفسها تقريباً).

غير مؤكد: Immutable releases.
