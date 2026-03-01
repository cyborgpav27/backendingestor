import sys
import re

bucket_name = sys.argv[1]

with open('infrastructure.yaml', 'r') as f:
    content = f.read()

# Replace the ZipFile block with S3 configuration
pattern = r'      Code:\s*\n\s+ZipFile: \|[^\n]*\n(?:.*\n)*?(?=      # Function configuration)'
replacement = f'      Code:\n        S3Bucket: {bucket_name}\n        S3Key: lambda-deployment-package.zip\n'

content = re.sub(pattern, replacement, content)

with open('infrastructure-deploy.yaml', 'w') as f:
    f.write(content)

print("Template updated successfully")
