"""
Test Coverage Analyzer - Discover testing gaps and opportunities
"""
import asyncio
import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Set
from pathlib import Path
import ast
import re

logger = logging.getLogger(__name__)

class TestCoverageAnalyzer:
    """Analyze codebase for testing gaps and opportunities"""
    
    def __init__(self, config: dict):
        self.config = config
        self.root_path = config.get('root_path', '.')
        self.source_dirs = config.get('source_dirs', ['src', 'lib', 'app'])
        self.test_dirs = config.get('test_dirs', ['tests', 'test', '__tests__', 'spec'])
        self.excluded_dirs = config.get('excluded_dirs', [
            "node_modules", ".git", "__pycache__", 
            "venv", ".venv", "env", ".env", "ENV", 
            "env.bak", "venv.bak", "virtualenv",
            "build", "dist", ".tox", ".nox",
            "coverage", "htmlcov", ".pytest_cache",
            ".sugar", ".claude"
        ])
        self.test_file_patterns = config.get('test_file_patterns', [
            r'test_.*\.py$', r'.*_test\.py$', r'.*\.test\.(js|ts)$', r'.*\.spec\.(js|ts)$'
        ])
    
    def _should_exclude_path(self, path: str) -> bool:
        """Check if a path should be excluded based on excluded_dirs configuration"""
        path_obj = Path(path)
        
        # Check if any part of the path matches excluded directories
        for part in path_obj.parts:
            if part in self.excluded_dirs:
                return True
        
        # Check if the path contains any excluded patterns
        path_str = str(path_obj)
        for excluded in self.excluded_dirs:
            if excluded in path_str:
                return True
                
        return False
        
    async def discover(self) -> List[Dict[str, Any]]:
        """Discover testing gaps and opportunities"""
        work_items = []
        
        try:
            # Find source files without tests
            untested_files = await self._find_untested_files()
            for file_path in untested_files:
                work_item = self._create_test_work_item(file_path, 'missing_tests')
                if work_item:
                    work_items.append(work_item)
            
            # Find test files with issues
            test_issues = await self._analyze_test_quality()
            for issue in test_issues:
                work_item = self._create_test_work_item(
                    issue['file_path'], 
                    'improve_tests', 
                    issue
                )
                if work_item:
                    work_items.append(work_item)
            
            # Find complex functions needing tests
            complex_functions = await self._find_complex_functions()
            for func_info in complex_functions:
                work_item = self._create_test_work_item(
                    func_info['file_path'], 
                    'test_complex_function',
                    func_info
                )
                if work_item:
                    work_items.append(work_item)
                    
        except Exception as e:
            logger.error(f"Error in test coverage analysis: {e}")
        
        # Prioritize and limit results
        work_items = self._prioritize_test_work(work_items)
        
        logger.info(f"🔍 TestCoverageAnalyzer discovered {len(work_items)} work items")
        return work_items
    
    async def _find_untested_files(self) -> List[str]:
        """Find source files that don't have corresponding test files"""
        source_files = []
        test_files = set()
        
        # Collect all source files
        for root, dirs, files in os.walk(self.root_path):
            # Skip excluded directories
            if self._should_exclude_path(root):
                dirs[:] = []  # Don't recurse into this directory
                continue
                
            # Filter out excluded subdirectories before walking into them
            dirs[:] = [d for d in dirs if not self._should_exclude_path(os.path.join(root, d))]
            
            # Skip non-source directories early
            path_parts = Path(root).parts
            if not any(src_dir in path_parts for src_dir in self.source_dirs):
                continue
            
            for file in files:
                file_path = os.path.join(root, file)
                
                # Skip excluded files
                if self._should_exclude_path(file_path):
                    continue
                    
                if file.endswith(('.py', '.js', '.ts', '.jsx', '.tsx')):
                    source_files.append(file_path)
        
        # Collect all test files and extract what they might be testing
        for root, dirs, files in os.walk(self.root_path):
            # Skip excluded directories
            if self._should_exclude_path(root):
                dirs[:] = []  # Don't recurse into this directory
                continue
                
            # Filter out excluded subdirectories before walking into them
            dirs[:] = [d for d in dirs if not self._should_exclude_path(os.path.join(root, d))]
            
            for file in files:
                file_path = os.path.join(root, file)
                
                # Skip excluded files
                if self._should_exclude_path(file_path):
                    continue
                    
                if self._is_test_file(file):
                    test_files.add(self._extract_tested_module_name(file))
        
        # Find source files without corresponding tests
        untested_files = []
        for source_file in source_files[:20]:  # Limit to avoid overwhelming
            module_name = self._extract_module_name(source_file)
            if module_name not in test_files:
                untested_files.append(source_file)
        
        return untested_files
    
    def _is_test_file(self, filename: str) -> bool:
        """Check if a file is a test file based on patterns"""
        for pattern in self.test_file_patterns:
            if re.search(pattern, filename):
                return True
        return False
    
    def _extract_module_name(self, file_path: str) -> str:
        """Extract module name from source file path"""
        filename = os.path.basename(file_path)
        name, _ = os.path.splitext(filename)
        return name.lower()
    
    def _extract_tested_module_name(self, test_filename: str) -> str:
        """Extract the module name that a test file is testing"""
        # test_auth.py -> auth
        # auth_test.py -> auth  
        # auth.test.js -> auth
        name = test_filename.lower()
        
        # Remove test prefixes/suffixes
        patterns_to_remove = [
            r'^test_', r'_test$', r'\.test$', r'\.spec$'
        ]
        
        for pattern in patterns_to_remove:
            name = re.sub(pattern, '', name)
        
        # Remove file extensions
        name = re.sub(r'\.(py|js|ts|jsx|tsx)$', '', name)
        
        return name
    
    async def _analyze_test_quality(self) -> List[Dict[str, Any]]:
        """Analyze existing test files for quality issues"""
        test_issues = []
        
        for root, dirs, files in os.walk(self.root_path):
            for file in files:
                if self._is_test_file(file):
                    file_path = os.path.join(root, file)
                    
                    try:
                        issues = await self._analyze_test_file(file_path)
                        test_issues.extend(issues)
                    except Exception as e:
                        logger.debug(f"Error analyzing test file {file_path}: {e}")
        
        return test_issues
    
    async def _analyze_test_file(self, file_path: str) -> List[Dict[str, Any]]:
        """Analyze a single test file for issues"""
        issues = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            lines = content.split('\n')
            
            if file_path.endswith('.py'):
                issues.extend(await self._analyze_python_test_file(file_path, content))
            elif file_path.endswith(('.js', '.ts', '.jsx', '.tsx')):
                issues.extend(await self._analyze_js_test_file(file_path, content))
            
            # Generic test issues
            test_function_count = len([line for line in lines 
                                    if re.search(r'def test_|it\(|test\(', line)])
            
            if test_function_count < 3:
                issues.append({
                    'type': 'insufficient_tests',
                    'file_path': file_path,
                    'description': f"Only {test_function_count} test functions found",
                    'suggestion': "Add more comprehensive test cases"
                })
            
        except Exception as e:
            logger.debug(f"Could not analyze test file {file_path}: {e}")
        
        return issues
    
    async def _analyze_python_test_file(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Analyze Python test file"""
        issues = []
        
        try:
            tree = ast.parse(content)
            
            test_methods = []
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                    test_methods.append(node)
            
            # Check for missing assertions
            for method in test_methods:
                has_assert = any(
                    isinstance(n, ast.Assert) or 
                    (isinstance(n, ast.Call) and 
                     isinstance(n.func, ast.Attribute) and 
                     n.func.attr.startswith('assert'))
                    for n in ast.walk(method)
                )
                
                if not has_assert:
                    issues.append({
                        'type': 'missing_assertions',
                        'file_path': file_path,
                        'description': f"Test method '{method.name}' lacks assertions",
                        'suggestion': f"Add assertions to verify {method.name} behavior"
                    })
        
        except SyntaxError:
            issues.append({
                'type': 'test_syntax_error',
                'file_path': file_path,
                'description': "Test file has syntax errors",
                'suggestion': "Fix syntax errors in test file"
            })
        
        return issues
    
    async def _analyze_js_test_file(self, file_path: str, content: str) -> List[Dict[str, Any]]:
        """Analyze JavaScript/TypeScript test file"""
        issues = []
        lines = content.split('\n')
        
        # Count test functions
        test_patterns = [r'\bit\(', r'\btest\(', r'\bdescribe\(']
        test_count = sum(
            len(re.findall(pattern, line)) 
            for line in lines 
            for pattern in test_patterns
        )
        
        # Count expect statements
        expect_count = sum(
            len(re.findall(r'\bexpect\(', line))
            for line in lines
        )
        
        # Check assertion to test ratio
        if test_count > 0 and expect_count / test_count < 1:
            issues.append({
                'type': 'insufficient_assertions',
                'file_path': file_path,
                'description': f"Low assertion to test ratio ({expect_count}/{test_count})",
                'suggestion': "Add more assertions to test cases"
            })
        
        return issues
    
    async def _find_complex_functions(self) -> List[Dict[str, Any]]:
        """Find complex functions that need testing"""
        complex_functions = []
        
        # Debug: Test the exclusion logic with a known problematic path
        test_path = "./venv/lib/python3.13/site-packages/typing_extensions.py"
        should_exclude = self._should_exclude_path(test_path)
        logger.info(f"Testing exclusion for {test_path}: should_exclude = {should_exclude}")
        
        for root, dirs, files in os.walk(self.root_path):
            # Skip excluded directories
            if self._should_exclude_path(root):
                logger.debug(f"Skipping excluded directory: {root}")
                dirs[:] = []  # Don't recurse into this directory
                continue
                
            # Filter out excluded subdirectories before walking into them
            original_dirs = dirs[:]
            dirs[:] = [d for d in dirs if not self._should_exclude_path(os.path.join(root, d))]
            if len(dirs) != len(original_dirs):
                excluded_dirs = [d for d in original_dirs if d not in dirs]
                logger.debug(f"Filtered out excluded subdirectories from {root}: {excluded_dirs}")
            
            # Focus on source directories (but only if not already excluded)
            path_parts = Path(root).parts
            if not any(src_dir in path_parts for src_dir in self.source_dirs):
                continue
            
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    
                    # Skip excluded files (double-check at file level)
                    if self._should_exclude_path(file_path):
                        logger.debug(f"Skipping excluded file: {file_path}")
                        continue
                    
                    try:
                        functions = await self._analyze_python_complexity(file_path)
                        complex_functions.extend(functions)
                    except Exception as e:
                        logger.debug(f"Error analyzing complexity in {file_path}: {e}")
        
        return complex_functions[:5]  # Limit to top 5 most complex
    
    async def _analyze_python_complexity(self, file_path: str) -> List[Dict[str, Any]]:
        """Analyze Python file for complex functions"""
        complex_functions = []
        
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            tree = ast.parse(content)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    complexity = self._calculate_cyclomatic_complexity(node)
                    line_count = getattr(node, 'end_lineno', node.lineno) - node.lineno
                    
                    if complexity > 5 or line_count > 20:  # Thresholds for complexity
                        complex_functions.append({
                            'file_path': file_path,
                            'function_name': node.name,
                            'complexity': complexity,
                            'line_count': line_count,
                            'line_number': node.lineno
                        })
        
        except Exception as e:
            logger.debug(f"Could not analyze complexity in {file_path}: {e}")
        
        return complex_functions
    
    def _calculate_cyclomatic_complexity(self, node: ast.FunctionDef) -> int:
        """Calculate basic cyclomatic complexity"""
        complexity = 1  # Base complexity
        
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
        
        return complexity
    
    def _create_test_work_item(self, file_path: str, work_type: str, 
                             details: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create work item for testing tasks"""
        
        filename = os.path.basename(file_path)
        details = details or {}
        
        work_types = {
            'missing_tests': {
                'type': 'test',
                'title': f"Add tests for {filename}",
                'priority': 3,
                'description': f"**Missing Test Coverage**\n\nFile: {file_path}\n\nThis source file appears to lack corresponding test coverage. Adding tests will help ensure code reliability and catch regressions."
            },
            'improve_tests': {
                'type': 'test',
                'title': f"Improve test quality in {filename}",
                'priority': 2,
                'description': f"**Test Quality Issues**\n\nFile: {file_path}\n\nIssue: {details.get('description', 'Quality issues detected')}\n\nSuggestion: {details.get('suggestion', 'Improve test coverage and quality')}"
            },
            'test_complex_function': {
                'type': 'test',
                'title': f"Add tests for complex function in {filename}",
                'priority': 4,
                'description': f"**Complex Function Needs Testing**\n\nFile: {file_path}\nFunction: {details.get('function_name', 'Unknown')}\nComplexity: {details.get('complexity', 'High')}\nLines: {details.get('line_count', 'Many')}\n\nThis complex function should have comprehensive test coverage to ensure reliability."
            }
        }
        
        template = work_types.get(work_type, work_types['missing_tests'])
        
        work_item = {
            'type': template['type'],
            'title': template['title'],
            'description': template['description'],
            'priority': template['priority'],
            'source': 'test_coverage',
            'source_file': file_path,
            'context': {
                'test_analysis': {
                    'work_type': work_type,
                    'details': details,
                    'discovered_at': datetime.utcnow().isoformat(),
                    'source_type': 'test_coverage'
                }
            }
        }
        
        return work_item
    
    def _prioritize_test_work(self, work_items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize and limit test work items"""
        
        # Sort by priority (high to low)
        work_items.sort(key=lambda x: x['priority'], reverse=True)
        
        # Limit total items and remove duplicates
        seen_files = set()
        filtered_items = []
        
        for item in work_items:
            file_path = item['source_file']
            if file_path not in seen_files:
                seen_files.add(file_path)
                filtered_items.append(item)
        
        return filtered_items[:8]  # Limit to 8 test-related tasks
    
    async def health_check(self) -> dict:
        """Return health status of test coverage analyzer"""
        return {
            "enabled": True,
            "root_path": self.root_path,
            "source_dirs": self.source_dirs,
            "test_dirs": self.test_dirs,
            "test_patterns": self.test_file_patterns
        }