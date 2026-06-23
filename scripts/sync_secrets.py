import os
import subprocess
import sys

# Change this to point to your variables file
SECRETS_FILE = "C:\\GitRepos\\TerraformDeployments\\LinkedCredsOnAWS\\terraform.tfvars"  # or "terraform.tfvars"

def run_command(command):
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error executing: {' '.join(command)}")
        print(result.stderr)
        return False
    return True

def sync_secrets():
    if not os.path.exists(SECRETS_FILE):
        print(f"File not found: {SECRETS_FILE}")
        sys.exit(1)

    print(f"📖 Reading secrets from {SECRETS_FILE}...")
    
    with open(SECRETS_FILE, "r") as file:
        for line in file:
            line = line.strip()
            # Ignore empty lines and comments
            if not line or line.startswith("#"):
                continue
            
            # Safely split by the first '='
            if "=" in line:
                key, value = line.split("=", 1)
                key = key.strip().upper()
                # Strip surrounding quotes from the value
                value = value.strip().strip('"').strip("'")
                
                print(f"Pushing secret: {key}...")
                
                # Use the 'gh' CLI to set the secret. 
                # We pass the value via standard input for security (doesn't show in process list)
                gh_command = ["gh", "secret", "set", key, "-R", "github.com/Josh-Rentrope/SkillsDemo"]
                
                process = subprocess.Popen(
                    gh_command, 
                    stdin=subprocess.PIPE, 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE, 
                    text=True
                )
                stdout, stderr = process.communicate(input=value)
                
                if process.returncode == 0:
                    print(f"   {key} synced successfully.")
                else:
                    print(f"   Failed to sync {key}: {stderr.strip()}")

if __name__ == "__main__":
    # Ensure gh CLI is installed and authenticated
    if not run_command(["gh", "auth", "status"]):
        print("Please install GitHub CLI and run 'gh auth login' first.")
        sys.exit(1)
        
    sync_secrets()
    print("🏁 All secrets processed.")