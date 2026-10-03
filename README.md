# إعدادات GitHub الخاصة بكنان

تُطبَّق هذه الإعدادات على أي مستودع عند الطلب. مصدرها `settings.yml`، ويطبّقها `apply.py`.

## الطلب من Claude

اكتب: «طبّق إعدادات الأمان الخاصة بكنان على المستودع `<الاسم>`». يقرأ Claude هذا المستودع، ويشغّل `apply.py`، ويضيف `gitleaks` بـ pull request إن كان المستودع خاصاً.

## التطبيق يدوياً

يحتاج `gh` مسجَّل الدخول، و`uv`:

```bash
uv run apply.py kenanwahbeh/<المستودع> --dry-run      # يعرض ما سيتغير فقط
uv run apply.py kenanwahbeh/<المستودع>                # يطبّق
uv run apply.py kenanwahbeh/<المستودع> --check test   # ويطلب نجاح فحص الـ CI test قبل الدمج
```

بعد إضافة `gitleaks` وSemgrep للمستودع الخاص، أعد التطبيق بـ `--check gitleaks --check semgrep` (ومعهما فحوص الـ CI الأخرى) حتى يمنعا الدمج.

أضف `--check` فقط باسم فحص يظهر فعلاً في الـ CI للمستودع، وإلا لن يُدمج أي pull request. وإن كان للمستودع ruleset باسم `main` يطلب فحوصاً، تبقى فحوصه إن لم تُمرَّر `--check`.

## ما يطبّقه `apply.py`

| الإعداد | المستودع العام | المستودع الخاص |
|---|---|---|
| Dependabot alerts وخريطة الاعتماديات | ✓ | ✓ |
| Dependabot security updates | ✓ | ✓ |
| Secret scanning وpush protection | ✓ | يُجرَّب، ويُستعمل `gitleaks` معه |
| CodeQL (default setup) | ✓ | يُجرَّب، ويُستعمل Semgrep معه |
| حذف الفرع بعد الدمج، والدمج التلقائي | ✓ | ✓ |
| ruleset `main`: لا حذف، لا force push، كل تغيير بـ pull request | ✓ | ✓ |

على المستودع الخاص قد يرفض GitHub الميزتين لأنهما إضافتان مدفوعة (GitHub Secret Protection وGitHub Code Security)، فيطبع `apply.py` السبب ويكمل الباقي.

المستودعات المستثناة من الـ ruleset في `ruleset_exclude`.

## `gitleaks` للمستودع الخاص

1. انسخ `workflows/secrets.yml` إلى `.github/workflows/secrets.yml` في المستودع.
2. شغّل `gitleaks git --redact -v .` محلياً. ما ليس سراً (كلمات سر الاختبارات مثلاً) أضف بصمته (`Fingerprint`) إلى `.gitleaksignore`.
3. أضف الملفين بـ pull request.

## Semgrep للمستودع الخاص

بديل CodeQL المجاني.

1. انسخ `workflows/semgrep.yml` إلى `.github/workflows/semgrep.yml`، واختر حزم القواعد بلغات المستودع (`p/python`، `p/django`، `p/javascript`، `p/typescript`...).
2. شغّل الأمر نفسه محلياً: `uvx semgrep scan --metrics off --error --config <الحزم> .`
3. صحّح ما هو مشكلة فعلاً. وما ليس مشكلة أسكته على سطره بتعليق `nosemgrep: <القاعدة>` مع السبب.
4. أضف الملف بـ pull request.

## ما لا API له

هذه تُضبط من الموقع مرة واحدة للحساب:

- **التحقق بخطوتين:** https://github.com/settings/security
- **الإعدادات الافتراضية للمستودعات الجديدة:** https://github.com/settings/security_analysis. لكل ميزة اضغط **Enable all**، وفعّل **Automatically enable for new repositories**. ويشمل ذلك Grouped security updates وMalware alerts، ولا API لهما.
- **توقيع الـ commits:** على كل جهاز جديد:

  ```bash
  ssh-keygen -t ed25519 -C "<الجهاز>"
  gh ssh-key add ~/.ssh/id_ed25519.pub --title "<الجهاز>"                   # للدخول
  gh auth refresh -h github.com -s admin:ssh_signing_key
  gh ssh-key add ~/.ssh/id_ed25519.pub --type signing --title "<الجهاز> signing"
  git config --global gpg.format ssh
  git config --global user.signingkey ~/.ssh/id_ed25519.pub
  git config --global commit.gpgsign true
  git config --global tag.gpgsign true
  ```

  البريد في `git config user.email` يجب أن يكون مسجّلاً في الحساب، وإلا لا يظهر الـ commit بـ Verified.
