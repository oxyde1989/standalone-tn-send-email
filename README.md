# 📬 Stand-alone TrueNAS Send Email Script  
*using the built-in `mail.config` data*

---

## 📌 About the project

Starting from Truenas 24.10.10, the `sendemail` function is no longer available, removed for security reason.  
This standalone script provides the ability to send emails and attachments using the TrueNAS native `mail.config`, in the simplest possible way for end users.  
Originally designed to be a wrapper for [Joe's Multi Report](https://github.com/JoeSchmuck/Multi-Report), it also can be used for simplify sending email overall in many other scenarios.  
  
Actually, there are 2 different basic usage methods:

1. Passing `--subject`, `--to_address`, `--mail_body_html` (nor a file path and plain text), plus other optionally args (like attachments, override sender-sendername, ecc).
2. Passing only the full email base64 encoded (nor a file path and plain text) as `--mail_bulk`, trying to emulating the old `sendemail` function, and all the info will be retrieved there.

## 🧰 Guidelines

[Full documentation and guidelines link](https://oxyde1989.github.io/standalone-tn-send-email/)

---

## 🔐 Security Concern

To retrieve TN mail configuration data, at least `READONLY_ADMIN` or `SHARING_ADMIN` roles are needed for the user that run the script.  
**So is highly adviced to only use the script in a secured folder**, not accessible to un-priviliged users, to avoid unexpected behaviour.  
The script will advice you in those scenarios, **so pay attention if some warning are raised on first usage** and fix your dataset permission accordingly.
There are other check that are performed to improve security (attachment black list, avoiding symlink, CRLF injection, ...), any suggestion is welcome and i will do my best to keep things safest and flexible for all.

---

## 🙋‍♂️ For any problem or improvements let me know!

