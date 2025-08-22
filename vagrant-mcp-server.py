#!/usr/bin/env python3
"""
Vagrant MCP Server

A Model Context Protocol server that provides tools for running Vagrant commands
and capturing their output for AI agents to utilize.
"""

import asyncio
import json
import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

# MCP SDK imports
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequestParams,
    TextContent,
    Tool,
    INVALID_PARAMS,
    INTERNAL_ERROR
)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("vagrant-mcp-server")

class VagrantMCPServer:
    def __init__(self):
        self.server = Server("vagrant-mcp-server")
        self.base_projects_dir = os.environ.get("VAGRANT_PROJECTS_DIR", "/vagrant-projects")
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup MCP server handlers"""
        
        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            """List available Vagrant tools"""
            return [
                Tool(
                    name="vagrant_status",
                    description="Get the status of Vagrant machines in the current directory",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "directory": {
                                "type": "string",
                                "description": "Directory parameter (ignored in containerized mode - uses mounted volume)"
                            }
                        }
                    }
                ),
                Tool(
                    name="vagrant_up",
                    description="Start and provision Vagrant machines",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "machine_name": {
                                "type": "string",
                                "description": "Name of specific machine to start (optional)"
                            },
                            "directory": {
                                "type": "string", 
                                "description": "Directory parameter (ignored in containerized mode - uses mounted volume)"
                            },
                            "provider": {
                                "type": "string",
                                "description": "Vagrant provider to use (e.g., virtualbox, vmware)"
                            },
                            "provision": {
                                "type": "boolean",
                                "description": "Whether to run provisioners",
                                "default": True
                            }
                        }
                    }
                ),
                Tool(
                    name="vagrant_halt",
                    description="Stop Vagrant machines gracefully",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "machine_name": {
                                "type": "string",
                                "description": "Name of specific machine to stop (optional)"
                            },
                            "directory": {
                                "type": "string",
                                "description": "Directory containing Vagrantfile"
                            },
                            "force": {
                                "type": "boolean", 
                                "description": "Force halt the machine",
                                "default": False
                            }
                        }
                    }
                ),
                Tool(
                    name="vagrant_destroy",
                    description="Destroy Vagrant machines and remove all traces",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "machine_name": {
                                "type": "string",
                                "description": "Name of specific machine to destroy (optional)"
                            },
                            "directory": {
                                "type": "string",
                                "description": "Directory containing Vagrantfile" 
                            },
                            "force": {
                                "type": "boolean",
                                "description": "Force destroy without confirmation",
                                "default": False
                            }
                        }
                    }
                ),
                Tool(
                    name="vagrant_ssh",
                    description="Execute commands via SSH on Vagrant machine",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "command": {
                                "type": "string",
                                "description": "Command to execute on the machine"
                            },
                            "machine_name": {
                                "type": "string",
                                "description": "Name of machine to SSH into (optional if only one machine)"
                            },
                            "directory": {
                                "type": "string",
                                "description": "Directory containing Vagrantfile"
                            }
                        },
                        "required": ["command"]
                    }
                ),
                Tool(
                    name="vagrant_provision",
                    description="Run provisioners on Vagrant machines",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "machine_name": {
                                "type": "string",
                                "description": "Name of specific machine to provision (optional)"
                            },
                            "directory": {
                                "type": "string",
                                "description": "Directory containing Vagrantfile"
                            },
                            "provision_with": {
                                "type": "string",
                                "description": "Specific provisioner to run"
                            }
                        }
                    }
                ),
                Tool(
                    name="vagrant_reload",
                    description="Restart Vagrant machines and reload Vagrantfile",
                    inputSchema={
                        "type": "object", 
                        "properties": {
                            "machine_name": {
                                "type": "string",
                                "description": "Name of specific machine to reload (optional)"
                            },
                            "directory": {
                                "type": "string",
                                "description": "Directory containing Vagrantfile"
                            },
                            "provision": {
                                "type": "boolean",
                                "description": "Whether to run provisioners after reload",
                                "default": False
                            }
                        }
                    }
                ),
                Tool(
                    name="vagrant_snapshot",
                    description="Manage Vagrant snapshots",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "action": {
                                "type": "string",
                                "enum": ["save", "restore", "list", "delete"],
                                "description": "Snapshot action to perform"
                            },
                            "snapshot_name": {
                                "type": "string", 
                                "description": "Name of the snapshot (required for save, restore, delete)"
                            },
                            "machine_name": {
                                "type": "string",
                                "description": "Name of machine for snapshot operation"
                            },
                            "directory": {
                                "type": "string",
                                "description": "Directory containing Vagrantfile"
                            }
                        },
                        "required": ["action"]
                    }
                ),
                Tool(
                    name="vagrant_global_status", 
                    description="Get global status of all Vagrant environments",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "prune": {
                                "type": "boolean",
                                "description": "Prune invalid entries",
                                "default": False
                            }
                        }
                    }
                )
            ]

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: dict | None
        ) -> list[TextContent]:
            """Handle tool calls"""
            try:
                if name == "vagrant_status":
                    return await self._vagrant_status(arguments or {})
                elif name == "vagrant_up":
                    return await self._vagrant_up(arguments or {})
                elif name == "vagrant_halt":
                    return await self._vagrant_halt(arguments or {})
                elif name == "vagrant_destroy":
                    return await self._vagrant_destroy(arguments or {})
                elif name == "vagrant_ssh":
                    return await self._vagrant_ssh(arguments or {})
                elif name == "vagrant_provision":
                    return await self._vagrant_provision(arguments or {})
                elif name == "vagrant_reload":
                    return await self._vagrant_reload(arguments or {})
                elif name == "vagrant_snapshot":
                    return await self._vagrant_snapshot(arguments or {})
                elif name == "vagrant_global_status":
                    return await self._vagrant_global_status(arguments or {})
                else:
                    raise ValueError(f"Unknown tool: {name}")
                    
            except Exception as e:
                logger.error(f"Error executing tool {name}: {e}")
                return [TextContent(type="text", text=f"Error: {str(e)}")]

    def _get_working_directory(self, requested_dir: Optional[str] = None) -> str:
        """Get the working directory, handling container volume mounts"""
        # In containerized mode, always use the mounted volume directory
        # The requested_dir parameter is ignored since we're working within a mounted volume
        # that contains the Vagrant project
        
        # Always use the base projects directory (the mounted volume)
        return self.base_projects_dir

    async def _run_vagrant_command(
        self, 
        args: List[str], 
        directory: Optional[str] = None,
        input_text: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run a vagrant command and capture output"""
        try:
            cmd = ["vagrant"] + args
            cwd = self._get_working_directory(directory)
            
            # Verify the directory exists and contains a Vagrantfile (for most operations)
            if not os.path.exists(cwd):
                return {
                    "command": " ".join(cmd),
                    "return_code": -1,
                    "stdout": "",
                    "stderr": f"Directory does not exist: {cwd}",
                    "success": False
                }
            
            # Check for Vagrantfile unless it's a global command
            if args[0] not in ["global-status"] and not os.path.exists(os.path.join(cwd, "Vagrantfile")):
                return {
                    "command": " ".join(cmd),
                    "return_code": -1,
                    "stdout": "",
                    "stderr": f"No Vagrantfile found in: {cwd}",
                    "success": False
                }
            
            logger.info(f"Running command: {' '.join(cmd)} in {cwd}")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=cwd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE if input_text else None
            )
            
            stdout, stderr = await process.communicate(
                input=input_text.encode() if input_text else None
            )
            
            return {
                "command": " ".join(cmd),
                "return_code": process.returncode,
                "stdout": stdout.decode('utf-8', errors='replace'),
                "stderr": stderr.decode('utf-8', errors='replace'),
                "success": process.returncode == 0,
                "working_directory": cwd
            }
            
        except Exception as e:
            logger.error(f"Failed to run vagrant command: {e}")
            return {
                "command": " ".join(cmd) if 'cmd' in locals() else "unknown",
                "return_code": -1,
                "stdout": "",
                "stderr": str(e),
                "success": False,
                "working_directory": cwd if 'cwd' in locals() else "unknown"
            }

    async def _vagrant_status(self, args: dict) -> list[TextContent]:
        """Get vagrant machine status"""
        directory = args.get("directory")
        result = await self._run_vagrant_command(["status"], directory)
        
        response = f"Vagrant Status:\n"
        response += f"Command: {result['command']}\n"
        response += f"Working Directory: {result.get('working_directory', 'unknown')}\n"
        response += f"Return Code: {result['return_code']}\n\n"
        
        if result['success']:
            response += f"Output:\n{result['stdout']}"
        else:
            response += f"Error:\n{result['stderr']}"
            
        return [TextContent(type="text", text=response)]

    async def _vagrant_up(self, args: dict) -> list[TextContent]:
        """Start vagrant machines"""
        cmd_args = ["up"]
        
        if args.get("machine_name"):
            cmd_args.append(args["machine_name"])
            
        if args.get("provider"):
            cmd_args.extend(["--provider", args["provider"]])
            
        if args.get("provision", True) is False:
            cmd_args.append("--no-provision")
            
        result = await self._run_vagrant_command(cmd_args, args.get("directory"))
        
        response = f"Vagrant Up:\n"
        response += f"Command: {result['command']}\n"
        response += f"Return Code: {result['return_code']}\n\n"
        
        if result['success']:
            response += f"Output:\n{result['stdout']}"
        else:
            response += f"Error:\n{result['stderr']}"
            
        return [TextContent(type="text", text=response)]

    async def _vagrant_halt(self, args: dict) -> list[TextContent]:
        """Halt vagrant machines"""
        cmd_args = ["halt"]
        
        if args.get("machine_name"):
            cmd_args.append(args["machine_name"])
            
        if args.get("force", False):
            cmd_args.append("--force")
            
        result = await self._run_vagrant_command(cmd_args, args.get("directory"))
        
        response = f"Vagrant Halt:\n"
        response += f"Command: {result['command']}\n"
        response += f"Return Code: {result['return_code']}\n\n"
        
        if result['success']:
            response += f"Output:\n{result['stdout']}"
        else:
            response += f"Error:\n{result['stderr']}"
            
        return [TextContent(type="text", text=response)]

    async def _vagrant_destroy(self, args: dict) -> list[TextContent]:
        """Destroy vagrant machines"""
        cmd_args = ["destroy"]
        
        if args.get("machine_name"):
            cmd_args.append(args["machine_name"])
            
        if args.get("force", False):
            cmd_args.append("--force")
            
        input_text = "y\n" if not args.get("force", False) else None
        result = await self._run_vagrant_command(
            cmd_args, args.get("directory"), input_text
        )
        
        response = f"Vagrant Destroy:\n"
        response += f"Command: {result['command']}\n"
        response += f"Return Code: {result['return_code']}\n\n"
        
        if result['success']:
            response += f"Output:\n{result['stdout']}"
        else:
            response += f"Error:\n{result['stderr']}"
            
        return [TextContent(type="text", text=response)]

    async def _vagrant_ssh(self, args: dict) -> list[TextContent]:
        """Execute SSH commands on vagrant machines"""
        if not args.get("command"):
            raise ValueError("command parameter is required")
            
        cmd_args = ["ssh"]
        
        if args.get("machine_name"):
            cmd_args.append(args["machine_name"])
            
        cmd_args.extend(["-c", args["command"]])
        
        result = await self._run_vagrant_command(cmd_args, args.get("directory"))
        
        response = f"Vagrant SSH Command:\n"
        response += f"Command: {result['command']}\n"
        response += f"Return Code: {result['return_code']}\n\n"
        
        if result['success']:
            response += f"Output:\n{result['stdout']}"
        else:
            response += f"Error:\n{result['stderr']}"
            
        return [TextContent(type="text", text=response)]

    async def _vagrant_provision(self, args: dict) -> list[TextContent]:
        """Run provisioners on vagrant machines"""
        cmd_args = ["provision"]
        
        if args.get("machine_name"):
            cmd_args.append(args["machine_name"])
            
        if args.get("provision_with"):
            cmd_args.extend(["--provision-with", args["provision_with"]])
            
        result = await self._run_vagrant_command(cmd_args, args.get("directory"))
        
        response = f"Vagrant Provision:\n"
        response += f"Command: {result['command']}\n"
        response += f"Return Code: {result['return_code']}\n\n"
        
        if result['success']:
            response += f"Output:\n{result['stdout']}"
        else:
            response += f"Error:\n{result['stderr']}"
            
        return [TextContent(type="text", text=response)]

    async def _vagrant_reload(self, args: dict) -> list[TextContent]:
        """Reload vagrant machines"""
        cmd_args = ["reload"]
        
        if args.get("machine_name"):
            cmd_args.append(args["machine_name"])
            
        if args.get("provision", False):
            cmd_args.append("--provision")
            
        result = await self._run_vagrant_command(cmd_args, args.get("directory"))
        
        response = f"Vagrant Reload:\n"
        response += f"Command: {result['command']}\n"
        response += f"Return Code: {result['return_code']}\n\n"
        
        if result['success']:
            response += f"Output:\n{result['stdout']}"
        else:
            response += f"Error:\n{result['stderr']}"
            
        return [TextContent(type="text", text=response)]

    async def _vagrant_snapshot(self, args: dict) -> list[TextContent]:
        """Manage vagrant snapshots"""
        action = args.get("action")
        if not action:
            raise ValueError("action parameter is required")
            
        cmd_args = ["snapshot", action]
        
        if action in ["save", "restore", "delete"] and not args.get("snapshot_name"):
            raise ValueError(f"snapshot_name is required for {action} action")
            
        if args.get("snapshot_name"):
            cmd_args.append(args["snapshot_name"])
            
        if args.get("machine_name"):
            cmd_args.append(args["machine_name"])
            
        result = await self._run_vagrant_command(cmd_args, args.get("directory"))
        
        response = f"Vagrant Snapshot {action.title()}:\n"
        response += f"Command: {result['command']}\n"
        response += f"Return Code: {result['return_code']}\n\n"
        
        if result['success']:
            response += f"Output:\n{result['stdout']}"
        else:
            response += f"Error:\n{result['stderr']}"
            
        return [TextContent(type="text", text=response)]

    async def _vagrant_global_status(self, args: dict) -> list[TextContent]:
        """Get global vagrant status"""
        cmd_args = ["global-status"]
        
        if args.get("prune", False):
            cmd_args.append("--prune")
            
        result = await self._run_vagrant_command(cmd_args)
        
        response = f"Vagrant Global Status:\n"
        response += f"Command: {result['command']}\n"
        response += f"Return Code: {result['return_code']}\n\n"
        
        if result['success']:
            response += f"Output:\n{result['stdout']}"
        else:
            response += f"Error:\n{result['stderr']}"
            
        return [TextContent(type="text", text=response)]

    async def run(self):
        """Run the MCP server"""
        async with stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="vagrant-mcp-server",
                    server_version="0.1.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={}
                    )
                )
            )

async def main():
    """Main entry point"""
    server = VagrantMCPServer()
    await server.run()

if __name__ == "__main__":
    asyncio.run(main())