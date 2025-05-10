# Stand-alone TrueNAS Send Email Script

<i>using the built-in `mail.config` data</i>

---

### What this script do
Starting from Truenas 24.10.10, the `sendemail` function is no longer available, removed for security reason.  <br>
This standalone script provides the ability to send emails and attachments using the TrueNAS native `mail.config`<br>
Designed to be a wrapper for <a href="https://github.com/JoeSchmuck/Multi-Report">Joe's Multi Report</a>, it also can be used for simplify sending email overall in many other scenarios.<br>
Actually, there are 2 different usage methods:<br>
<ul>
    <li>1- passing `--subject`,  `--to_address`, `--mail_body_html` (nor a file path and plain text), plus other optionally args **</li>
    <li>2- passing only the full email base64 encoded (nor a file path and plain text) as `--mail_bulk`, trying to emulating the old `sendemail` function, and all the info will be retrieved there <li>
</ul>

** Optionals args are:
<ul>
    <li>`--debug_enabled` to activate the debug mode </li>
    <li> an array of absolute file path for attachments as `--attachment_files` <li>
    <li> a specific sender name as `--override_fromname`</li>
    <li> a specific sender address as `--override_fromemail`</li>
</ul>

### Sender data override
Is possible to override the TN sender name - sender email:
- passing `--override_fromemail` or `--override_fromname`
- multi report users can edit theyr standard mr_config file, value involved are `FromName` and `FromEmail`, as a fallback
The priority is override data > fallback data > default. Also, only `override_fromname` and `FromName` can be passed, and they will be applied to the default email.

<b>Version 1.10 possible breakchange for multi report users:</b> <br>
before update, <i>check if your multi report configuration file contains a valid `FromEmail` value.</i> <br>
Gmail users shouldn't be impacted by that, but for SMTP and Outlook users, <b>a not valid alias-address used there can be reason of fail.</b>

### Debugging
*** From version 1.00, the script will not generate log file anymore automatically
*** From version 1.05, the file cleanup has been totally removed.
In case of need, passing `--debug_enabled` as arg to the script will activate the debug mode: a log file will be generated and placed into `sendemail_log` folder; folder itself and files can be safely deleted manually everytime.<br>
<b>Logs file not expose credentials or access token</b>, but consider anyway to cleanup everything after a debug session.<br>

### Security Concern
To retrieve TB mail config data, at least `READONLY_ADMIN` or `SHARING_ADMIN` roles are needed for the user that run the script.
<b>Is highly adviced to use the script in a secured folder</b>, not accessible to un-priviliged users, to avoid unexpected behaviour. 
<br>The script will advice you in those scenarios, <b>but check your dataset permission before use the script.</b>

### For any problem or improvements let me know!

---

### Basic Example:
### Method 1

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
### Method 2
```bash
#!/bin/bash

# Basic Configuration
mail_bulk= '/path/to/base64encode/email'

python3 multireport_sendemail.py \
    --mail_bulk "$mail_bulk"

```

### Method 1 With Debug

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
### Method 1 with sender override

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