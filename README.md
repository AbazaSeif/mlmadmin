### Description
MLMAdmin is a web application powered by the Django framework. It is designed to give web access to the mass mailing software [mlmmj](http://mlmmj.org/) .  
### Main features:

* User interface  
Users can manage subscription to mailing lists, moderate tasks, compose new emails in the web form and read bounces.  
Only users with a 'staff' attribute can download existing lists.  
A user can be a moderator of any number of mailing lists.

* Admin interface  
Admins can create, rename and delete mailing lists, add moderators, manage subscription to mailing lists.  
Admins can also synchronized the file structure of [mlmmj](http://mlmmj.org/), i.e. in case of the active-passive configuration of the service,  
when MySQL is configured in the master-slave mode. Synchronization can be done in the admin interface and by a Django admin command.

* RESTful API  
Only used with a 'staff' attribute can use the API.  
A user with an issued token can use the API to view and update mailing lists.  
The API is based on [Django REST framework](http://www.django-rest-framework.org/).

* LDAP users and groups  
MLMAdmin mailing lists and users are created based on LDAP groups and their members.  
LDAP users should have a valid email and be enabled.

* Users can be authenticated either by Kerberos or locally.  
In case of the Kerberos authentication the web server authenticates the user and supplies the 'REMOTE_USER' in the header of the request.


### System requirement
* Centos 6/RHEL 6,
* Python 2.6.6,
* Postfix 2.6,
* Apache 2.2,

## Installation

### Virtualenv, Django and MLMAdmin
Install these packages with yum install:
```sh
mlmmj httpd mysql-server mod_ssl.x86_64 mod_auth_kerb mod_wsgi python-virtualenv.noarch gcc mysql-devel MySQL-python openldap-devel
```
Set permission for the directory '/var/spool/mlmmj/':
```sh
chown nobody:root /var/spool/mlmmj/
```

### Log file
Create a file '/var/log/mlmadmin_sync.log' and set permissions:
```sh
touch /var/log/mlmadmin_sync.log
chown nobody:nobody /var/log/mlmadmin_sync.log
```

### Services
Make links for httpd and mysqld in runlevels 2345:
```sh
chkconfig httpd on
chkconfig mysqld on
```
Make sure that postfix has links for runlevels 2345 as well.

### MySQL
Create the database 'mlmadmin' in MySQL, use 'CHARACTER SET utf8', then create a MySQL user 'mlmadmin_dbuser', and grant permission:
```
mysql> CREATE DATABASE mlmadmin CHARACTER SET utf8;
mysql> CREATE USER 'mlmadmin_dbuser'@'localhost' IDENTIFIED BY 'YOUR_PASSWORD_HERE';
mysql> GRANT ALL PRIVILEGES ON mlmadmin.* TO 'mlmadmin_dbuser'@'localhost';
mysql> FLUSH PRIVILEGES;
```

### MLMAdmin
Untar the Django project 'MLMAdmin' to '/opt/mlmadmin'.  
Set permision 755 (root:root) for the directory '/opt/mlmadmin/ and its subdirectories. The owner and the group for the directory '/opt/mlmadmin/media/upload' should be nobody:root.  
All the files should have 644 root:root except for '/opt/mlmadmin/mlmmj-make-ml' which must have an execution bit.  
Set the correct settings in the file '/opt/mlmadmin/settings.py':
```
# Project settings
COMPANY_NAME = 'The name of the company' # leave empty to not display the company name
COMPANY_MAIL_DOMAIN = 'example.com'

# Use AUTHENTICATION BACKEND 'mlmadmin.auth.backends.MLMRemoteUserBackend'
AUTH_USE_KERBEROS = True

# LDAP settings for AUTHENTICATION BACKEND 'mlmadmin.auth.backends.MLMRemoteUserBackend'
AUTH_LDAP_SERVER_URI_SET = ['ldapserver1', 'ldapserver2', 'ldapsearver3', ]
AUTH_LDAP_BIND_DN = 'CN=LDAP_USERNAME,OU=Server Accounts,OU=SYSTEMS,DC=example,DC=com'
AUTH_LDAP_BIND_PASSWORD = 'password for LDAP user'
AUTH_LDAP_USER_SEARCH = 'DC=example,DC=com'
AUTH_LDAP_GROUP_SEARCH = 'OU=MLMAdmin,DC=example,DC=com'
# Automatically create a Token when a user is created
REST_FRAMEWORK_TOKEN_USER_CREATE = True

# Automatically create a Token when a user is created
REST_FRAMEWORK_TOKEN_USER_CREATE = False
SERVER_EMAIL = 'mlmadmin@example.com'
DEFAULT_FROM_EMAIL = SERVER_EMAIL
ADMINS = (
    ('support_team', 'support_team@example.com'),
)

DATABASES = {
    'default': {
        ...
        'PASSWORD': 'password for the DB user',             # Not used with sqlite3.
        ...
    }
}

ALLOWED_HOSTS = ['name of the server', 'FQDN name of the server']
```

### Apache configuration file
Copy the configuration file 'mlmadmin.conf' for the Apache web server, change the name and the address of the server:
```sh
cp /opt/mlmadmin/mlmadmin.conf /etc/httpd/conf.d/mlmadmin.conf
```

### Keytab
Copy the file '/etc/krb5.keytab' to '/root/krb5.keytab', add 'Service Principals' HTTP:
```sh
net ads keytab add HTTP -U jsmith
```
Run 'ktutil' and leave only 'HTTP' lines, save it to the file '/etc/httpd/conf.d/http.keytab', set permissions 500 apache:apache:
```
rkt /etc/httpd/conf.d/http.keytab
```
Copy the original file '/root/krb5.keytab' back to '/etc/krb5.keytab', its permissions should be 500 root:root.

### Certificate
Issue a new certificate in the Certificate Authority, the type should be 'Server Authentication', put all SAM (Subject Alternative Name) for all the names by which the web service can be addressed,  
i.e. 'mlmadmin.example.com', 'mlmadmin'. Put the signed certificate and the CA certificate in '/etc/pki/tls/certs/', put the private key in '/etc/pki/tls/private/'.  
A sample configuration file to generate a certificate request 'mlmadmin_csr.cfg' can be as follows:
```
[ req ]
default_bits           = 2048
default_md             = sha256
default_keyfile        = mlmadmin.key
distinguished_name     = req_distinguished_name
encrypt_key            = no
prompt                 = no
string_mask            = nombstr
req_extensions         = v3_req
[ v3_req ]
basicConstraints       = CA:FALSE
keyUsage               = digitalSignature, keyEncipherment, dataEncipherment
extendedKeyUsage       = serverAuth, clientAuth
subjectAltName         = IP:10.0.0.2, DNS:mlmadmin, DNS:mlmadmin.example.com
[ req_distinguished_name ]
countryName            = RU
stateOrProvinceName    = Moscow
localityName           = Moscow
0.organizationName     = COMPANY LTD
organizationalUnitName = IT
commonName             = mlmadmin.example.com
```
Use these commands to create a private key and a certification request:
```sh
openssl genrsa -out mlmadmin.key 2048
openssl req -new -key mlmadmin.key -out mlmadmin.csr -config mlmadmin_csr.cfg
```

### Configure Virtualenv
Create and activate a 'virtualenv' in '/opt/mlmadmin/venv':
```sh
virtualenv /opt/mlmadmin/venv
cd /opt/mlmadmin/venv
source /opt/mlmadmin/venv/bin/activate
```
Read more about 'virtualenv' at https://virtualenv.pypa.io/en/latest/userguide.html.

### Python packages
Install the following python packages with 'pip install -r /opt/mlmadmin/requirements.txt',  
the contents of the file '/opt/mlmadmin/requirements.txt' are as follows:
```
Django==1.4.20
django-annoying==0.8.3
django-multifilefield==1.0
django-settings-export==1.0.5
djangorestframework==3.1.3
MySQL-python==1.2.5
python-dateutil==2.4.2
python-ldap==2.4.20
```

### Create tables and superuser
Run this Django admin command '/opt/mlmadmin/python manage.py syncdb', it will create tables, necessary for the web application to run, and create a superuser:
```sh
(venv)[root@mlmadmin mlmadmin]# /opt/mlmadmin/python manage.py syncdb
Creating tables ...
Creating table auth_permission
Creating table auth_group_permissions
Creating table auth_group
Creating table auth_user_user_permissions
Creating table auth_user_groups
Creating table auth_user
Creating table django_content_type
Creating table django_session
Creating table django_admin_log
Creating table authtoken_token
Creating table mlmadmin_mlm_moderators
Creating table mlmadmin_mlm
Creating table mlmadmin_recipient
You just installed Django's auth system, which means you do not have any superusers defined.
Would you like to create one now? (yes/no): yes
Username (leave blank to use 'root'): admin
E-mail address: admin@example.com
Password:
Password (again):
Superuser created successfully.
Installing custom SQL ...
Installing indexes ...
Installed 0 object(s) from 0 fixture(s)
```

### Configure postfix
Add the following settings to the file '/etc/postfix/main.cf':
```
inet_interfaces = all
mydestination = $myhostname, localhost.$mydomain, localhost, example.com
alias_maps = hash:/etc/aliases, hash:/var/spool/mlmmj/mlmmj
recipient_delimiter = +
```

### Collect static files
Run this command to collect the Django static files
```sh
(venv)[root@mlmadmin mlmadmin]# python /opt/mlmadmin/manage.py collectstatic
```

### Crontab
Add the following job to the crontab of the user 'nobody', it will enable synchronization of LDAP users and groups:
```sh
crontab -u nobody -e
*/15 * * * * /opt/mlmadmin/venv/bin/python /opt/mlmadmin/manage.py sync_users_groups
```
### Manual synchronization
in case a manual synchronization is needed, use these Django admin commands:
```sh
sudo -u nobody /opt/mlmadmin/venv/bin/python /opt/mlmadmin/manage.py sync_mlmmj
sudo -u nobody /opt/mlmadmin/venv/bin/python /opt/mlmadmin/manage.py sync_users_groups
```
Please note that these commands are run as the user 'nobody'