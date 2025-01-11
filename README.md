# standalone-tn-send-email

**Stand-alone TrueNAS Send Email Script**

---

### Description
Starting from Truenas 24.10.10, the `sendemail` function is no longer available.  
This standalone script provides the ability to send emails and attachments using the TrueNAS `mail.config`.

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
