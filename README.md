# 📬 Stand-alone TrueNAS Send Email Script  
*using the built-in `mail.config` data*

---

## 📌 What this script do

Starting from Truenas 24.10.10, the `sendemail` function is no longer available, removed for security reason.  
This standalone script provides the ability to send emails and attachments using the TrueNAS native `mail.config`, in the simplest possible way.  
Originally designed to be a wrapper for [Joe's Multi Report](https://github.com/JoeSchmuck/Multi-Report), it also can be used for simplify sending email overall in many other scenarios.  
  
Actually, there are 2 different usage methods:

1. Passing `--subject`, `--to_address`, `--mail_body_html` (nor a file path and plain text), plus other optionally args.
2. Passing only the full email base64 encoded (nor a file path and plain text) as `--mail_bulk`, trying to emulating the old `sendemail` function, and all the info will be retrieved there.

---

### ⚙️ Optional args:

- `--debug_enabled` to activate the debug mode (available in `--mail_bulk` too )
- `--test_mode` to trigger a quick test email send (`--to_address` need to be specified, nothing else)
- An array of absolute file path for attachments as `--attachment_files`  
- A specific sender name as `--override_fromname`  
- A specific sender address as `--override_fromemail`

---

## ✉️ Sender data override

Is possible to override the TN sender name - sender email to fit more scenarios in those ways:

- using directly `--override_fromemail` or `--override_fromname` args calling the script
- (for multi report users) editing own standard `mr_config` file, value involved are `FromName` and `From`, as a fallback  

📌 The priority is:  
`override data > fallback data > default`  

Also, only `override_fromname` and `FromName` can be passed, and they will be applied to the default email.
 
> **Customize the sender name has no particoular restrictions**, is pretty safe, **instead you have to pay attention on customizing the sender** (reject ratio depending on your provider):
> - **GMAIL**:  this provider will override your sender with the account email if it is not a validated alias, and the deliver shouldn't fail; you can safely send email with a sender plus address (example, your account is `myemail@gmail.com` and you use `myemail+multireport@gmail.com` as sender)
> - **OUTLOOK**: every sender that is not a valid alias of the account will be rejected
> - **SMTP**: every provider has own policy, but the most reject sender that is not a validated account/alias; also to mention, despite the email is send, using a sender with a different domain can be checked as spoofing with the direct conseguence that the email is delivered but go into the SPAM folder

---

## 🐞 Debugging

In case of need, passing `--debug_enabled` as arg to the script will activate the debug mode: a log file will be generated and placed into `sendemail_log` folder. 
Folder itself and files can be safely deleted manually anytime.  
Calling the script from crontab, with the debug enabled, can lead to problem if the `root` user is the one used and, before invoke the script, the correct working directory is not selected with a `cd` command.

> **Logs file not obviously expose credentials or access token**, but dont forget to cleanup after a debug session anyway to not expose more-or-less sensitive data in your usage context.

If you wanna just test the basic function fast and quickly, use the `--test_mode` and the script will compose and send a test email to the actual user email address. If an address is not specified the script will fail gracefully. In test mode, also the debug will be enabled
> **The log file attached will not contain all the info generated after the file itself will be attached**, but this not affect the original file in the `sendemail_log` folder. 

---

## 🔐 Security Concern

To retrieve TN mail configuration data, at least `READONLY_ADMIN` or `SHARING_ADMIN` roles are needed for the user that run the script.  
**So is highly adviced to only use the script in a secured folder**, not accessible to un-priviliged users, to avoid unexpected behaviour.  
The script will advice you in those scenarios, **so pay attention if some warning are raised on first usage** and fix your dataset permission accordingly.
There are other check that are performed to improve security (attachment black list, avoiding symlink, CRLF injection, ...), any suggestion is welcome and i will do my best to keep things safest and flexible for all.


---

## 🙋‍♂️ For any problem or improvements let me know!

---

## 📘 Basic Example

### ✅ TestMode: quick testing (from 1.25)

```bash
#!/bin/bash

python3 multireport_sendemail.py --test_mode
```

### ✅ Method 1

```bash
#!/bin/bash

# Basic Configuration
subject='test' 
recipient='myemail@gmail.com'

# Email Body: can be an HTML file path or plain text/html
html_file="<h1>Send Email Test</h1><p>Hello World!</p>"

# Attachments (optional): add file paths
attachment=() 
attachment+=("path/to/first/attachment")  # Replace with the actual path
#attachment+=("path/to/second/attachment") # Add additional files as needed

python3 multireport_sendemail.py \
    --subject "$subject" \
    --to_address "$recipient" \
    --mail_body_html "$html_file" \
    --attachment_files "${attachment[@]}"

```
### ✅ Method 2
```bash
#!/bin/bash

# Basic Configuration
mail_bulk= '/path/to/base64encode/email'

python3 multireport_sendemail.py \
    --mail_bulk "$mail_bulk"

```

### ✅ Method 1 With Debug

```bash
#!/bin/bash

subject='test' 
recipient='myemail@gmail.com'
html_file="<h1>Send Email Test</h1><p>Hello World!</p>"

attachment=() 
attachment+=("path/to/first/attachment")  # Replace with the actual path

python3 multireport_sendemail.py \
    --subject "$subject" \
    --to_address "$recipient" \
    --mail_body_html "$html_file" \
    --attachment_files "${attachment[@]}"
    --debug_enabled
```
### ✅ Method 1 with sender override

```bash
#!/bin/bash

subject='test' 
recipient='myemail@gmail.com'
html_file="<h1>Send Email Test</h1><p>Hello World!</p>"

python3 multireport_sendemail.py \
    --subject "$subject" \
    --to_address "$recipient" \
    --mail_body_html "$html_file" \
    --override_fromname "Pippo" \
    --override_fromemail "myemail+pippo@gmail.com"

```
