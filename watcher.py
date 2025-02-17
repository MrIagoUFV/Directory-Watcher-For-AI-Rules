import os
import json
import time
from pathlib import Path
import fnmatch

class DirectoryWatcher:
    def __init__(self, use_cursor=True, use_windsurf=True, use_copilot=True, interval=30, log_callback=None):
        self.use_cursor = use_cursor
        self.use_windsurf = use_windsurf
        self.use_copilot = use_copilot
        self.interval = interval
        self.log_callback = log_callback or print
        self.is_running = True

    def load_gitignore(self):
        """Load rules from .gitignore file"""
        gitignore_path = Path('.gitignore')
        if not gitignore_path.exists():
            return []
        
        with open(gitignore_path, 'r', encoding='utf-8') as f:
            rules = [line.strip() for line in f if line.strip() and not line.startswith('#')]
        return rules

    def should_ignore(self, path, ignore_rules):
        """Check if a path should be ignored based on gitignore rules"""
        # Never ignore files in root
        if len(path.parts) == 1:
            return False
            
        # Convert path to gitignore format
        path_str = str(path.relative_to('.'))
        
        # Check if path matches any gitignore rule
        for rule in ignore_rules:
            # Check full path
            if fnmatch.fnmatch(path_str, rule):
                return True
            # Check if any part matches the rule
            if fnmatch.fnmatch(path_str, f"*/{rule}"):
                return True
            # Check if rule is a directory (ends with /)
            if rule.endswith('/'):
                rule = rule[:-1]  # Remove slash
                parts = path_str.split(os.sep)
                if rule in parts:
                    return True
        
        return False

    def get_directory_structure(self, ignore_rules):
        """Analyze directory structure, ignoring gitignore patterns"""
        structure = {}
        root_path = Path('.')

        for path in root_path.rglob('*'):
            # Check if should ignore based on gitignore rules
            if self.should_ignore(path, ignore_rules):
                continue

            # Build structure
            current = structure
            parts = [p for p in path.parts if p != '.']
            
            for i, part in enumerate(parts):
                is_last = i == len(parts) - 1
                if part not in current:
                    if is_last:
                        current[part] = None if path.is_file() else {}
                    else:
                        current[part] = {}
                if not is_last:
                    current = current[part]

        return structure

    def update_rules_file(self, structure, filename, create_message=None):
        """Update a rules file with new structure"""
        rules_path = Path(filename)
        
        # Load or create file content
        if rules_path.exists():
            try:
                with open(rules_path, 'r', encoding='utf-8') as f:
                    try:
                        data = json.load(f)
                    except json.JSONDecodeError:
                        # If file exists but isn't valid JSON, create new
                        data = {}
            except Exception:
                data = {}
        else:
            # If file doesn't exist, create new
            data = {}
            if create_message:
                self.log_callback(create_message)

        # Check if structure changed
        if data.get('directory-structure') != structure:
            # Update or add key keeping rest of content
            data['directory-structure'] = structure
            
            try:
                # Save formatted file
                with open(rules_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
                return True
            except Exception as e:
                self.log_callback(f"Error saving file {filename}: {e}")
                return False
        
        return False

    def update_cursorrules(self, structure):
        """Update .cursorrules file with new structure"""
        return self.update_rules_file(
            structure,
            '.cursorrules',
            create_message="📄 Creating .cursorrules file..."
        )

    def update_windsurfrules(self, structure):
        """Update .windsurfrules file with new structure"""
        return self.update_rules_file(
            structure,
            '.windsurfrules',
            create_message="📄 Creating .windsurfrules file..."
        )

    def update_copilot_instructions(self, structure):
        """Update VSCode Copilot file with new structure"""
        github_dir = Path('.github')
        if not github_dir.exists():
            github_dir.mkdir(exist_ok=True)
            self.log_callback("📁 Creating .github/ directory")
        
        copilot_file = github_dir / 'copilot-instructions.md'
        
        # Create file with initial content if doesn't exist
        if not copilot_file.exists():
            self.log_callback("📄 Creating copilot-instructions.md file...")
            initial_content = """# Copilot Instructions

This file contains instructions for GitHub Copilot about the project structure.

## Project Structure

The following JSON represents the current project structure:

```json
{
    "directory-structure": {}
}
```
"""
            with open(copilot_file, 'w', encoding='utf-8') as f:
                f.write(initial_content)
        
        # Read current content
        with open(copilot_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Convert structure to formatted JSON
        new_json = json.dumps({"directory-structure": structure}, indent=4, ensure_ascii=False)
        
        # If JSON block exists, replace it
        if '```json' in content:
            # Find start and end of JSON block
            start = content.find('```json')
            end = content.find('```', start + 6)
            if end != -1:
                # Replace existing JSON
                new_content = content[:start] + '```json\n' + new_json + '\n```' + content[end + 3:]
                
                # Save only if content changed
                if new_content != content:
                    with open(copilot_file, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    return True
        else:
            # If no JSON block exists, add at end
            new_content = content.rstrip() + '\n\n```json\n' + new_json + '\n```\n'
            with open(copilot_file, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
        
        return False

    def run(self):
        """Main monitoring loop"""
        self.log_callback("🔍 Starting directory monitoring...")
        self.is_running = True
        
        while self.is_running:
            try:
                # Load gitignore rules
                ignore_rules = self.load_gitignore()
                
                # Get current structure
                structure = self.get_directory_structure(ignore_rules)
                
                # Update files based on settings
                updated = False
                if self.use_cursor:
                    updated |= self.update_cursorrules(structure)
                if self.use_windsurf:
                    updated |= self.update_windsurfrules(structure)
                if self.use_copilot:
                    updated |= self.update_copilot_instructions(structure)
                
                # Show message if any file was updated
                if updated:
                    self.log_callback(f"✅ Structure updated at {time.strftime('%H:%M:%S')}")
                
                # Wait for next update
                time.sleep(self.interval)
                
            except Exception as e:
                self.log_callback(f"❌ Error: {e}")
                time.sleep(self.interval)

    def stop(self):
        """Stop the monitoring loop"""
        self.is_running = False

def main():
    """CLI entry point"""
    watcher = DirectoryWatcher()
    try:
        watcher.run()
    except KeyboardInterrupt:
        print("\n👋 Monitoring finished")

if __name__ == '__main__':
    main() 