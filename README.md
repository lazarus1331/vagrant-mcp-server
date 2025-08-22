# Vagrant MCP Server Setup

## Prerequisites

1. Python 3.8+
2. MCP SDK for Python

## Installation

### 1. Create a virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install dependencies
```bash
pip install "mcp[cli]"
```

### 3. Create requirements.txt
```txt
mcp[cli]>=1.13.0
```

### 4. Make the server executable
```bash
chmod +x vagrant-mcp-server.py
```

## Configuration

### Usage with VS Code

Add the following JSON block to your User Settings (JSON) file in VS Code. You can do this by pressing `Ctrl + Shift + P` and typing `Preferences: Open User Settings (JSON)`. 

More about using MCP server tools in VS Code's [agent mode documentation](https://code.visualstudio.com/docs/copilot/chat/mcp-servers).

```json
{
  "servers": {
    "vagrant": {
      "type": "stdio",
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-v", "${workspaceFolder}:/vagrant-projects:rw",
        "-v", "${userHome}/.vagrant.d:/app/.vagrant.d:rw",
        "--privileged",
        "--network", "host",
        "vagrant-mcp-server"
      ],
      "env": {
        "VAGRANT_PROJECTS_DIR": "/vagrant-projects",
        "VAGRANT_HOME": "/app/.vagrant.d"
      }
    }
  }
}
```

#### Volume mounts

The following volume mounts are configured for the Vagrant MCP server:

- `${workspaceFolder}:/vagrant-projects:rw`: Mounts the workspace folder to the Vagrant projects directory.  This is where the Vagrantfile can be found.
- `/home/$USER/.vagrant.d:/app/.vagrant.d:rw`: Mounts the user's Vagrant home directory to the Vagrant user's Vagrant home directory. This allows Vagrant to access user-specific configurations and files.

#### Environment Variables

The following environment variables are configured for the Vagrant MCP server:

```json
{
  "VAGRANT_PROJECTS_DIR": "/vagrant-projects",
  "VAGRANT_HOME": "/app/.vagrant.d"
}
```

- `VAGRANT_PROJECTS_DIR`: The directory where Vagrant projects are located.
- `VAGRANT_HOME`: The directory where Vagrant stores its data.

### For other MCP clients

Use stdio transport with the command:
```bash
python vagrant_mcp_server.py
```

## Available Tools

The server provides these Vagrant tools:

1. **vagrant_status** - Get machine status
2. **vagrant_up** - Start machines
3. **vagrant_halt** - Stop machines gracefully  
4. **vagrant_destroy** - Destroy machines
5. **vagrant_ssh** - Execute SSH commands
6. **vagrant_provision** - Run provisioners
7. **vagrant_reload** - Restart and reload machines
8. **vagrant_snapshot** - Manage snapshots
9. **vagrant_global_status** - Global status of all environments

## Usage Examples

Once configured, you can ask Claude to:

- "Check the status of my Vagrant machines"
- "Start the web server VM"
- "Run 'ls -la' on the database machine"
- "Create a snapshot called 'before-update'"
- "Provision the development environment"

## Project Structure

```
vagrant-mcp-server/
├── vagrant_mcp_server.py      # Main server implementation
├── requirements.txt           # Python dependencies
├── README.md                 # This file
└── examples/
    └── Vagrantfile           # Example Vagrantfile for testing
```

## Security Considerations

- This server executes Vagrant commands with your user permissions
- It can modify, create, and destroy virtual machines
- Ensure proper access controls if used in shared environments
- Consider running in a restricted directory structure

## Troubleshooting

### Common Issues

1. **Command not found**: Ensure Vagrant is in your PATH
2. **Permission denied**: Make sure the script is executable
3. **MCP connection failed**: Check the configuration file syntax
4. **Python import errors**: Verify MCP SDK is installed in the correct environment

### Debug Mode

Set logging level to DEBUG by modifying the script:
```python
logging.basicConfig(level=logging.DEBUG)
```

### Testing the Server

You can test the server manually using the MCP inspector:
```bash
npx @modelcontextprotocol/inspector python vagrant_mcp_server.py
```

## Contributing

Feel free to extend this server with additional Vagrant commands or improve error handling. Some ideas:

- Add `vagrant box` management commands
- Implement `vagrant plugin` operations  
- Add support for multi-machine operations
- Improve output parsing and formatting
- Add configuration validation

## License

???
