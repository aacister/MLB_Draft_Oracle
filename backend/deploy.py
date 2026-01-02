import os
import shutil
import zipfile
import subprocess


def main():
    print("Creating Lambda deployment package...")

    # Clean up
    if os.path.exists("lambda-package"):
        shutil.rmtree("lambda-package")
    if os.path.exists("lambda-deployment.zip"):
        os.remove("lambda-deployment.zip")

    # Create package directory
    os.makedirs("lambda-package")

    # Install dependencies using Docker with Lambda runtime image
    print("Installing dependencies for Lambda runtime...")

    # Use the official AWS Lambda Python 3.12 image
    # This ensures compatibility with Lambda's runtime environment
    # Get project root (one level up from directory)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    subprocess.run(
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{project_root}:/var/task",
            "--platform",
            "linux/amd64",  # Force x86_64 architecture
            "--entrypoint",
            "",  # Override the default entrypoint
            "public.ecr.aws/lambda/python:3.12",
            "/bin/sh",
            "-c",
            f"pip install --target /var/task/lambda-package -r /var/task/requirements.txt --platform manylinux2014_x86_64 --only-binary=:all: --upgrade",
        ],
        check=True,
    )

    # Copy application files
    print("Copying application files...")
    for file in ["lambda_handler.py"]:
        if os.path.exists(file):
            shutil.copy2(file, "lambda-package/")

    # Copy api directory
    if os.path.exists("api"):
        shutil.copytree("api", "lambda-package/api")

    # Copy config directory
    if os.path.exists("config"):
        shutil.copytree("config", "lambda-package/config")

    # Copy data directory
    if os.path.exists("data"):
        shutil.copytree("data", "lambda-package/data")
    
    # Copy draft_agents directory
    if os.path.exists("draft_agents"):
        shutil.copytree("draft_agents", "lambda-package/draft_agents")
    
    # Copy mcp_clients directory
    if os.path.exists("mcp_clients"):
        shutil.copytree("mcp_clients", "lambda-package/mcp_clients")
    
    # Copy mcp_servers directory
    if os.path.exists("mcp_servers"):
        shutil.copytree("mcp_servers", "lambda-package/mcp_servers")

    # Copybackend.models directory
    if os.path.exists(backend.models"):
        shutil.copytree(backend.models", "lambda-packagebackend.models")
    
    # Copy templates directory
    if os.path.exists("templates"):
        shutil.copytree("templates", "lambda-package/templates")

    # Copy utils directory
    if os.path.exists("utils"):
        shutil.copytree("utils", "lambda-package/utils")

    # Copy memory directory
    if os.path.exists("memory"):
        shutil.copytree("memory", "lambda-package/memory")
    
    # Copy sqlite-data directory
    if os.path.exists("sqlite-data"):
        shutil.copytree("sqlite-data", "lambda-package/sqlite-data")



    # Create zip
    print("Creating zip file...")
    with zipfile.ZipFile("lambda-deployment.zip", "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk("lambda-package"):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, "lambda-package")
                zipf.write(file_path, arcname)

    # Show package size
    size_mb = os.path.getsize("lambda-deployment.zip") / (1024 * 1024)
    print(f"✓ Created lambda-deployment.zip ({size_mb:.2f} MB)")


if __name__ == "__main__":
    main()