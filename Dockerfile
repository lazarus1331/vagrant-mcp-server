FROM python:3.12-slim-bookworm
LABEL maintainer="Michael Rollins"

# Set user ID to use for vagrant user; Should match target environment User's UID
ARG SET_UID=1000

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    unzip \
    curl \
    gnupg \
    lsb-release \
    && rm -rf /var/lib/apt/lists/*

# Install Vagrant
RUN wget -O- https://apt.releases.hashicorp.com/gpg | gpg --dearmor | tee /usr/share/keyrings/hashicorp-archive-keyring.gpg \
    && echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] https://apt.releases.hashicorp.com $(lsb_release -cs) main" | tee /etc/apt/sources.list.d/hashicorp.list \
    && apt-get update && apt-get install -y vagrant \
    && rm -rf /var/lib/apt/lists/*

# Install VirtualBox (if using VirtualBox provider)
# Note: This requires privileged mode and may not work in all container environments
RUN wget -O- https://www.virtualbox.org/download/oracle_vbox_2016.asc | gpg --dearmor | tee /usr/share/keyrings/oracle-virtualbox-2016.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/oracle-virtualbox-2016.gpg] https://download.virtualbox.org/virtualbox/debian $(lsb_release -cs) contrib" | tee /etc/apt/sources.list.d/virtualbox.list \
    && apt-get update && apt-get install -y virtualbox-7.0 \
    && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the MCP server script
COPY vagrant-mcp-server.py .

# Create directory for Vagrant projects
RUN mkdir -p /vagrant-projects /app/.vagrant.d

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV VAGRANT_HOME=/app/.vagrant.d
ENV VAGRANT_PROJECTS_DIR=/vagrant-projects

# Create vagrant user to avoid running as root
RUN useradd -m -u ${SET_UID} vagrant && \
    chown -R vagrant:vagrant /app /vagrant-projects
USER vagrant

# Expose stdio for MCP communication
CMD ["python", "vagrant-mcp-server.py"]

# docker run -i --rm \
# -v /path/to/your/vagrant/projects:/vagrant-projects:rw \
# -v /home/$USER/.vagrant.d:/app/.vagrant.d:rw \
# vagrant-mcp-server
