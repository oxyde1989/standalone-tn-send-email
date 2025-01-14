# standalone-tn-send-email

**Stand-alone TrueNAS Send Email Script**

---

### Description
Starting from Truenas 24.10.10, the `sendemail` function is no longer available.  <br>
This standalone script provides the ability to send emails and attachments using the TrueNAS `mail.config`.<br>
Designed to be a wrapper for <a href="https://github.com/JoeSchmuck/Multi-Report">Joe's Multi Report</a>, it also can be used for simplify sending email overall.<br>
Everytime the script run, a log file will be generated; those files are automatically deleted with a retention of max 15. <br>

### For any problem, improvements, ecc ecc let me know!
If you feel more comfortable to share logs, also send me an email: oxyde1989@gmail.com

---

### Basic Example:

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
