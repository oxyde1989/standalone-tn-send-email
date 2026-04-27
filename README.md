# 📬 Standalone TrueNAS Send Email Script  
*using the built-in `mail.config` data*

## 📌 About the project

Starting from TrueNAS 24.10.10, the sendemail builtin function is no longer available (removed for security reason).

The `mail.send` method is still available, but is quite trivial to use due to some payload limitations/encoding/ecc.

This standalone script provides the ability to send emails and attachments using the TrueNAS native `mail.config`, in the simplest possible way, without giving up on some more advanced features that are not natively available.

Originally designed to be a wrapper for [Joe's Multi Report](https://github.com/JoeSchmuck/Multi-Report), it also can be used to simplify sending email overall in many other scenarios.

## ⚠️ Breaking change (vNext)

Version 1.90 introduces a **change in email body handling**.

### Before
```
--mail_body_html
```
### Now

```
--mail_body
--mail_body_type (html | plain > default html)
```

For backward compatibility:
- --mail_body_html is still supported, but being deprecated, will be removed in a future release
- If both --mail_body and --mail_body_html are somehow provided, --mail_body takes precedence.
- Custom templates should be aligned, replacing the old `{html_content}` with `{body_content}`, because `{html_content}` variable will be removed in future relase 

## 🧰 Guidelines

TLDR, there are 2 differents basic usage methods:

1. Passing `--subject`, `--to_address`, `--mail_body` (either a file path and plain text), plus other optionally args (like mail_body_type, attachments, sender override logics, email template).
2. Passing only the full email base64 encoded (nor a file path and plain text) as `--mail_bulk`, trying to emulating the old `sendemail` function, and all the info will be retrieved there.

[Read the full documentation](https://oxyde1989.github.io/standalone-tn-send-email/) to discover all the script's capabilities
- attachments
- sender override logics
- prebuilt templates
- custom templates
- debugging
- update strategy
- test mode

and some usefull report snipplets ready to use

## 🔐 Security Concern

To retrieve TN mail configuration data, at least `READONLY_ADMIN` or `SHARING_ADMIN` roles are needed for the user that run the script.  
**So is highly adviced to only use the script in a secured folder**, not accessible to un-priviliged users, to avoid unexpected behaviour.  
The script will advice you in those scenarios, **so pay attention if some warning are raised on first usage** and fix your dataset permission accordingly.
There are other check that are performed to improve security (attachment black list, avoiding symlink, CRLF injection, ...), any suggestion is welcome and i will do my best to keep things safest and flexible for all.

---

## 🙋‍♂️ For any problem or improvements let me know!

