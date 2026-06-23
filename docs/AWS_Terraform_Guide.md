# AWS + Terraform/OpenTofu Setup Guide

## Overview

This guide walks you through:
1. Creating an AWS account
2. Creating an API key (so Terraform can talk to AWS)
3. Installing Terraform or OpenTofu
4. Installing the AWS CLI and configuring credentials
5. Deploying your first Terraform file
6. Building a real-world project with variables

---

## Part 1: Create an AWS Account

1. Go to https://aws.amazon.com/
2. Click **Create an AWS Account** (top-right)
3. Enter your email and a password, then click **Continue**
4. Choose **Personal** for the account type
5. Enter your billing details (name, address, phone, credit card)
   - **AWS will charge you for real resources.** Most small experiments cost pennies, but always check pricing first.
6. Verify your identity via phone (automated call)
7. You can choose the **Basic (free)** support plan; but if you hit limits, try making an account with the paid plan.
8. You're in. Go to https://console.aws.amazon.com/

---

## Part 2: Create an API Key (Access Key)

An "access key" is a pair of IDs that lets Terraform act on your behalf.

1. Log into the AWS Console: https://console.aws.amazon.com/
2. In the search bar at the top, type **IAM** and click the result
3. In the left menu, click **Users**, then **Create user**
4. Enter a name like `terraform-user`, click **Next**
5. Under "Permissions options", select **Attach policies directly**
6. In the search box, type **AdministratorAccess**, check the box next to it
   - ⚠️ For production, you'd use a more restricted policy. For learning, this is fine.
7. Click **Next**, then **Create user**
8. Click the username you just created, go to the **Security credentials** tab
9. Scroll to **Access keys**, click **Create access key**
10. Choose **Command Line Interface (CLI)**, check the acknowledgement, click **Next**
11. Click **Create access key**
12. **IMPORTANT:** Click **Download .csv file** — save this file somewhere safe. It contains:
    - `Access Key ID` (e.g. `AKIAIOSFODNN7EXAMPLE`)
    - `Secret Access Key` (e.g. `wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY`)

> **Never share these keys or commit them to code.** Treat them like your bank PIN.

---

## Part 3: Install Terraform or OpenTofu

### Option A: Terraform

**Windows (easiest):** Use the `install-terraform.bat` script included with this guide.
1. **Right-click** `install-terraform.bat` → **Run as administrator** (choose Yes on the UAC prompt)
2. The script will auto-detect the latest version, download and extract to `C:\Terraform`, and update your system PATH
3. Open a **new** PowerShell or Command Prompt window after it finishes

**Manual install (any OS):**
1. Go to https://developer.hashicorp.com/terraform/install
2. Download the version for your operating system (Windows, Mac, Linux)
3. **Windows:** Run the downloaded `.exe` installer
4. **Mac:** Open the downloaded `.zip` — move the `terraform` binary to `/usr/local/bin/`
5. Verify it worked by opening a terminal and running:
   ```
   terraform --version
   ```
   You should see a version number.

   > **Windows tip:** Press the Windows key, type `cmd`, press Enter — that opens Command Prompt.

### Option B: OpenTofu (recommended — open-source fork of Terraform)

OpenTofu is fully compatible with Terraform files. Everything in this guide works the same — just replace `terraform` with `tofu` in every command.

1. Go to https://opentofu.org/docs/intro/install/
2. Pick your OS and follow the 2-3 step instructions
3. Verify:
   ```
   tofu --version
   ```

---

## Part 4: Install and Configure the AWS CLI

The AWS CLI is the command-line tool that handles login credentials. Once it's set up, both Terraform and the `aws` command can use those credentials automatically.

### 4a. Install the AWS CLI

The latest way to get the AWS CLI is to run an install script from command prompt

e.g. for Windows:
```
msiexec.exe /i https://awscli.amazonaws.com/AWSCLIV2.msi
```

Here is more information about the Install:
https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html

And information about the CLI tool as a whole can be found at https://aws.amazon.com/cli/


After you run the install command, you can open a **new** terminal window and verify:
   ```
   aws --version
   ```
   You should see something like `aws-cli/2.x.x`.

### 4b. Run `aws configure`

This saves your credentials into a file that Terraform reads automatically. No more environment variables.

In your terminal, run:

```
aws configure
```

The tool will ask you four questions. Type in your values and press Enter after each one:

| Prompt | What to enter |
|---|---|
| `AWS Access Key ID` | Paste the access key ID from Part 2 |
| `AWS Secret Access Key` | Paste the secret key from Part 2 |
| `Default region name` | Type `us-east-1` (or your preferred region) |
| `Default output format` | Type `json` |

**That's it.** From now on, any Terraform project you run in this computer will use these credentials automatically. No need to set environment variables each time.

### 4c. (Advanced) Using SSO instead of access keys

If your company uses AWS SSO (Single Sign-On) instead of access keys:

```
aws configure sso
```

This launches a browser login flow. After you log in, the CLI saves a temporary session. You'll need to run `aws sso login` periodically to refresh it. Terraform picks up SSO credentials the same way.

> For a personal learning account, stick with `aws configure` from section 4b. SSO is mainly for corporate setups.

### How credential discovery works

When you run `terraform plan` or `terraform apply`, Terraform looks for credentials in this order:

1. **Environment variables** (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`) — if set, these win
2. **AWS CLI credentials file** (`~/.aws/credentials`) — this is what `aws configure` created
3. **AWS config file** (`~/.aws/config`)
4. **IMDS** (if running on an EC2 instance, it grabs temporary credentials automatically)

For your local machine, the AWS CLI credentials file is all you need.

---

## Part 5: Practice — Deploy Your First Resource

Walk through this to prove everything works. You'll create an S3 bucket (a simple cloud storage folder).

### 5a. Create a project folder

```
mkdir my-first-infra
cd my-first-infra
```

### 5b. Create a file called `main.tf`

Open a text editor (Notepad, VS Code, etc.) and paste this:

```hcl
# Tell Terraform to use AWS
terraform {
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

# Configure the AWS provider
# It picks up credentials from your AWS CLI automatically
provider "aws" {
  region = "us-east-1"
}

# Create a simple resource: an S3 bucket (like a cloud folder)
resource "aws_s3_bucket" "my_first_bucket" {
  bucket = "my-unique-bucket-name-123456789"
  tags = {
    Name = "MyFirstBucket"
  }
}
```

> **Change the bucket name:** S3 bucket names must be **globally unique**. Pick something like `yourname-test-bucket-2025` — if you get an error, just change it and try again.

### 5c. Open a terminal in this folder

Make sure your terminal is at the `my-first-infra` path. (On Windows, type `cd C:\path\to\my-first-infra`.)

### 5d. Initialize (downloads the AWS provider)

```
terraform init
```

You'll see "Terraform has been successfully initialized!"

### 5e. Preview what will be created

```
terraform plan
```

This shows you what Terraform will do. Read it to make sure it looks right.

### 6. Apply (create the resources)

```
terraform apply
```

Type `yes` when prompted. After 30-60 seconds you should see:

```
Apply complete! Resources: 1 added, 0 changed, 0 destroyed.
```

### 7. Verify in AWS

Go to https://s3.console.aws.amazon.com/s3/ — you should see your bucket.

### 8. Clean up (so you don't get charged)

```
terraform destroy
```

Type `yes`. This deletes everything Terraform created.

---
## Part 6: Deploying Your LinkedCreds Project to AWS

This section guides you through deploying your full Next.js and FastAPI stack to AWS using **Amazon ECS (Elastic Container Service) with AWS Fargate** and an **Application Load Balancer**. This setup packages your frontend and backend into isolated containers via GitHub, ensuring a highly reliable and zero-touch deployment.

### 6a. Understand the Architecture

This layout automates how your code moves from GitHub to a live web address:

1. **The Code Registry (ECR):** A secure repository in your AWS account that stores your finalized application images.
2. **The App Runner (ECS Fargate):** The cloud engine that runs your application packages securely without requiring you to manage underlying servers.
3. **The Traffic Director (Load Balancer):** A single permanent web address provided by AWS. It accepts public traffic and automatically routes web dashboard requests to the Frontend, and `/api` requests to the Backend.

---

### 6b. Set Up Your Infrastructure with Terraform

First, we establish the cloud environment. Create a local folder to hold your infrastructure configuration files:

```bash
mkdir aws-LinkedCreds
cd aws-LinkedCreds

```

Save your provided configuration files (`main.tf` and `variables.tf`) inside this directory. Ensure your local terminal is authenticated to your AWS account, and initialize the project:

```bash
terraform init

```

Deploy the infrastructure to AWS:

```bash
terraform apply

```

Review the infrastructure plan on your screen, type `yes`, and press Enter. Once complete, Terraform will output a permanent web link called `alb_dns_name` (e.g., `http://linkedcreds-alb-12345.elb.amazonaws.com`). Save this URL—it is the direct gateway to your live application.

---

### 6c. Automate Your Secrets with the GitHub CLI

Your cloud build needs access to your project credentials (such as Firebase keys and AWS deploy tokens). You can use the official **GitHub CLI (`gh`)** to sync your local configurations to GitHub instantly without manual data entry.

1. Install the GitHub CLI if it isn't already on your machine (on Windows: `winget install --id GitHub.cli`).
2. Log into your GitHub account via your terminal:
```bash
gh auth login

```


3. Create a local file named `.env` in your project root and add your deployment variables:
```text
AWS_ACCESS_KEY_ID="your-aws-key"
AWS_SECRET_ACCESS_KEY="your-aws-secret"
AWS_REGION="us-east-2"
NEXT_PUBLIC_FIREBASE_API_KEY="your-firebase-key"
# ... add any remaining project variables

```


4. Run the automated synchronization script:
```bash
python scripts/sync_secrets.py

```



This securely populates your repository's encrypted settings vault on GitHub.

---

### 6d. Trigger the Cloud Build and Deploy

To save local disk space and processing power, your application builds run entirely in the cloud using GitHub Actions. To ensure stability, deployments are tied strictly to a dedicated branch.

1. Create and switch to your deployment branch:
```bash
git checkout -b aws-deployment

```


2. Commit your application code along with the pipeline configuration file (`.github/workflows/deploy.yml`).
3. Push the branch to GitHub:
```bash
git push origin aws-deployment

```



---

### 6e. Verify and Visit Your App

1. Navigate to your repository on GitHub.com and select the **Actions** tab.
2. Click on the running **Build and Push to Amazon ECR** workflow to monitor the build.
3. Once the workflow completes successfully, AWS ECS automatically pulls the fresh packages and launches the containers.

You can now copy the `alb_dns_name` link generated during your Terraform step and paste it into any browser to access your live application. For your final production launch, your custom domain (`linkedcreds.domain.org`) can be pointed directly to this Load Balancer link.

## Common Commands Cheat Sheet

| Command | What it does |
|---|---|
| `terraform init` | Set up the project (run once at the start) |
| `terraform plan` | Preview changes |
| `terraform apply` | Create/update resources |
| `terraform destroy` | Delete all resources |
| `terraform fmt` | Auto-format your `.tf` files |
| `aws configure` | Set up or update your saved credentials |
| `aws sts get-caller-identity` | Verify which AWS account you're logged in as |

For OpenTofu, replace `terraform` with `tofu` in all commands above.

---

## Troubleshooting

| Problem | Likely Fix |
|---|---|
| `No valid credential sources found` | You haven't run `aws configure` yet, or you're in a new terminal and the profile isn't set. Run `aws configure` (Part 4b). |
| `Unable to locate credentials` | Same as above. Run `aws configure` and verify with `aws sts get-caller-identity`. |
| `Bucket already exists` | The bucket name is taken. Change the `bucket` value to something more unique. |
| `AccessDenied` | Your IAM user doesn't have permission. Go back to Part 2 and ensure you attached `AdministratorAccess`. |
| `command not found: terraform` | Terraform isn't installed or isn't in your PATH. Re-run the installer or restart your terminal. |
| `command not found: aws` | The AWS CLI isn't installed. Re-run the installer from Part 4a. |

---

## Next Steps

- Add more resources: https://registry.terraform.io/browse/providers/aws
- Learn more: https://developer.hashicorp.com/terraform/tutorials
- Store your state file remotely (instead of locally) with an S3 backend — ask about this when you're ready
