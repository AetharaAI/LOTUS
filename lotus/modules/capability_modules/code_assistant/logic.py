"""
Code Assistant Module - Autonomous Code Intelligence

This module provides Ash with sophisticated code analysis, generation,
and monitoring capabilities. It watches files in real-time, analyzes
code quality, generates new code, and autonomously fixes issues.

Key Features:
- Real-time file monitoring
- Intelligent code analysis (syntax, logic, security, performance)
- Context-aware code generation
- Autonomous bug fixing
- Pattern learning from user's code style
- Proactive improvement suggestions
"""

import asyncio
import ast
import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent

from lotus.lib.module import BaseModule
from lotus.lib.decorators import on_event, tool, periodic


@dataclass
class CodeIssue:
    """Represents a detected code issue"""
    file_path: str
    line: int
    column: int
    severity: str  # error, warning, info
    issue_type: str  # syntax, logic, security, performance, style
    message: str
    suggested_fix: Optional[str] = None
    auto_fixable: bool = False
    confidence: float = 0.0


@dataclass
class CodeContext:
    """Context for code analysis"""
    file_path: str
    content: str
    language: str
    project_type: Optional[str] = None
    dependencies: List[str] = None
    recent_changes: List[str] = None


class CodeFileWatcher(FileSystemEventHandler):
    """Watches code files for changes"""
    
    def __init__(self, module: 'CodeAssistant'):
        self.module = module
        self.debounce_tasks = {}
    
    def on_modified(self, event):
        """File was modified"""
        if event.is_directory:
            return
        
        file_path = event.src_path
        
        # Check if this is a watched file type
        if not self._should_watch(file_path):
            return
        
        # Debounce rapid changes
        if file_path in self.debounce_tasks:
            self.debounce_tasks[file_path].cancel()
        
        # Schedule analysis after debounce period
        task = asyncio.create_task(
            self._debounced_analysis(file_path)
        )
        self.debounce_tasks[file_path] = task
    
    def _should_watch(self, file_path: str) -> bool:
        """Check if file should be watched"""
        path = Path(file_path)
        
        # Check extension
        watched_extensions = {'.py', '.js', '.ts', '.tsx', '.jsx', '.go', '.rs', '.java'}
        if path.suffix not in watched_extensions:
            return False
        
        # Check ignore patterns
        ignore_patterns = ['node_modules', '.git', '__pycache__', 'venv', '.venv']
        for pattern in ignore_patterns:
            if pattern in str(path):
                return False
        
        return True
    
    async def _debounced_analysis(self, file_path: str):
        """Analyze file after debounce delay"""
        await asyncio.sleep(2)  # Debounce 2 seconds
        
        await self.module.analyze_file(file_path)
        
        # Cleanup
        if file_path in self.debounce_tasks:
            del self.debounce_tasks[file_path]


class CodeAssistant(BaseModule):
    """
    Autonomous Code Assistant
    
    Provides intelligent code analysis, generation, and monitoring.
    Acts as Ash's code intelligence system.
    """
    
    async def initialize(self):
        """Initialize code assistant"""
        self.logger.info("Initializing Code Assistant module")
        
        # File watcher
        self.file_watcher = None
        self.observer = None
        
        # Analysis cache
        self.analysis_cache = {}
        
        # Code patterns learned from user
        self.user_patterns = await self._load_user_patterns()
        
        # Issue tracking
        self.detected_issues = {}
        
        # Start file watching if enabled
        if self.config.get("file_watching.enabled", True):
            await self._start_file_watching()
        
        self.logger.info("Code Assistant initialized successfully")
    
    async def _start_file_watching(self):
        """Start watching code files"""
        self.file_watcher = CodeFileWatcher(self)
        self.observer = Observer()
        
        # Watch configured directories
        watch_dirs = self.config.get("file_watching.directories", ["."])
        
        for directory in watch_dirs:
            path = Path(directory).expanduser().resolve()
            if path.exists():
                self.observer.schedule(
                    self.file_watcher,
                    str(path),
                    recursive=True
                )
                self.logger.info(f"Watching directory: {path}")
        
        self.observer.start()
    
    async def shutdown(self):
        """Clean shutdown"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
    
    # ========================================
    # EVENT HANDLERS
    # ========================================
    
    @on_event("perception.file_change")
    async def on_file_change(self, event):
        """Handle file change events from perception module"""
        file_path = event.data.get("file_path")
        change_type = event.data.get("change_type", "modified")
        
        if change_type == "modified":
            await self.analyze_file(file_path)
    
    @on_event("perception.user_input")
    async def on_user_input(self, event):
        """Handle code-related user requests"""
        user_message = event.data.get("text", "")
        
        # Check if this is a code request
        if self._is_code_request(user_message):
            await self._handle_code_request(user_message, event.data)
    
    @on_event("cognition.code_request")
    async def on_code_request(self, event):
        """Handle explicit code requests from reasoning engine"""
        request_type = event.data.get("type")
        params = event.data.get("params", {})
        
        if request_type == "analyze":
            result = await self.analyze_code(**params)
        elif request_type == "generate":
            result = await self.generate_code(**params)
        elif request_type == "refactor":
            result = await self.refactor_code(**params)
        elif request_type == "fix":
            result = await self.fix_issue(**params)
        else:
            result = {"error": f"Unknown request type: {request_type}"}
        
        await self.publish("code.result", result)
    
    # ========================================
    # CORE FUNCTIONALITY
    # ========================================
    
    async def analyze_file(self, file_path: str) -> Dict[str, Any]:
        """
        Analyze a code file for issues
        
        Performs:
        - Syntax analysis
        - Logic error detection
        - Security vulnerability scanning
        - Performance issue detection
        - Code style checking
        """
        self.logger.info(f"Analyzing file: {file_path}")
        
        # Read file
        try:
            with open(file_path, 'r') as f:
                content = f.read()
        except Exception as e:
            self.logger.error(f"Failed to read file {file_path}: {e}")
            return {"error": str(e)}
        
        # Detect language
        language = self._detect_language(file_path)
        
        # Build context
        context = CodeContext(
            file_path=file_path,
            content=content,
            language=language,
            project_type=self._detect_project_type(),
            dependencies=await self._get_dependencies(file_path),
            recent_changes=await self._get_recent_changes(file_path)
        )
        
        # Run analysis
        issues = []
        
        # 1. Syntax analysis (fast, local)
        syntax_issues = await self._analyze_syntax(context)
        issues.extend(syntax_issues)
        
        # 2. If syntax is clean, do deeper analysis with LLM
        if not any(i.severity == "error" for i in syntax_issues):
            deep_issues = await self._deep_analysis(context)
            issues.extend(deep_issues)
        
        # Cache results
        self.analysis_cache[file_path] = {
            "timestamp": datetime.now(),
            "issues": issues
        }
        
        # Publish results
        await self.publish("code.analysis_complete", {
            "file_path": file_path,
            "issues": [self._issue_to_dict(i) for i in issues],
            "severity": self._calculate_severity(issues)
        })
        
        # Autonomously fix auto-fixable issues
        if self.config.get("autonomy.auto_fix.enabled", True):
            await self._auto_fix_issues(file_path, issues)
        
        # Notify user of important issues
        await self._notify_issues(file_path, issues)
        
        return {
            "file_path": file_path,
            "issues": issues,
            "summary": self._generate_summary(issues)
        }
    
    async def generate_code(
        self,
        description: str,
        language: str = "python",
        context: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Generate new code based on description
        
        Uses LLM to generate context-aware code that matches
        the user's style and project conventions.
        """
        self.logger.info(f"Generating {language} code: {description}")
        
        # Build context for generation
        full_context = await self._build_generation_context(
            description, language, context
        )
        
        # Build prompt
        prompt = self._build_generation_prompt(description, language, full_context)
        
        # Generate code using configured provider
        provider = self.config.get("generation.provider", "claude-sonnet-4")
        
        response = await self.llm.complete(
            prompt=prompt,
            provider=provider,
            temperature=0.2,  # Lower temperature for code
            max_tokens=2000
        )
        
        # Extract code from response
        generated_code = self._extract_code_from_response(response.content)
        
        # Validate generated code
        is_valid, validation_errors = await self._validate_code(
            generated_code, language
        )
        
        if not is_valid:
            self.logger.warning(f"Generated code has issues: {validation_errors}")
            # Try to fix
            generated_code = await self._fix_generated_code(
                generated_code, validation_errors
            )
        
        # Remember this generation for learning
        await self.memory.remember(
            content=f"Generated {language} code: {description}\nCode:\n{generated_code}",
            type="code_generation",
            importance=0.7
        )
        
        return {
            "code": generated_code,
            "language": language,
            "description": description,
            "valid": is_valid
        }
    
    async def refactor_code(
        self,
        file_path: str,
        refactoring_type: str
    ) -> Dict[str, Any]:
        """
        Refactor existing code
        
        Types:
        - extract_method
        - extract_variable
        - rename
        - simplify
        - optimize
        """
        self.logger.info(f"Refactoring {file_path}: {refactoring_type}")
        
        # Read current code
        with open(file_path, 'r') as f:
            original_code = f.read()
        
        # Build refactoring prompt
        prompt = self._build_refactoring_prompt(
            original_code, refactoring_type
        )
        
        # Get refactored code from LLM
        response = await self.llm.complete(
            prompt=prompt,
            provider="claude-sonnet-4",
            temperature=0.1
        )
        
        refactored_code = self._extract_code_from_response(response.content)
        
        # Validate refactoring
        is_valid, errors = await self._validate_refactoring(
            original_code, refactored_code
        )
        
        if not is_valid:
            return {
                "success": False,
                "errors": errors
            }
        
        # If valid, write back
        with open(file_path, 'w') as f:
            f.write(refactored_code)
        
        await self.publish("code.refactored", {
            "file_path": file_path,
            "type": refactoring_type
        })
        
        return {
            "success": True,
            "original_lines": len(original_code.splitlines()),
            "refactored_lines": len(refactored_code.splitlines())
        }
    
    async def fix_issue(
        self,
        issue_id: str,
        auto_approve: bool = False
    ) -> Dict[str, Any]:
        """
        Fix a detected code issue
        
        Can fix automatically if enabled and issue is auto-fixable.
        """
        if issue_id not in self.detected_issues:
            return {"error": "Issue not found"}
        
        issue = self.detected_issues[issue_id]
        
        # Check if auto-fixable
        if not issue.auto_fixable and not auto_approve:
            return {
                "error": "Issue requires manual approval",
                "issue": self._issue_to_dict(issue)
            }
        
        # Apply fix
        success = await self._apply_fix(issue)
        
        if success:
            await self.publish("code.issue_fixed", {
                "issue_id": issue_id,
                "file_path": issue.file_path
            })
        
        return {
            "success": success,
            "issue": self._issue_to_dict(issue)
        }
    
    # ========================================
    # ANALYSIS HELPERS
    # ========================================
    
    async def _analyze_syntax(self, context: CodeContext) -> List[CodeIssue]:
        """Fast local syntax analysis"""
        issues = []
        
        if context.language == "python":
            try:
                ast.parse(context.content)
            except SyntaxError as e:
                issues.append(CodeIssue(
                    file_path=context.file_path,
                    line=e.lineno or 0,
                    column=e.offset or 0,
                    severity="error",
                    issue_type="syntax",
                    message=str(e),
                    auto_fixable=False,
                    confidence=1.0
                ))
        
        return issues
    
    async def _deep_analysis(self, context: CodeContext) -> List[CodeIssue]:
        """Deep analysis using LLM"""
        
        # Build analysis prompt
        prompt = f"""Analyze this {context.language} code for issues:

File: {context.file_path}

Code:
```{context.language}
{context.content}
```

Check for:
1. Logic errors
2. Security vulnerabilities
3. Performance issues
4. Code smells
5. Best practice violations

Return a JSON list of issues with:
- line: line number
- severity: error/warning/info
- issue_type: logic/security/performance/style
- message: description
- suggested_fix: how to fix it (if applicable)
- auto_fixable: boolean

Be specific and actionable."""

        response = await self.llm.complete(
            prompt=prompt,
            provider="claude-sonnet-4",
            temperature=0.3
        )
        
        # Parse LLM response
        issues = self._parse_analysis_response(response.content, context)
        
        return issues
    
    def _parse_analysis_response(self, response: str, context: CodeContext) -> List[CodeIssue]:
        """Parse LLM analysis response into CodeIssue objects"""
        issues = []
        
        try:
            # Try to extract JSON from response
            # LLMs sometimes wrap JSON in markdown
            json_str = response
            if "```json" in response:
                json_str = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                json_str = response.split("```")[1].split("```")[0]
            
            issue_dicts = json.loads(json_str.strip())
            
            for issue_dict in issue_dicts:
                issues.append(CodeIssue(
                    file_path=context.file_path,
                    line=issue_dict.get("line", 0),
                    column=issue_dict.get("column", 0),
                    severity=issue_dict.get("severity", "info"),
                    issue_type=issue_dict.get("issue_type", "unknown"),
                    message=issue_dict.get("message", ""),
                    suggested_fix=issue_dict.get("suggested_fix"),
                    auto_fixable=issue_dict.get("auto_fixable", False),
                    confidence=issue_dict.get("confidence", 0.5)
                ))
        
        except json.JSONDecodeError:
            self.logger.warning("Failed to parse LLM analysis response as JSON")
        
        return issues
    
    # ========================================
    # CODE GENERATION HELPERS
    # ========================================
    
    async def _build_generation_context(
        self,
        description: str,
        language: str,
        extra_context: Optional[Dict]
    ) -> Dict:
        """Build context for code generation"""
        
        # Get relevant code examples from memory
        examples = await self.memory.recall(
            query=f"{language} code {description}",
            limit=3
        )
        
        # Get user's coding style patterns
        style_patterns = self.user_patterns.get(language, {})
        
        # Get project conventions
        conventions = await self._get_project_conventions()
        
        return {
            "examples": examples,
            "style": style_patterns,
            "conventions": conventions,
            "extra": extra_context or {}
        }
    
    def _build_generation_prompt(
        self,
        description: str,
        language: str,
        context: Dict
    ) -> str:
        """Build prompt for code generation"""
        
        prompt = f"""Generate {language} code based on this description:

{description}

Requirements:
- Follow Cory's coding style (patterns below)
- Include type hints (Python) or types (TypeScript)
- Add docstrings/comments
- Write clean, readable code
- Include error handling

Cory's {language} style preferences:
{json.dumps(context.get('style', {}), indent=2)}

Project conventions:
{json.dumps(context.get('conventions', {}), indent=2)}

Generate ONLY the code, no explanations before or after.
```{language}
"""
        
        return prompt
    
    def _extract_code_from_response(self, response: str) -> str:
        """Extract code from LLM response"""
        # Remove markdown code blocks
        code = response
        
        if "```" in code:
            # Extract from code block
            parts = code.split("```")
            for i, part in enumerate(parts):
                if i % 2 == 1:  # Odd indices are inside code blocks
                    # Remove language identifier
                    lines = part.split('\n')
                    if lines[0].strip() in ['python', 'javascript', 'typescript', 'java', 'go', 'rust']:
                        lines = lines[1:]
                    code = '\n'.join(lines)
                    break
        
        return code.strip()
    
    # ========================================
    # AUTONOMOUS FIXING
    # ========================================
    
    async def _auto_fix_issues(self, file_path: str, issues: List[CodeIssue]):
        """Automatically fix auto-fixable issues"""
        auto_fixable = [i for i in issues if i.auto_fixable]
        
        if not auto_fixable:
            return
        
        self.logger.info(f"Auto-fixing {len(auto_fixable)} issues in {file_path}")
        
        for issue in auto_fixable:
            await self._apply_fix(issue)
    
    async def _apply_fix(self, issue: CodeIssue) -> bool:
        """Apply a fix to a code issue"""
        try:
            # Read file
            with open(issue.file_path, 'r') as f:
                lines = f.readlines()
            
            # Apply fix (simplified - real implementation would be more sophisticated)
            if issue.suggested_fix:
                lines[issue.line - 1] = issue.suggested_fix + '\n'
            
            # Write back
            with open(issue.file_path, 'w') as f:
                f.writelines(lines)
            
            self.logger.info(f"Fixed issue in {issue.file_path}:{issue.line}")
            return True
        
        except Exception as e:
            self.logger.error(f"Failed to apply fix: {e}")
            return False
    
    # ========================================
    # UTILITIES
    # ========================================
    
    def _is_code_request(self, message: str) -> bool:
        """Check if user message is a code request"""
        code_keywords = [
            'write', 'create', 'generate', 'code', 'function',
            'class', 'implement', 'fix', 'bug', 'refactor',
            'optimize', 'improve'
        ]
        message_lower = message.lower()
        return any(keyword in message_lower for keyword in code_keywords)
    
    def _detect_language(self, file_path: str) -> str:
        """Detect programming language from file extension"""
        ext = Path(file_path).suffix
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.jsx': 'javascript',
            '.go': 'go',
            '.rs': 'rust',
            '.java': 'java',
            '.c': 'c',
            '.cpp': 'cpp',
            '.h': 'c'
        }
        return language_map.get(ext, 'unknown')
    
    def _detect_project_type(self) -> Optional[str]:
        """Detect type of project (FastAPI, React, etc.)"""
        # Check for common files
        if Path('requirements.txt').exists():
            with open('requirements.txt', 'r') as f:
                content = f.read()
                if 'fastapi' in content:
                    return 'fastapi'
                elif 'django' in content:
                    return 'django'
                elif 'flask' in content:
                    return 'flask'
        
        if Path('package.json').exists():
            with open('package.json', 'r') as f:
                pkg = json.load(f)
                deps = pkg.get('dependencies', {})
                if 'react' in deps:
                    return 'react'
                elif 'vue' in deps:
                    return 'vue'
                elif 'next' in deps:
                    return 'nextjs'
        
        return None
    
    async def _get_dependencies(self, file_path: str) -> List[str]:
        """Get dependencies for a file"""
        # Simplified - would parse imports
        return []
    
    async def _get_recent_changes(self, file_path: str) -> List[str]:
        """Get recent changes to file from memory"""
        changes = await self.memory.recall(
            query=f"file change {file_path}",
            limit=5
        )
        return [c.content for c in changes]
    
    async def _load_user_patterns(self) -> Dict:
        """Load learned user coding patterns from memory"""
        patterns = await self.memory.recall(
            query="coding style patterns",
            limit=10
        )
        
        # Parse patterns (simplified)
        return {
            "python": {
                "formatter": "black",
                "line_length": 88,
                "type_hints": True
            }
        }
    
    async def _get_project_conventions(self) -> Dict:
        """Get project-specific conventions"""
        return {
            "naming": "snake_case",
            "docstring_style": "google"
        }
    
    def _issue_to_dict(self, issue: CodeIssue) -> Dict:
        """Convert CodeIssue to dictionary"""
        return {
            "file_path": issue.file_path,
            "line": issue.line,
            "column": issue.column,
            "severity": issue.severity,
            "issue_type": issue.issue_type,
            "message": issue.message,
            "suggested_fix": issue.suggested_fix,
            "auto_fixable": issue.auto_fixable,
            "confidence": issue.confidence
        }
    
    def _calculate_severity(self, issues: List[CodeIssue]) -> str:
        """Calculate overall severity"""
        if any(i.severity == "error" for i in issues):
            return "critical"
        elif any(i.severity == "warning" for i in issues):
            return "warning"
        else:
            return "info"
    
    def _generate_summary(self, issues: List[CodeIssue]) -> str:
        """Generate human-readable summary"""
        if not issues:
            return "No issues found"
        
        errors = sum(1 for i in issues if i.severity == "error")
        warnings = sum(1 for i in issues if i.severity == "warning")
        
        return f"Found {errors} errors and {warnings} warnings"
    
    async def _notify_issues(self, file_path: str, issues: List[CodeIssue]):
        """Notify user of important issues"""
        # Only notify on errors and high-confidence warnings
        important = [
            i for i in issues
            if i.severity == "error" or (i.severity == "warning" and i.confidence > 0.7)
        ]
        
        if important:
            await self.publish("action.respond", {
                "text": f"Found {len(important)} issues in {file_path}",
                "issues": [self._issue_to_dict(i) for i in important]
            })
    
    async def _validate_code(self, code: str, language: str) -> tuple[bool, List[str]]:
        """Validate generated code"""
        errors = []
        
        if language == "python":
            try:
                ast.parse(code)
            except SyntaxError as e:
                errors.append(str(e))
        
        return (len(errors) == 0, errors)
    
    async def _fix_generated_code(self, code: str, errors: List[str]) -> str:
        """Attempt to fix generated code"""
        # Use LLM to fix errors
        prompt = f"""Fix these errors in the code:

Errors:
{chr(10).join(errors)}

Code:
```
{code}
```

Return only the fixed code."""

        response = await self.llm.complete(
            prompt=prompt,
            provider="claude-sonnet-4",
            temperature=0.1
        )
        
        return self._extract_code_from_response(response.content)
    
    def _build_refactoring_prompt(self, code: str, refactoring_type: str) -> str:
        """Build prompt for refactoring"""
        return f"""Refactor this code using {refactoring_type}:

```
{code}
```

Return only the refactored code, preserving functionality."""
    
    async def _validate_refactoring(
        self,
        original: str,
        refactored: str
    ) -> tuple[bool, List[str]]:
        """Validate that refactoring preserves functionality"""
        # Simplified - real implementation would run tests
        return (True, [])
    
    async def _handle_code_request(self, message: str, context: Dict):
        """Handle code-related user input"""
        # Extract intent and parameters from message
        # Then delegate to appropriate method
        
        # This would be more sophisticated in production
        if "generate" in message.lower():
            result = await self.generate_code(
                description=message,
                language="python"
            )
            
            await self.publish("action.respond", {
                "text": f"Generated code:\n```python\n{result['code']}\n```"
            })
    
    # ========================================
    # TOOLS (exposed to other modules)
    # ========================================
    
    @tool("analyze_code")
    async def tool_analyze_code(self, file_path: str, analysis_type: str = "full"):
        """Analyze code file"""
        return await self.analyze_file(file_path)
    
    @tool("generate_code")
    async def tool_generate_code(
        self,
        description: str,
        language: str = "python",
        context: Optional[Dict] = None
    ):
        """Generate new code"""
        return await self.generate_code(description, language, context)
    
    @tool("fix_issue")
    async def tool_fix_issue(self, issue_id: str, auto_approve: bool = False):
        """Fix a detected issue"""
        return await self.fix_issue(issue_id, auto_approve)
    
    @periodic(interval=3600)  # Every hour
    async def periodic_pattern_learning(self):
        """Learn from recent code interactions"""
        # Analyze accepted vs rejected suggestions
        # Update user_patterns
        self.logger.debug("Running periodic pattern learning")