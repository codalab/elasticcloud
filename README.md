# Elastic Cloud CLI Tool

EC will automatically spin-up and spin-down VM instances according to the parameters set by you.

## Heroku setup

Env vars:

```
# SSH Keys to connect to workers with
GCE_SSH_PUB
GCE_SSH_PRIV
# Broker to connect to
BROKER_URL
# max count of VMs  
GCE_MAX 
# min count of VMs
GCE_MIN
# How many checks resulting in a node being not-busy before shrink is called
GCE_SHRINK_SENSITIVITY
# How many checks resulting in all nodes being busy before expand is called
GCE_EXPAND_SENSITIVITY
GCE_IMAGE_NAME
GCE_USE_GPUS
GCE_VM_SIZE
GCE_DATACENTER
# Actual JSON data in place of the file, this takes priority
GCE_SERVICE_ACCOUNT_KEY
# File path for GCE account json data
GCE_SERVICE_ACCOUNT_FILE
```

### Python Environment

The necessary Python packages are contained in the requirements.txt file. Install them into your environment with the following command.

`pip install -r requirements.txt`


### Google Cloud

In order to use the Google Compute Engine ( *GCE* ) provider, you must create a Google Cloud account. After creating account, you must create a service account. Instructions for creating a service account follow.

1. Open the Google Cloud Console.
2. Click the Navigation Menu at the top-left of the console window.
3. In the Navigation Menu, click **IAM & Admin -> Service Accounts**.
4. Near the banner at the top of the window, click **+ CREATE SERVICE ACCOUNT**.
5. Enter your personal details. These are not critical to the Elastic Cloud tool.
6. Click **CREATE**.
7. Grant the service account Project -> Owner permissions.
8. Grant your user account email permissions to use and administer the service account ( Enter your email into both the user and admin fields ). 
9. Click **+ CREATE KEY**.
10. Choose the JSON option and click **CREATE**. This will automatically download your service account key.
11. Move this key into your local `ElasticCloud/service_account/` directory. You may change the name to anything you like, but be sure the extension is still **.json**.
12. Copy `cloud_config/sample_config.yaml` to the name, `cloud_config/config.yaml`.
13. Open `cloud_config/config.yaml` in your favorite text editor and change the `service_account_file:` key from `service_account/test_service_account_key.json` to `service_account/your_chosen_key_name.json`.

### Ssh Key

We must create an ssh key to enable ssh access to the VMs that are instantiated by the Elastic Cloud tool. Instructions to do so follow.

1. Create the ssh key
	1. Use the `ssh-keygen -t rsa -m PEM` command.
	2. Name the key, `~/.ssh/GCE_rsa`.
2. Enable access with the newly-created ssh key.
	1.  Open the Google Cloud Console.
	2.  Navigate to the **Compute Engine** -> **Metadata**.
	3.  Click **Edit**
	4.  Scroll down to add a new key.
	5.  Copy the contents of your public key file, `~/.ssh/GCE_rsa.pub` into the *Enter entire key data* field. Now your key is enabled on every instance created with this service account!
