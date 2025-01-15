# standalone-tn-send-email

**Stand-alone TrueNAS Send Email Script**

---

### Description
Starting from Truenas 24.10.10, the `sendemail` function is no longer available.  <br>
This standalone script provides the ability to send emails and attachments using the TrueNAS `mail.config`.<br>
Designed to be a wrapper for <a href="https://github.com/JoeSchmuck/Multi-Report">Joe's Multi Report</a>, it also can be used for simplify sending email overall.<br>
From version 0.05 is possible to use 2 different methods:<br>
<ul>
    <li>1 passing <i>subject</i>, <i>to_address</i>, <i>mail_body_html</i> (nor a file path and plain text) and optionally an array of file path for attachments as <i>attachment_files</i></li>
    <li>2 passing the full email base64 encoded (nor a file path and plain text), excatly as using `sendemail` function<li>
</ul>
Everytime the script run, a log file will be generated; those files are automatically deleted with a retention of max 15. <br>

### For any problem, improvements, ecc ecc let me know!
If you feel more comfortable to share logs, also send me an email: oxyde1989@gmail.com

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
    --mail_bulk "$mail_bulk" \

