# main.py
import os
import json
from git import Repo
from github import Github
from pathlib import Path
import pickle
from typing import Dict, List, Optional
from dataclasses import dataclass
import logging
from pydriller import Repository
from tree_sitter import Language, Parser

@dataclass
class FileContext:
    path: str
    content: str
    language: str
    imports: List[str]
    dependencies: List[str]
    description: str

@dataclass
class RepoContext:
    repo_name: str
    branch: str
    files: List[FileContext]
    structure: Dict
    main_languages: List[str]
    dependencies: Dict

class GitHubAnalysisAgent:
    def __init__(self, github_token: str):
        self.github = Github(github_token)
        self.logger = logging.getLogger(__name__)
        self.setup_logging()
        
    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )

    def clone_repository(self, repo_url: str, branch: str, local_path: str) -> Repo:
        """Clone a specific branch of a repository."""
        try:
            if os.path.exists(local_path):
                return Repo(local_path)
            
            self.logger.info(f"Cloning repository: {repo_url}, branch: {branch}")
            repo = Repo.clone_from(repo_url, local_path, branch=branch)
            return repo
        except Exception as e:
            self.logger.error(f"Error cloning repository: {str(e)}")
            raise

    def analyze_file_structure(self, local_path: str) -> Dict:
        """Generate a dictionary representing the file structure."""
        structure = {}
        root_path = Path(local_path)
        
        def build_structure(path: Path, current_dict: Dict):
            for item in path.iterdir():
                if item.name.startswith('.') or item.name == '__pycache__':
                    continue
                    
                if item.is_file():
                    current_dict[item.name] = None
                else:
                    current_dict[item.name] = {}
                    build_structure(item, current_dict[item.name])
        
        build_structure(root_path, structure)
        return structure

    def analyze_file_content(self, file_path: str) -> FileContext:
        """Analyze individual file content."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        file_ext = Path(file_path).suffix
        language = self.detect_language(file_ext)
        imports = self.extract_imports(content, language)
        
        return FileContext(
            path=file_path,
            content=content,
            language=language,
            imports=imports,
            dependencies=self.analyze_dependencies(content, language),
            description=self.generate_file_description(content, language)
        )

    def detect_language(self, file_extension: str) -> str:
        """Detect programming language based on file extension."""
        language_map = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.java': 'java',
            '.cpp': 'cpp',
            '.go': 'go',
        }
        return language_map.get(file_extension.lower(), 'unknown')

    def extract_imports(self, content: str, language: str) -> List[str]:
        """Extract import statements from file content."""
        imports = []
        if language == 'python':
            import ast
            try:
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for name in node.names:
                            imports.append(name.name)
                    elif isinstance(node, ast.ImportFrom):
                        module = node.module or ''
                        for name in node.names:
                            imports.append(f"{module}.{name.name}")
            except:
                self.logger.warning(f"Could not parse Python imports")
        return imports

    def analyze_dependencies(self, content: str, language: str) -> List[str]:
        """Analyze code dependencies."""
        # Implement dependency analysis based on language
        # This is a simplified version
        return []

    def generate_file_description(self, content: str, language: str) -> str:
        """Generate a description of the file's purpose."""
        # In a real implementation, you would use an LLM here
        return f"Source code file in {language}"

    def analyze_repository(self, repo_url: str, branch: str) -> RepoContext:
        """Main method to analyze a repository."""
        # Create temporary directory for cloning
        temp_dir = f"temp_repo_{branch}"
        
        try:
            # Clone repository
            repo = self.clone_repository(repo_url, branch, temp_dir)
            
            # Analyze structure
            structure = self.analyze_file_structure(temp_dir)
            
            # Analyze files
            files = []
            for root, _, filenames in os.walk(temp_dir):
                for filename in filenames:
                    if filename.endswith(('.py', '.js', '.java', '.ts', '.go')):
                        file_path = os.path.join(root, filename)
                        file_context = self.analyze_file_content(file_path)
                        files.append(file_context)
            
            # Create repository context
            repo_context = RepoContext(
                repo_name=repo_url.split('/')[-1],
                branch=branch,
                files=files,
                structure=structure,
                main_languages=self.detect_main_languages(files),
                dependencies=self.aggregate_dependencies(files)
            )
            
            # Save context
            self.save_context(repo_context)
            
            return repo_context
            
        finally:
            # Cleanup
            if os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir)

    def detect_main_languages(self, files: List[FileContext]) -> List[str]:
        """Detect main languages used in the repository."""
        language_count = {}
        for file in files:
            language_count[file.language] = language_count.get(file.language, 0) + 1
        
        # Sort by frequency
        sorted_languages = sorted(language_count.items(), key=lambda x: x[1], reverse=True)
        return [lang for lang, _ in sorted_languages]

    def aggregate_dependencies(self, files: List[FileContext]) -> Dict:
        """Aggregate dependencies across all files."""
        dependencies = {}
        for file in files:
            for dep in file.dependencies:
                dependencies[dep] = dependencies.get(dep, 0) + 1
        return dependencies

    def save_context(self, context: RepoContext, filename: str = "repo_context.pkl"):
        """Save the repository context to a file."""
        with open(filename, 'wb') as f:
            pickle.dump(context, f)
        
        # Also save a JSON readable version
        json_context = {
            "repo_name": context.repo_name,
            "branch": context.branch,
            "structure": context.structure,
            "main_languages": context.main_languages,
            "files": [
                {
                    "path": f.path,
                    "language": f.language,
                    "imports": f.imports,
                    "dependencies": f.dependencies,
                    "description": f.description
                }
                for f in context.files
            ]
        }
        
        with open("repo_context.json", 'w') as f:
            json.dump(json_context, f, indent=2)