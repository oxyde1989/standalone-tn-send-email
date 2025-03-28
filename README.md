# Stand-alone TrueNAS Send Email Script

** standalone-tn-send-email **

---

### What this script do
Starting from Truenas 24.10.10, the `sendemail` function is no longer available, removed for security reason.  <br>
This standalone script provides the ability to send emails and attachments using the TrueNAS native `mail.config`, so at least `READONLY_ADMIN`, `SHARING_ADMIN` roles are needed to run correctly the script.<br>
Designed to be a wrapper for <a href="https://github.com/JoeSchmuck/Multi-Report">Joe's Multi Report</a>, it also can be used for simplify sending email overall in many other scenarios.<br>
Actually there are 2 different methods:<br>
<ul>
    <li>1- passing `--subject`,  `--to_address`, `--mail_body_html` (nor a file path and plain text) and optionally an array of file path for attachments as `--attachment_files`</li>
    <li>2- passing only the full email base64 encoded (nor a file path and plain text) as `--mail_bulk`, trying to emulating the old `sendemail` function <li>
</ul>

From version 1.00, the script will not generate log file anymore automatically; also, in version 1.05, the file cleanup has been totally removed.
<br>Old `sendemail_log` folder and file inside can be safely deleted. <br>

<b>Is highly adviced to use the script in a secured folder</b>, not accessible to un-priviliged users, to avoid unexpected behaviour. 
<br>The script will advice you in those scenario, check your dataset permission before use the script.

### Debugging
In case of need, passing `--debug_enabled` as arg to the script will activate the debug mode: a log file will be generated and placed into `sendemail_log` folder; folder itself and files can be safely deleted manually whene debug finish.<br>
<b>Logs file not expose credentials or access token</b>, but consider to cleanup after a debug session  <br>

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