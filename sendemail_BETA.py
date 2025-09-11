#!/usr/bin/env python3

import smtplib, json, argparse, os, stat, time, base64, subprocess, socket, uuid, requests, urllib.request, sys, re, hashlib, hmac, shutil
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from email.utils import formatdate, parseaddr
from email import message_from_string
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

##### V 1.70
##### Stand alone script to send email via Truenas
__version__ = "1.70"
__ghlink__ = "https://github.com/oxyde1989/standalone-tn-send-email"
__ghlink_raw__ = "https://raw.githubusercontent.com/oxyde1989/standalone-tn-send-email/refs/heads/main/sendemail.py"
__ghlink_raw_sha__ = "https://raw.githubusercontent.com/oxyde1989/standalone-tn-send-email/refs/heads/main/sendemail.py.sha256"
__email_template__ = f"https://raw.githubusercontent.com/oxyde1989/standalone-tn-send-email/refs/heads/main/templates/{__version__}.json"
__script_directory__ = os.getcwd()
__script_path__ = os.path.abspath(__file__)
__script_name__ = os.path.basename(__script_path__)

class HandleMissingVar(dict):
    def __missing__(self, key):
        return "[" + key + "]"

def render_template(name, **ctx):
    """
        this function will help to format out the email templates get by repo, to keep the code clean as possible. Now switch correctly from core and scale
    """
    try:
        append_log("Entering template render. Scale/Core switch needed")
        _name = name if os.path.exists("/usr/bin/midclt") else f"{name}_text"
        append_log(f"search for {name} template on REPO")
        reqtempl = urllib.request.Request(__email_template__, headers={"User-Agent": "tn-send-email"})
        append_log("reading template")
        with urllib.request.urlopen(reqtempl, timeout=5) as resptempl:
            template_list = json.loads(resptempl.read().decode("utf-8"))
            append_log("templates loaded")
        return template_list[_name].format_map(HandleMissingVar(**ctx))
    except Exception as e:
        append_log(f"[ERROR] rendering template '{name}': {e}")
        return f"🔴 [ERROR] Sorry, an error occured rendering template '{name}'. 🔴"

def _render_once_with_vars(text: str, vars_dict: dict):
    return text.format_map(HandleMissingVar(**vars_dict))

def _apply_microloops(text: str, vars_dict: dict):
    """
        This function will recursively expands <!-- #for x in list --> ... <!-- #endfor --> blocks. Convention: use placeholders like {x[key]} or {x[0]}, etc. in body to activate this.
        Not actually support nested loops
    """
    FOR_BLOCK_RE = re.compile(
        r"<!--\s*#for\s+(?P<var>\w+)\s+in\s+(?P<iter>\w+)\s*-->(?P<body>.*?)<!--\s*#endfor\s*-->",
        re.DOTALL | re.IGNORECASE,
    )
    append_log("trying to expands iterated vars")    
    try:
        while True:
            m = FOR_BLOCK_RE.search(text)
            if not m:
                append_log("nothing to iterate found")
                break
            else:
               append_log("block to iterate found!") 
               
            _var_name = m.group("var") 
            _iter_name = m.group("iter") 
            _body = m.group("body")               
               
            iterable = vars_dict.get(_iter_name, [])
            if not isinstance(iterable, (list, tuple)):
                append_log("iterable not found")
                iterable = []

            rendered_parts = []
            for item in iterable:
                scope = dict(vars_dict)
                scope[_var_name] = item
                rendered_parts.append(_render_once_with_vars(_body, scope))
                append_log(f"added: {item} to rendered parts")
                
            start, end = m.span()
            text = text[:start] + "".join(rendered_parts) + text[end:]
            append_log("iterations completed succesfully")

        return text   
    except Exception as e:
        append_log(f"An error occured trying to render microloop: {e}")
      
def add_user_template(u_template, u_subject, u_content, u_var=None):
    AVAILABLE_TEMPLATE = [
        "UT_default"
        , "UT_default_adv"
    ]
    
    if not u_template:
      append_log("no template provided")
      return u_content, u_subject
    u_template_file = os.path.join(__script_directory__, u_template)  
    if u_template in AVAILABLE_TEMPLATE or os.path.exists(u_template_file):
        append_log(f"template {u_template} is valid")
        user_vars = {}
        append_log("try building user custom fields")
        if u_var:
            try:
                parsed = json.loads(u_var)
                if isinstance(parsed, dict):
                    user_vars = parsed
                else:
                    append_log("var provided is not a JSON object — ignored")
            except Exception as e:
                append_log(f"[ERROR] JSON error: {e} retrieving user var")       
        u_content = u_content.format_map(HandleMissingVar(**user_vars))  
        u_subject = u_subject.format_map(HandleMissingVar(**user_vars))     
        completevar = {**user_vars, "subject": u_subject, "html_content": u_content}
        append_log("switch from builtin template or custom file template")        
        if u_template in AVAILABLE_TEMPLATE:  
            append_log("builtin template provided") 
            try:
                u_template_file_content = _apply_microloops(u_template, completevar) 
                return render_template(u_template_file_content, **completevar), u_subject
            except Exception as e:
                append_log(f"template '{u_template}' error: {e} — fallback to raw content")
                return u_content, u_subject   
        elif os.path.exists(u_template_file):
            append_log("custom template provided")             
            try:
                with open(u_template_file, 'r') as g:
                    u_template_file_content = g.read()    
                u_template_file_content = _apply_microloops(u_template_file_content, completevar)    
                return u_template_file_content.format_map(HandleMissingVar(**completevar)), u_subject
            except Exception as e:
                append_log(f"custom template '{u_template}' error: {e} — fallback to raw content")
                return u_content, u_subject               
    else:
        append_log(f"template {u_template} not applied")
        return u_content, u_subject      
    
def quick_tn_builtin_sendemail(tn_subject, tn_text):
    tn_payload_dict = {"subject": tn_subject, "html": tn_text}
    tn_payload = json.dumps(tn_payload_dict)    
    tn_midclt_path = "/usr/bin/midclt"
    if not os.path.exists(tn_midclt_path):
        tn_midclt_path = "/usr/local/bin/midclt"
        tn_payload_dict = {"subject": tn_subject, "text": tn_text}
        tn_payload = json.dumps(tn_payload_dict)
        if not os.path.exists(tn_midclt_path):
            raise FileNotFoundError("[ERROR]: Failed to load midclt")
    subprocess.run([tn_midclt_path, "call", "mail.send", tn_payload], check=True) 

class CheckForUpdate: 
    """
        this class will handle the update availability, usefull for other script that use the sendemail, or for people that wanna build theyr own update logic. Also can be used internally
    """      
    def __init__(self):  
        try:
            puo_update_available, puo_new_version = check_for_update(__version__)
            puo_response = json.dumps({"version": __version__,"latest_version": puo_new_version, "need_update": puo_update_available}, ensure_ascii=False) 
            self.puo_update_available = puo_update_available
            self.puo_new_version = puo_new_version
            self.puo_response = puo_response
        except Exception as e:
            print(f"[ERROR]: {e}")
            sys.exit(1)
            
    def parse_as_resp(self):
        return self.puo_new_version, self.puo_update_available    
    def parse_as_output(self):
        return self.puo_response   

class PerformUpdate:
    """
        this class will handle all the update process of the script. It rely on CheckForUpdate class and on the built in truenas send email to avoid conflicts
    """     
    def __init__(self):
        self.staging_dir = os.path.join(__script_directory__, "sendemail_update")
        self.new_version = None
        self.backup_path = None
        append_log(f"### Script Version: {__version__} ###")
        append_log("### SELF UPDATE ACTIVATED ###") 
        
    def get_postupdate_message(self):
        return render_template("notify_update_done", __version__=__version__, new_version=self.new_version,__ghlink__=__ghlink__)  
    def get_postupdate_fail_message(self):
        return render_template("notify_update_fail", __version__=__version__, new_version=self.new_version,__ghlink__=__ghlink__)      

    def _create_update_dir(self):
        append_log("Preparing sendemail_update dir") 
        if os.path.islink(self.staging_dir):
            self.updatepath_process_output(True, f"[ERROR]: {self.staging_dir} is a symlink. Operation not allowed for security reason", 1)
        if not os.path.exists(self.staging_dir):
            os.makedirs(self.staging_dir, exist_ok=True)
            append_log("Folder created") 
        elif not os.path.isdir(self.staging_dir):
            self.updatepath_process_output(True, f"[ERROR]: {self.staging_dir} exists and is not a directory?", 1)
        append_log("All checks performed") 
        return self.staging_dir
    
    def updatepath_process_output(self, error, detail="", exit_code=None):                
        response = json.dumps({"version": __version__,"error": error, "detail": detail, "logfile": log_file, "new_version": self.new_version, "backup_version": self.backup_path}, ensure_ascii=False)
        append_log(f"{detail}") 
        print(response)
        if exit_code is not None:
            sys.exit(exit_code)      

    def _generate_timestamp(self):
        append_log("generating a temp timestamp") 
        now = datetime.now()
        return f"{now:%Y%m%d_%H%M%S}_{now.microsecond//1000:03d}_{os.getpid()}_{__script_name__}"        
    
    def _verify_sha256(self, _payload, _remote_sha):
        append_log("Performing sha256 check") 
        _local_sha = hashlib.sha256(_payload).hexdigest().lower()
        append_log("local sha256 calculated")
        _expected_sha = _remote_sha.strip().split()[0].lower()
        append_log("remote sha256 retrieved")
        _sharesult = hmac.compare_digest(_local_sha, _expected_sha)
        append_log(f"result: {_sharesult}")
        return _sharesult

    def apply_update(self):
        try:
            append_log("Checking for update") 
            new_version, update_available = CheckForUpdate().parse_as_resp()
            self.new_version = new_version
            if not update_available:
                self.updatepath_process_output(False, f"Version {__version__} is up to date", 0)
            append_log(f"Update to the {new_version} version available") 
            d = self._create_update_dir()
            out_path = os.path.join(d, self._generate_timestamp())
            
            append_log("retrieving from github latest version")
            req = urllib.request.Request(__ghlink_raw__, headers={"User-Agent": "tn-sendemail-updater"})
            with urllib.request.urlopen(req, timeout=5) as r:
                payload = r.read()
            with open(out_path, "wb") as f:
                f.write(payload); f.flush(); os.fsync(f.fileno())
            dir_fd = os.open(d, os.O_DIRECTORY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
            append_log(f"file generated as temp {out_path}")
            
            append_log("retrieving from github latest SHA version")
            req_sha = urllib.request.Request(__ghlink_raw_sha__, headers={"User-Agent": "tn-sendemail-updater"})  
            with urllib.request.urlopen(req_sha, timeout=5) as r:
                remote_sha = r.read().decode("utf-8")
                
            append_log("everything retrievied and ready to perform sanity check")    
            check_sha = self._verify_sha256(payload, remote_sha)
            if not check_sha:
                self.updatepath_process_output(True, "[ERROR]: SHA256 mismatch, aborting", 1)
            append_log("sanity check passed")    
                
            append_log("swapping old and new script file.")    
            backup_name = self._generate_timestamp()
            backup_path = os.path.join(d, backup_name)         
            shutil.copy2(__script_path__, backup_path)    
            dst_dir = os.path.dirname(__script_path__)
            os.replace(out_path, __script_path__)
            dst_fd = os.open(dst_dir, os.O_DIRECTORY)
            try:
                os.fsync(dst_fd)
            finally:
                os.close(dst_fd)
            append_log("swap terminated, need to check again because this part can fail silently")    
            try:
                with open(__script_path__, "rb") as f:
                    _installed_payload = f.read()
            except Exception as e:
                self.updatepath_process_output(True, f"[ERROR]: unable to read installed file for sha check: {e}", 1)
            _check_post = self._verify_sha256(_installed_payload, remote_sha)
            if not _check_post:
                self.updatepath_process_output(True, "[ERROR]: post-swap SHA256 mismatch; concurrent update or name collision suspected", 1)
            append_log("post-swap sha256 OK")             
            
            if args.notify_self_update:
                self.post_update_send_notify()
                append_log("Notify send") 
            self.updatepath_process_output(False, f"New version {new_version} installed", 0)        
        except Exception as e:
            if args.notify_self_update:
                self.post_update_fail_send_notify()
            self.updatepath_process_output(True, f"[ERROR]: {e}", 1)       
            
    def post_update_send_notify(self):    
        append_log("preparing email to notify the update") 
        f_subject = f"🟢TN SendEmail {self.new_version} installed"
        f_text = self.get_postupdate_message()
        try:
            quick_tn_builtin_sendemail(f_subject, f_text)   
        except Exception as e:
            append_log("notify email send failed, sorry")     
             
    def post_update_fail_send_notify(self):    
        append_log("preparing email to notify the fail update") 
        f_subject = f"🔴TN SendEmail {self.new_version} install FAIL"
        f_text = self.get_postupdate_fail_message()
        try:
            quick_tn_builtin_sendemail(f_subject, f_text)   
        except Exception as e:
            append_log("notify email send failed, sorry")             
   
class NotifyForUpdate:
    """
        this class rely on the built-in sendemail to deliver a notify when an update is available. Considering that update are not so frequent, use the --notify_update on a weekly cronjob to avoid unecessary pings
    """      
    def __init__(self):
        
        def get_update_message():
            return render_template("notify_update_available", __version__=__version__, f_new_version=f_new_version,__ghlink__=__ghlink__)

        try:
            f_new_version, f_update_available = CheckForUpdate().parse_as_resp()
            if f_update_available:
                f_subject = f"ℹ️TN SendEmail {f_new_version} available"
                f_text = get_update_message()
                try:
                    quick_tn_builtin_sendemail(f_subject, f_text)   
                except Exception as e:
                    print("notify email send failed, sorry") 
        except Exception as e:
            print(f"[ERROR]: {e}")            
            sys.exit(1)                                             

def validate_arguments(args):
    """
        new function for an easier validation of the args passed to the function, due the fact there are now 2 calls methods. If mail_body_html is passed, nor subject and to_address are mandatory
    """
    if not args.mail_bulk and not args.mail_body_html:
        print("Error: You must provide at least --mail_bulk or --mail_body_html.")
        sys.exit(1)
    if args.mail_body_html and (not args.subject or not args.to_address):
        print("Error: If --mail_body_html is provided, both --subject and --to_address are required.")
        sys.exit(1)
    for param_name in ["subject", "to_address", "override_fromname", "override_fromemail"]:
        param_value = getattr(args, param_name, None)
        if param_value and ("\r" in param_value or "\n" in param_value):
            print(f"Error: arg '{param_name}' contains CRLF char, not allowed")
            sys.exit(1)        
    if args.debug_enabled:
        if not os.access(__script_directory__, os.W_OK):
            print(f"Current user doesn't have permission in the execution folder: {__script_directory__}")
            sys.exit(1)     
        sfw = is_secure_directory()
        if sfw:
            print(f"{sfw}")
            
def check_for_update(local_version):
    try:
        with urllib.request.urlopen(__ghlink_raw__, timeout=5) as response:
            content = response.read(2048).decode("utf-8")
            match = re.search(r'__version__\s*=\s*[\'"](\d+\.\d+)[\'"]', content)
            if match:
                remote_version = match.group(1)
                return remote_version > local_version, remote_version
    except Exception as e:
        pass
    return False, None                       
        
def is_secure_directory(directory_to_check=None):
    """
        this function help to report eventually security concerns about the usage context of the script. Promemorial: The function itself not log anything, output should be used when logfile available
    """
    if not args.debug_enabled:    
        return ""
    else:    
        try:
            directory_to_check = directory_to_check or __script_directory__
            stat_info  = os.stat(directory_to_check)
            append_message = ""
            if stat_info .st_uid != os.getuid():
                append_message = f"Security Advice: The current user (UID={os.getuid()}) is not the owner of the directory '{directory_to_check}' (Owner UID={stat_info .st_uid})."
            if bool(stat_info .st_mode & stat.S_IWOTH):
                append_message = append_message + "SECURITY WARNING: this folder is accessible to non-priviliged users that are nor owner or in group"
            return append_message  
        except Exception as e:
            print(f"Something wrong checking security issue: {e} checking {directory_to_check}")
            sys.exit(1)        
            
def is_secure_directory_forupdate(__script_path__, __version__, directory_to_check=None):
    """
    This function centralize some security check to perform before try to update, despite the is_secure_directory function that only warning, in this case the process will be aborted
    """
    if os.path.islink(__script_path__):
        real = os.path.realpath(__script_path__)
        err = {"version": __version__, "error": True, "detail": f"[ERROR]: script is a symlink; updater should be run on the real path: {real}"}
        print(json.dumps(err, ensure_ascii=False))
        sys.exit(1)
        
    directory = directory_to_check
    if not directory:
        directory = os.path.dirname(os.path.abspath(__script_path__)) or __script_directory__
    try:
        st = os.stat(directory, follow_symlinks=True)
    except Exception as e:
        err = {"version": __version__, "error": True, "detail": f"[ERROR]: cannot stat directory '{directory}': {e}"}
        print(json.dumps(err, ensure_ascii=False))
        sys.exit(1)

    if bool(st.st_mode & stat.S_IWOTH):
        err = {
            "version": __version__, "error": True, "detail": (f"[SECURITY ERROR]: directory '{directory}' is accessible to non-priviliged users that are nor owner or in group; update aborted.")}
        print(json.dumps(err, ensure_ascii=False))
        sys.exit(1)

    return True              

def create_log_file():
    """
        We setup a folder called sendemail_log where store log's file on every start if --debug_enabled is set. Every Logfiles can be safely deleted.
    """   
    
    if not args.debug_enabled:    
        return None, 0
    else:
        try:    
            log_dir = os.path.join(__script_directory__, 'sendemail_log')
            
            if os.path.islink(log_dir):
                print("Something wrong is happening here: the sendemail_log folder is a symlink")
                sys.exit(1)  
            
            if not os.path.exists(log_dir):
                os.makedirs(log_dir)
                log_file_count = 0  
            else:                 
                log_files = [f for f in os.listdir(log_dir) if f.endswith('.txt') and os.path.isfile(os.path.join(log_dir, f)) and not os.path.islink(os.path.join(log_dir, f))]
                log_file_count = len( log_files )  
            log_file_count = log_file_count + 1   

            timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime())
            log_file_path = os.path.join(log_dir, f"{timestamp}.txt")

            if not os.path.exists(log_file_path):
                with open(log_file_path, 'w') as f:
                    pass              
            return log_file_path, log_file_count
        except Exception as e:
            print(f"Something wrong managing logs: {e}")
            sys.exit(1)          

def append_log(content):
    """
        Centralized file log append
    """   
    if args.debug_enabled:        
        try:
            with open(log_file, 'a') as f:
                f.write(content + '\n')
        except Exception as e:
            process_output(True, f"Error: {e}", 1)

def process_output(error, detail="", exit_code=None):
    """
        Centralized output response 
        - version str error bool detail string exit_code 0 (ok) 1 (ko) or None (ignore)
    """                   
    response = json.dumps({"version": __version__,"error": error, "detail": detail, "logfile": log_file, "total_attach": attachment_count, "ok_attach": attachment_count_valid}, ensure_ascii=False)
    append_log(f"{detail}") 
    print(response)
    if exit_code is not None:
        sys.exit(exit_code)      

def read_config_data():
    """
     function for read the mail.config from midclt. Now supporting Core and Scale 
    """    
    append_log("trying read mail.config")
    midclt_path = "/usr/bin/midclt"
    if not os.path.exists(midclt_path):
        append_log(f"{midclt_path} not found, switching to Core midclt path") 
        midclt_path = "/usr/local/bin/midclt"
        if not os.path.exists(midclt_path):
          process_output(True, "Failed to load midclt", 1)     
     
    midclt_output = subprocess.run(
        [midclt_path, "call", "mail.config"],
        capture_output=True,
        text=True,
        check=True
    )
    if midclt_output.returncode != 0:
        process_output(True, f"Failed to call midclt: {midclt_output.stderr.strip()}", 1)
        
    append_log("read mail.config successfully")                
    midclt_config = json.loads(midclt_output.stdout)
    return midclt_config

def read_user_email():
    """
     function for read the context user email - to automatic retrieve recipient for email test
    """    
    midclt_path = "/usr/bin/midclt"
    if not os.path.exists(midclt_path):
        midclt_path = "/usr/local/bin/midclt"
        if not os.path.exists(midclt_path):
            return None
    try:
        uid = os.geteuid()
        cmd_user = [
            midclt_path,
            "call",
            "user.query",
            f'[["uid","=",{uid}]]',
            '{"get": true}'
        ]
        user_json = subprocess.check_output(cmd_user, text=True)
        user_data = json.loads(user_json)
        if user_data and user_data.get("email"):
            return user_data["email"]
    except Exception:
        return None
    return None

def load_html_content(input_content):
    """
     use this fuction to switch from achieve nor a file to read and a plain text/html
    """
    try:        
        if len(input_content) > 255:
            append_log("body can't be a file, too much long")
            return input_content
        elif os.path.exists(input_content):
            with open(input_content, 'r') as f:
                append_log("body is a file") 
                return f.read()
        else:
            append_log("no file found, plain text/html output") 
            return input_content            
    except Exception as e:
        process_output(True, f"Something wrong on body content {e}", 1)  

def validate_base64_content(input_content):
    """
    use this funtcion to validate that an input is base64encoded. Return error if not
    """      
    try:
        base64.b64decode(input_content, validate=True) 
        append_log("Base64 message is valid.")
    except Exception as e:
        process_output(True, f"Error: Invalid Base64 content. {e}", 1)   
                            
def calc_attachment_count(attachment_input):      
    """
    improved attachments output
    """      
    total_attachments = len(attachment_input) if attachment_input else 0
    return total_attachments    

DENYLIST_PREFIXES = [
    "/etc/ssh/",
    "/root/.ssh/",
]

DENYLIST_FILES = [
    "/etc/passwd",
    "/etc/shadow",
    "/etc/hosts",
    "/root/.bash_history",
    "/var/log/auth.log",
    "/var/log/messages",
    "/var/log/secure",
    "/etc/sudoers",
    "/etc/fstab",
]

def attachment_denied(path):
    try:
        real_path = os.path.realpath(path)
        if real_path in DENYLIST_FILES:
            return True        
        for prefix in DENYLIST_PREFIXES:
            if real_path.startswith(prefix):
                return True
    except Exception:
        pass
    return False

def attach_files(msg, attachment_files, attachment_ok_count):
    """
    Function to attach files: max size:50mb, no symlink allowed
    """
    attachment_max_size = 50 * 1024 * 1024
    for attachment_file in attachment_files:
        try:
            st = os.lstat(attachment_file)
            if stat.S_ISLNK(st.st_mode):
                append_log(f"skipping {attachment_file}: symlink detected")
                continue  
            append_log(f"symlink verification for {attachment_file} pass")
            if st.st_size > attachment_max_size:
                append_log(f"skipping {attachment_file}: exceeds max attachment size")
                continue 
            append_log(f"size verification for {attachment_file} pass") 
            if attachment_denied(attachment_file):
                append_log(f"skipping {attachment_file}: file in denylist")
                continue             
            append_log(f"blacklist verification for {attachment_file} pass")                    
            with open(attachment_file, 'rb') as f:
                file_data = f.read()              
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(file_data)
                encoders.encode_base64(part)
                part.add_header(
                    'Content-Disposition',
                    f'attachment; filename="{attachment_file.split("/")[-1]}"'
                )
                msg.attach(part)
                attachment_ok_count +=1
                append_log(f"attachment OK {attachment_file}")
        
        except Exception as e:
            append_log(f"attachment KO {attachment_file}: {e}")      
    return attachment_ok_count  

def getMRconfigvalue(key):
    """
    Function to get eventually multi report value from config, passing the key > the name of the setting
    """    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_file = os.path.join(script_dir, "multi_report_config.txt")

    if not os.path.exists(config_file):
        append_log(f"{config_file} not found")
        return ""

    try:
        with open(config_file, "r") as file:
            for line in file:
                line = line.strip()
                key_value_pair, _, _ = line.partition('#')
                key_value_pair = key_value_pair.strip()

                if key_value_pair.startswith(key + "="):
                    append_log(f"{key} found")
                    value = key_value_pair.split("=")[1].strip().strip('"')
                    if "\r" in value or "\n" in value:
                        append_log(f"{key} rejected, contains CRLF")
                        return ""                    
                    return value
    except Exception as e:
        append_log(f"Error reading {config_file}: {e}")
        return ""

    return ""

def get_outlook_access_token():
    """get an access token using the tn refresh token in truenas"""
    
    append_log("retrieving access token") 
    oauth_url = "https://login.microsoftonline.com/common/oauth2/v2.0/token"    
    data = {
        "client_id": email_config["oauth"]["client_id"],
        "client_secret": email_config["oauth"]["client_secret"],
        "refresh_token": email_config["oauth"]["refresh_token"],
        "grant_type": "refresh_token",
        "scope": "https://outlook.office.com/SMTP.Send openid offline_access"
    }   
    try:
        response = requests.post(oauth_url, data=data, timeout=15)   
        if response.status_code == 200:
            append_log("got access token!") 
            return response.json()["access_token"]
        else:
            process_output(True, f"response for the access token has an error: {response.text}", 1)   
    except Exception as e:
        process_output(True, f"A problem occurred retrieving access token: {e}", 1)
        
def get_fromname_fromemail(options):
    """ centralized function to retrieve from name - from email """
    try:
        for fromname, fromemail, log_message in options:
            if fromemail:
                append_log(log_message)
                return f"{fromname} <{fromemail}>" if fromname else fromemail, fromemail
        return None, None
    except Exception as e:
        process_output(True, f"A problem occurred retrieving data: {e}", 1)       
        
def get_test_message():
    return render_template("test_message", __version__=__version__,__ghlink__=__ghlink__) 
                   
def send_email(subject, to_address, mail_body_html, attachment_files, email_config, provider, bulk_email, user_template):
    """
    Function to send an email via SMTP or Gmail OAuth based on the provider available
    """
    attachment_ok_count = 0 
    tn_fromemail = email_config["fromemail"]
    tn_fromname = email_config["fromname"]    
    fallback_fromname = getMRconfigvalue("FromName")
    fallback_fromemail = getMRconfigvalue("From")     
    override_fromname = args.override_fromname
    override_fromemail = args.override_fromemail    
    from_options = [
        (override_fromname, override_fromemail, "using override fromname-email"),
        (fallback_fromname, fallback_fromemail, "using mr-config fromname-email"),
        (tn_fromname, tn_fromemail, "using default fromname-email"),
        (override_fromname, tn_fromemail, "using override fromname with tn email"),
        (fallback_fromname, tn_fromemail, "using fallback fromname with tn email"),
        (None, override_fromemail, "using override fromemail"),
        (None, fallback_fromemail, "using mr-config fromemail"),
        (None, tn_fromemail, "using default fromemail")
    ]       
    
    if provider == "smtp":
        try:
            append_log("parsing smtp config") 
            smtp_security = email_config["security"]
            smtp_server = email_config["outgoingserver"]
            smtp_port = email_config["port"]
            smtp_user = email_config["user"]
            smtp_password = email_config["pass"]
            smtp_login = email_config["smtp"]
 
            append_log("switch from classic send and bulk email")    
            if mail_body_html:
                append_log("mail hmtl provided")
                append_log("parsing html content") 
                html_content = load_html_content(mail_body_html)
                append_log("trying apply a template") 
                html_content, subject = add_user_template(user_template, subject, html_content, args.template_var)                

                append_log("start parsing headers")
                msg = MIMEMultipart()
                
                append_log("parsing data from config and override options")                                 
                msg['From'], smtp_senderemail = get_fromname_fromemail(from_options)                                              
                msg['To'] = to_address
                msg['Subject'] = subject
                msg.attach(MIMEText(html_content, 'html'))
                
                append_log(f"generate a message ID using {smtp_user}")
                try:
                    messageid_domain = smtp_user.split("@")[1]
                except Exception:
                    append_log(f"{smtp_user} not a valid address, tryng on {smtp_senderemail}")
                    try:
                        messageid_domain = smtp_senderemail.split("@")[1]
                    except Exception:
                        append_log(f"{smtp_senderemail} not a valid address, need to use a fallback ")
                        messageid_domain = "local.me"
                append_log(f"domain: {messageid_domain}")
                messageid_uuid = f"{datetime.now().strftime('%Y_%m_%d_%H_%M_%S_%f')[:-3]}{uuid.uuid4()}"
                append_log(f"uuid: {messageid_uuid}")
                messageid = f"<{messageid_uuid}@{messageid_domain}>"
                append_log(f"messageid: {messageid}")
                msg['Message-ID'] = messageid
                msg['Date'] = formatdate(localtime=True)                
                
                append_log("check for attachements...") 
                if attachment_files:
                    append_log("attachments found") 
                    attachment_ok_count = attach_files(msg, attachment_files, attachment_ok_count)
                    append_log(f"{attachment_ok_count} ok attachments") 
                    
                append_log("get hostname")     
                try:
                    hostname = socket.getfqdn()
                    if not hostname:
                        hostname = socket.gethostname()  
                except Exception:
                    process_output(True, "A problem occurred retrieving hostname", 1)     
                append_log(f"hostname retrieved: {hostname}")   
                
                append_log("tryng retrieving if more recipient are set")
                try:    
                    to_address = [email.strip() for email in to_address.split(",")] if "," in to_address else to_address.strip()
                except Exception as e:
                    process_output(True, f"Error parsing recipient: {e}", 1)                 
            
            elif bulk_email:
                append_log("using bulk email provided")
                hostname = ""
                pre_msg = load_html_content(bulk_email)
                if not pre_msg:
                    append_log("can't properly retrieve bulk email")
                validate_base64_content(pre_msg) 
                try:
                    decoded_msg = base64.b64decode(pre_msg).decode('utf-8')
                    append_log("bulk email successfully decoded from Base64")
                    mime_msg = message_from_string(decoded_msg)
                    to_address = mime_msg['To']
                    from_address = mime_msg['From']
                    try:
                        _, smtp_senderemail = parseaddr(from_address)
                        append_log("sender retrieved")
                    except Exception as e:
                        process_output(True, f"Error parsing sender: {e}", 1)  
                    if to_address:
                        append_log("recipient retrieved")
                        try:    
                            to_address = [email.strip() for email in to_address.split(",")] if "," in to_address else to_address.strip()
                        except Exception as e:
                            process_output(True, f"Error parsing recipient: {e}", 1)                         
                        msg = mime_msg
                    else:
                        process_output(True, "failed retriving recipient", 1)    
                except Exception as e:
                    process_output(True, f"Error decoding Base64 content: {e}", 1)                
                 
            else:
                process_output(True, "Something wrong with the data input", 1)                

            append_log(f"establing connection based on security level set on TN: {smtp_security}") 
            try:
                server_sendemail_done = False
                if smtp_security == "TLS":
                    with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
                        append_log(f"entered {smtp_security} path")                        
                        if hostname:        
                            append_log("adding ehlo to the message")          
                            server.ehlo(hostname)      
                        append_log("establing TLS connection")    
                        server.starttls()
                        if smtp_login:
                            append_log("entering credentials") 
                            server.login(smtp_user, smtp_password)
                        append_log(f"sending {smtp_security} email") 
                        server.sendmail(smtp_senderemail, to_address, msg.as_string())
                        server_sendemail_done = True
                elif smtp_security == "SSL":
                    with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=30) as server:
                        append_log(f"entered {smtp_security} path")   
                        if hostname:        
                            append_log("adding ehlo to the message")          
                            server.ehlo(hostname)   
                        if smtp_login:           
                            append_log("entering credentials") 
                            server.login(smtp_user, smtp_password)
                        append_log(f"sending {smtp_security} email") 
                        server.sendmail(smtp_senderemail, to_address, msg.as_string())
                        server_sendemail_done = True
                elif smtp_security == "PLAIN":
                    with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
                        append_log(f"entered {smtp_security} path")   
                        if hostname:        
                            append_log("adding ehlo to the message")          
                            server.ehlo(hostname)  
                        if smtp_login:    
                            append_log("entering credentials")
                            server.login(smtp_user, smtp_password)   
                        append_log(f"sending {smtp_security} email") 
                        server.sendmail(smtp_senderemail, to_address, msg.as_string())  
                        server_sendemail_done = True    
                else:
                    process_output(True, "KO: something wrong switching SMTP security level", 1)             
            except Exception as e:
                append_log(f"An unexpected error has occured: {e}")
                op_result_error = str(e)
                if server_sendemail_done and any(x in op_result_error.lower() for x in ["(-1,", "connection", "broken pipe", "reset", "closed"]):
                    append_log("Ignoring the error because has been detected as not-fatal")
                    return
                else:
                    process_output(True, f"KO: {e}", 1)                
                               
            append_log("SMTP operations finished")
            return attachment_ok_count            

        except Exception as e:
            process_output(True, f"KO: {e}", 1)

    elif provider == "gmail": 
        try:
            append_log("parsing Oauth config") 
            credentials = Credentials.from_authorized_user_info(email_config["oauth"])
            service = build('gmail', 'v1', credentials=credentials)
            
            append_log("switch from classic send and bulk email")     
            if mail_body_html:                  
                append_log("mail hmtl provided")
                append_log("start parsing headers")          
                msg = MIMEMultipart()
                        
                append_log("parsing html content") 
                html_content = load_html_content(mail_body_html) 
                append_log("trying apply a template") 
                html_content, subject = add_user_template(user_template, subject, html_content, args.template_var)                            
                msg.attach(MIMEText(html_content, 'html'))
                
                append_log("parsing data from config and override options")                                 
                msg['From'], smtp_senderemail = get_fromname_fromemail(from_options)                                         
                msg['to'] = to_address
                msg['subject'] = subject                
                
                append_log("check for attachements...") 
                if attachment_files:
                    append_log("attachments found") 
                    attachment_ok_count = attach_files(msg, attachment_files, attachment_ok_count)
                    append_log(f"{attachment_ok_count} ok attachments")   
                      
                append_log("Encoding message")     
                raw_message = msg.as_bytes() 
                msg = base64.urlsafe_b64encode(raw_message).decode('utf-8')                
                    
            elif bulk_email:
                append_log("using bulk email provided")
                msg = load_html_content(bulk_email)
                validate_base64_content(msg)          
            else:
                process_output(True, "Something wrong with the data input", 1)                                                     
            
            append_log("sending email")           
            service.users().messages().send(userId="me", body={'raw': msg}).execute()
            
            append_log("Email Sent via Gmail")
            return attachment_ok_count

        except Exception as e:
            process_output(True, f"KO: {e}", 1)
            
    elif provider == "outlook":
        try:
            new_access_token = get_outlook_access_token()
            append_log("parsing smtp config for outlook") 
            smtp_security = email_config["security"]
            smtp_server = email_config["outgoingserver"]
            smtp_port = email_config["port"]
                  
            append_log("switch from classic send and bulk email")   
            if mail_body_html:
                append_log("mail hmtl provided")
                append_log("parsing html content") 
                html_content = load_html_content(mail_body_html)
                append_log("trying apply a template") 
                html_content, subject = add_user_template(user_template, subject, html_content, args.template_var) 
                
                append_log("start parsing headers")
                msg = MIMEMultipart()
                append_log("parsing data from config and override options")                                 
                msg['From'], smtp_senderemail = get_fromname_fromemail(from_options) 
                msg['To'] = to_address
                msg['Subject'] = subject
                msg.attach(MIMEText(html_content, 'html'))
                
                append_log(f"generate a message ID using {smtp_senderemail}")
                try:
                    messageid_domain = smtp_senderemail.split("@")[1]
                except Exception:
                    append_log(f"{smtp_senderemail} not a valid address, need to use a fallback ")
                    messageid_domain = "local.me"
                    
                append_log(f"domain: {messageid_domain}")
                messageid_uuid = f"{datetime.now().strftime('%Y_%m_%d_%H_%M_%S_%f')[:-3]}{uuid.uuid4()}"
                append_log(f"uuid: {messageid_uuid}")
                messageid = f"<{messageid_uuid}@{messageid_domain}>"
                append_log(f"messageid: {messageid}")
                msg['Message-ID'] = messageid
                msg['Date'] = formatdate(localtime=True)                
                
                append_log("check for attachements...") 
                if attachment_files:
                    append_log("attachments found") 
                    attachment_ok_count = attach_files(msg, attachment_files, attachment_ok_count)
                    append_log(f"{attachment_ok_count} ok attachments") 
                    
                append_log("get hostname")     
                try:
                    hostname = socket.getfqdn()
                    if not hostname:
                        hostname = socket.gethostname()  
                except Exception:
                    process_output(True, "A problem occurred retrieving hostname", 1)     
                append_log(f"hostname retrieved: {hostname}")   
                
                append_log("tryng retrieving if more recipient are set")
                try:    
                    to_address = [email.strip() for email in to_address.split(",")] if "," in to_address else to_address.strip()
                except Exception as e:
                    process_output(True, f"Error parsing recipient: {e}", 1)        
                            
            elif bulk_email:
                append_log("using bulk email provided")
                hostname = ""
                pre_msg = load_html_content(bulk_email)
                if not pre_msg:
                    append_log("can't properly retrieve bulk email")
                validate_base64_content(pre_msg) 
                try:
                    decoded_msg = base64.b64decode(pre_msg).decode('utf-8')
                    append_log("bulk email successfully decoded from Base64")
                    mime_msg = message_from_string(decoded_msg)
                    to_address = mime_msg['To']
                    from_address = mime_msg['From']
                    try:
                        _, smtp_senderemail = parseaddr(from_address)
                        append_log("sender retrieved")
                    except Exception as e:
                        process_output(True, f"Error parsing sender: {e}", 1)                      
                    if to_address:
                        append_log("recipient retrieved")
                        try:    
                            to_address = [email.strip() for email in to_address.split(",")] if "," in to_address else to_address.strip()
                        except Exception as e:
                            process_output(True, f"Error parsing recipient: {e}", 1)                         
                        msg = mime_msg
                    else:
                        process_output(True, "failed retriving recipient", 1)    
                except Exception as e:
                    process_output(True, f"Error decoding Base64 content: {e}", 1)                
                 
            else:
                process_output(True, "Something wrong with the data input", 1)  

            append_log("establing connection") 
            if smtp_security == "TLS":
                with smtplib.SMTP(smtp_server, smtp_port, timeout=30) as server:
                    append_log(f"confirmed {smtp_security} path")                                 
                    append_log("establing TLS connection")    
                    server.starttls()
                    if hostname:        
                        append_log("adding ehlo to the message")          
                        server.ehlo(hostname)     
                    else:
                        append_log("invoking ehlo")
                        server.ehlo()                  
                    append_log("starting auth with access token")
                    auth_string = f"user={tn_fromemail}\1auth=Bearer {new_access_token}\1\1"
                    server.docmd("AUTH XOAUTH2 " + base64.b64encode(auth_string.encode()).decode())                                                        
                    append_log(f"sending {smtp_security} email") 
                    server.sendmail(smtp_senderemail, to_address, msg.as_string())
                    
                    append_log("Email Sent via Outlook")
                    return attachment_ok_count  
            else:
                process_output(True, "Something wrong... TLS not set in TN?", 1)   
        except Exception as e:    
            process_output(True, f"KO: {e}", 1)
        
    else:
        process_output(True, "No valid email configuration found.", 1)
                                                                
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Workaround to send email easily in Multi Report using Truenas mail.config")
    parser.add_argument("--subject", help="Email subject. Mandatory when using -mail_body_html")
    parser.add_argument("--to_address", help="Recipient email address. Mandatory when using -mail_body_html")
    parser.add_argument("--mail_body_html", help="File path for the email body, or just a plain text/html. No encoding needed")
    parser.add_argument("--attachment_files", help="OPTIONAL attachments as json file path array. No ecoding needed", nargs='*')
    parser.add_argument("--mail_bulk", help="Bulk email with all necessary parts, encoded and combined together. File path or plain text supported. Content must be served as Base64 without newline /n, the recipient will be get from the To in the message")
    parser.add_argument("--debug_enabled", help="OPTIONAL use to let the script debug all steps into log files. Usefull for troubleshooting", action='store_true')
    parser.add_argument("--override_fromname", help="OPTIONAL override sender name from TN config")
    parser.add_argument("--override_fromemail", help="OPTIONAL override sender email from TN config")
    parser.add_argument("--test_mode", help="OPTIONAL use to let the script override all info and quickly send a sample email. If the script is in the same multi report folder, the fallback will be used anyway", action='store_true')  
    parser.add_argument("--notify_update", help="OPTIONAL use to let the script to only check update availability, and notify the context user. Use in a cronjob with a weekly check", action='store_true')   
    parser.add_argument("--check_update", help="OPTIONAL use to let the script to only check update availability", action='store_true')              
    parser.add_argument("--self_update", help="OPTIONAL use to let the script to check update availability and perform an update when needed", action='store_true')      
    parser.add_argument("--notify_self_update", help="OPTIONAL use to let the script to send a notification if a self update is performed", action='store_true') 
    parser.add_argument("--use_template", help="OPTIONAL specify a template code to wrap the email. Not available in bulk path")    
    parser.add_argument("--template_var", help="OPTIONAL a json object containing all the dynamic fields to be used in the template")
    
    args = parser.parse_args()
    
    if args.check_update:
        check_update_output = CheckForUpdate().parse_as_output()
        print(f"{check_update_output}")
        sys.exit(0)      
    
    if args.notify_update:
        NotifyForUpdate()
        sys.exit(0)   
        
    if args.self_update:
        _, precheck = CheckForUpdate().parse_as_resp()
        if precheck:
            is_secure_directory_forupdate(__script_path__, __version__)           
            log_file, log_file_count = create_log_file()
            PerformUpdate().apply_update()               
        else:
            check_update_output = CheckForUpdate().parse_as_output()
            print(f"{check_update_output}")
            sys.exit(0)              
    
    if args.test_mode:
        print("Activating test mode") 
        args.debug_enabled = True
        log_file, log_file_count = create_log_file()
        append_log("### TEST MODE ON ###")
        append_log(f"### Script Version: {__version__} ###")
        args.subject = f"📩 TN SendEmail Test mode V{__version__}"        
        args.mail_body_html = get_test_message()
        args.attachment_files = None
        args.mail_bulk = None
        args.override_fromname = "Oxyde"
        args.override_fromemail = None
        args.to_address = read_user_email()
    
    validate_arguments(args) 

    try:        
        if args.test_mode:
            args.attachment_files = [log_file]
        else:
            log_file, log_file_count = create_log_file()
            append_log(f"### Script Version: {__version__} ###")    
        append_log(f"File {log_file} successfully generated")
        append_log(f"{log_file_count} totals file log")
        
        attachment_count = calc_attachment_count(args.attachment_files)  
        attachment_count_valid = 0      
        append_log(f"{attachment_count} totals attachment to handle") 
        
        email_config = read_config_data()
        append_log("Switching for the right provider")             
        provider = ""        
        tn_provider = tn_provider = email_config.get("oauth", {}).get("provider", "gmail")
        
        if "smtp" in email_config and email_config["smtp"] and not email_config.get("oauth"):
            provider = "smtp"
            append_log("** SMTP Version **")  
        elif not email_config["smtp"] and not email_config.get("oauth"):     
            provider = "smtp"
            append_log("** SMTP Version - without login **")               
        elif "oauth" in email_config and email_config["oauth"] and tn_provider == "gmail":
            provider = "gmail"
            append_log("** Gmail OAuth version **")        
        elif "oauth" in email_config and email_config["oauth"] and tn_provider == "outlook":
            provider = "outlook"
            append_log("** Outlook OAuth version **")                     
        else:
            process_output(True, "Can't switch provider", 1)
            
        attachment_count_valid = send_email(args.subject, args.to_address, args.mail_body_html, args.attachment_files, email_config, provider, args.mail_bulk, args.use_template)
        
        if attachment_count_valid is None:
            attachment_count_valid = 0
        
        final_output_message = "<< Email Sent >> "  
        
        if attachment_count_valid < attachment_count:
            final_output_message = final_output_message + "\n>> Soft warning: something wrong with 1 or more attachments >>"

        final_output_message = final_output_message + is_secure_directory()
            
        process_output(False, f"{final_output_message}", 0)
        
    except Exception as e:
        process_output(True, f"Error: {e}", 1)