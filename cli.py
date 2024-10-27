# cli.py
import click
import os
from main import GitHubAnalysisAgent

@click.command()
@click.option('--repo-url', required=True, help='GitHub repository URL')
@click.option('--branch', default='main', help='Branch to analyze')
@click.option('--output', default='repo_context.json', help='Output file for context')
def analyze_repo(repo_url: str, branch: str, output: str):
    """Analyze a GitHub repository and generate context."""
    # Get GitHub token from environment variable
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        raise click.ClickException("Please set the GITHUB_TOKEN environment variable")
    
    try:
        agent = GitHubAnalysisAgent(github_token)
        context = agent.analyze_repository(repo_url, branch)
        click.echo(f"Analysis completed. Context saved to {output}")
        
    except Exception as e:
        click.echo(f"Error: {str(e)}", err=True)

if __name__ == '__main__':
    analyze_repo()