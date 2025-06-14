#!/usr/bin/env python3
"""
File Operations Tool - Safe file system operations

Provides read, write, and list operations with path validation and security checks.
Demonstrates async file I/O and proper error handling patterns.
"""
import os
import asyncio
from pathlib import Path
from typing import Optional

import sys
sys.path.append('..')
from base_tool import BaseTool, ToolResult, ToolError


class FileOperationsTool(BaseTool):
    """
    Safe file system operations with security validation.
    
    Supports:
    - Reading file contents  
    - Writing file contents
    - Listing directory contents
    - Path validation and sandboxing
    """
    
    name = "file_ops"
    description = "Read, write, and list files with security validation"
    
    def __init__(self):
        # Define safe working directory (can be configured)
        self.safe_directory = Path.cwd() / "workspace" 
        self.safe_directory.mkdir(exist_ok=True)
    
    async def execute(self, operation: str, path: str, content: Optional[str] = None) -> ToolResult:
        """
        Execute file operation.
        
        Args:
            operation: Operation type ('read', 'write', 'list')
            path: File or directory path (relative to workspace)
            content: Content to write (required for 'write' operation)
        """
        try:
            # Validate and resolve path
            safe_path = self._validate_path(path)
            
            if operation == "read":
                return await self._read_file(safe_path)
            elif operation == "write":
                if content is None:
                    raise ToolError("Content required for write operation")
                return await self._write_file(safe_path, content)
            elif operation == "list":
                return await self._list_directory(safe_path)
            else:
                raise ToolError(f"Unknown operation: {operation}. Use 'read', 'write', or 'list'")
                
        except ToolError:
            raise
        except Exception as e:
            raise ToolError(f"File operation failed: {str(e)}")
    
    def _validate_path(self, path: str) -> Path:
        """Validate path is safe and within workspace"""
        try:
            # Convert to Path and resolve
            user_path = Path(path)
            
            # Handle absolute paths by making them relative
            if user_path.is_absolute():
                # Strip leading slash/drive to make it relative
                user_path = Path(*user_path.parts[1:]) if user_path.parts else Path(".")
            
            # Resolve relative to safe directory
            full_path = (self.safe_directory / user_path).resolve()
            
            # Security check: ensure path is within safe directory
            try:
                full_path.relative_to(self.safe_directory.resolve())
            except ValueError:
                raise ToolError(f"Path outside safe workspace: {path}")
            
            return full_path
            
        except Exception as e:
            raise ToolError(f"Invalid path: {path} - {str(e)}")
    
    async def _read_file(self, file_path: Path) -> ToolResult:
        """Read file contents asynchronously"""
        if not file_path.exists():
            raise ToolError(f"File not found: {file_path.name}")
        
        if not file_path.is_file():
            raise ToolError(f"Path is not a file: {file_path.name}")
        
        try:
            # Use async file reading
            content = await asyncio.to_thread(file_path.read_text, encoding='utf-8')
            
            result = ToolResult()
            result.add_text(f"📄 File: {file_path.name}")
            result.add_text(f"📏 Size: {len(content)} characters")
            result.add_text(f"\n{content}")
            
            return result
            
        except UnicodeDecodeError:
            raise ToolError(f"File is not valid UTF-8 text: {file_path.name}")
        except Exception as e:
            raise ToolError(f"Failed to read file: {str(e)}")
    
    async def _write_file(self, file_path: Path, content: str) -> ToolResult:
        """Write content to file asynchronously"""
        try:
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Use async file writing
            await asyncio.to_thread(file_path.write_text, content, encoding='utf-8')
            
            result = ToolResult()
            result.add_text(f"✅ File written: {file_path.name}")
            result.add_text(f"📏 Size: {len(content)} characters")
            result.add_text(f"📁 Location: {file_path.relative_to(self.safe_directory)}")
            
            return result
            
        except Exception as e:
            raise ToolError(f"Failed to write file: {str(e)}")
    
    async def _list_directory(self, dir_path: Path) -> ToolResult:
        """List directory contents"""
        if not dir_path.exists():
            raise ToolError(f"Directory not found: {dir_path.name}")
        
        if not dir_path.is_dir():
            raise ToolError(f"Path is not a directory: {dir_path.name}")
        
        try:
            items = list(dir_path.iterdir())
            items.sort(key=lambda x: (x.is_file(), x.name.lower()))
            
            result = ToolResult()
            result.add_text(f"📁 Directory: {dir_path.relative_to(self.safe_directory) or '.'}")
            result.add_text(f"📊 Items: {len(items)}")
            
            if items:
                result.add_text("\n📋 Contents:")
                for item in items:
                    icon = "📄" if item.is_file() else "📁"
                    size_info = ""
                    if item.is_file():
                        try:
                            size = item.stat().st_size
                            size_info = f" ({size} bytes)"
                        except:
                            pass
                    result.add_text(f"  {icon} {item.name}{size_info}")
            else:
                result.add_text("\n📭 Directory is empty")
                
            return result
            
        except Exception as e:
            raise ToolError(f"Failed to list directory: {str(e)}")


# Example usage and testing
if __name__ == "__main__":
    async def test_file_tool():
        tool = FileOperationsTool()
        
        print("🧪 Testing File Operations Tool")
        print(f"Schema: {tool.input_schema}")
        
        # Test write
        write_result = await tool.execute("write", "test.txt", "Hello, MCP World!")
        print(f"Write result: {write_result.to_dict()}")
        
        # Test read
        read_result = await tool.execute("read", "test.txt")
        print(f"Read result: {read_result.to_dict()}")
        
        # Test list
        list_result = await tool.execute("list", ".")
        print(f"List result: {list_result.to_dict()}")
    
    asyncio.run(test_file_tool())
