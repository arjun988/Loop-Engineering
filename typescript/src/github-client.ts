/**
 * GitHub API integration for PR creation
 */

import { execSync } from 'child_process';
import { retryAsync } from './retry.js';

export interface PullRequestResult {
  success: boolean;
  prNumber?: number;
  prUrl?: string;
  branch?: string;
  error?: string;
}

export class GitHubClient {
  private token?: string;
  private repo?: string;
  private defaultBranch: string;

  constructor(token?: string, repo?: string, defaultBranch = 'main') {
    this.token = token ?? process.env.GITHUB_TOKEN;
    this.repo = repo ?? process.env.GITHUB_REPO ?? this.detectRepo();
    this.defaultBranch = defaultBranch ?? process.env.GITHUB_DEFAULT_BRANCH ?? 'main';
  }

  private detectRepo(): string | undefined {
    try {
      const url = execSync('git remote get-url origin', { encoding: 'utf-8' }).trim();
      if (url.includes('github.com')) {
        const parts = url.replace('.git', '').split('/');
        if (parts.length >= 2) return `${parts[parts.length - 2]}/${parts[parts.length - 1]}`;
      }
    } catch {
      // ignore
    }
    return undefined;
  }

  private headers(): Record<string, string> {
    if (!this.token) throw new Error('GITHUB_TOKEN environment variable is required');
    return {
      Authorization: `Bearer ${this.token}`,
      Accept: 'application/vnd.github+json',
      'X-GitHub-Api-Version': '2022-11-28',
    };
  }

  async createPullRequest(options: {
    title: string;
    body: string;
    branch: string;
    base?: string;
  }): Promise<PullRequestResult> {
    if (!this.repo) {
      return { success: false, error: 'Could not detect GitHub repo. Set GITHUB_REPO=owner/repo' };
    }

    const baseBranch = options.base ?? this.defaultBranch;

    try {
      return await retryAsync(async () => {
        const response = await fetch(`https://api.github.com/repos/${this.repo}/pulls`, {
          method: 'POST',
          headers: { ...this.headers(), 'Content-Type': 'application/json' },
          body: JSON.stringify({
            title: options.title,
            body: options.body,
            head: options.branch,
            base: baseBranch,
          }),
        });
        if (response.status === 422) {
          const data = (await response.json()) as { message?: string; errors?: Array<{ message: string }> };
          const msg = data.errors?.[0]?.message ?? data.message ?? 'Validation failed';
          return { success: false, error: msg };
        }
        if (!response.ok) throw new Error(`GitHub API error: ${response.status}`);
        const data = (await response.json()) as { number: number; html_url: string };
        return {
          success: true,
          prNumber: data.number,
          prUrl: data.html_url,
          branch: options.branch,
        };
      });
    } catch (error) {
      return { success: false, error: String(error) };
    }
  }

  async pushBranch(branch: string, cwd?: string): Promise<[boolean, string]> {
    try {
      execSync(`git push -u origin ${branch}`, { cwd, stdio: 'pipe', timeout: 120000 });
      return [true, 'Branch pushed successfully'];
    } catch (error) {
      return [false, String(error)];
    }
  }
}
