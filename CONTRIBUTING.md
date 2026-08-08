# Contributing to Thon Code

**First off, thank you for considering contributing to Thon Code! We appreciate your time and effort, and we’re excited to work with you. Please take a moment to review this guide – it will help you get started smoothly.**

**By participating in this project, you agree to abide by our [Code of Conduct](LINK_TO_CODE_OF_CONDUCT).**

---

## 1. Ways to Contribute

**We welcome contributions of all kinds, not just code! Here are some ways you can help:**

- Reporting bugs or issues
- Suggesting new features or enhancements
- Improving or translating documentation
- Submitting pull requests with bug fixes or new features
- Participating in discussions and helping other users
- Providing design or UI/UX improvements

Every contribution, no matter how small, is valuable to us.

---

## 2. Development Environment Setup

**To get started with development, follow these steps:**

1. **Fork** the repository on GitHub.
2. **Clone** your fork locally:
   ```bash
   git clone https://github.com/L-YLing/Thon-Code.git
   cd Thon-Code
   ```
3. **Set up the upstream remote to keep your fork synced:**
   ```bash
   git remote add upstream https://github.com/L-YLing/Thon-Code.git
   ```
4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
5. **Run the project locally to verify everything works:**
   ```bash
   python <the path of main.py>
   ```
   
## 3. Finding an Issue to Work On

**We use GitHub Issues to track tasks. Look for labels that indicate good starting points:**

* **good first issue – tasks specifically chosen for newcomers.**

* **help wanted – issues that we’d particularly like help with.**

**Feel free to comment on an issue to let us know you’re working on it, and we’ll assign it to you.**

## 4. Contribution Workflow

**Follow this workflow to ensure a smooth review and merge process.**

### Branch Naming

* **Create a new branch for your work, never commit directly to `main` or `master`.**

**Use descriptive names:**

* **feature/short-description for new features**

* **fix/short-description for bug fixes**

* **docs/short-description for documentation changes**

* **chore/short-description for maintenance tasks**

**Example:**
```bash
git checkout -b feature/add-login-endpoint
```

### Commit Messages

**We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification. Please format your commit messages as:**

```
<type>(<scope>): <subject>
<BLANK LINE>
<body>
<BLANK LINE>
<footer>
```

**Common types:**

* **`feat` – new feature**

* **`fix` – bug fix**

* **`docs` – documentation only**

* **`style` – code style (formatting, etc.)**

* **`refactor` – code change that neither fixes a bug nor adds a feature**

* **`*test` – adding or updating tests**

* **`chore` – maintenance tasks**

**Example:**

```
feat(auth): add JWT token validation

Adds middleware to validate JWT tokens for protected endpoints.
Closes #123
```

### Pull Request (PR) Process

1. **Sync your branch with the latest upstream `main` to avoid conflicts:**
   ```bash
   git fetch upstream
   git rebase upstream/main
   ```
2. **Push your branch to your fork:**
   ```bash
   git push origin feature/add-login-endpoint
   ```
3. **Open a Pull Request on GitHub against the `main` branch of the original repository.**
4. **In the PR description, clearly explain:**
   * **What the PR does**
   * **Why it’s needed**
   * **Any related issue numbers (e.g., Closes #456)**
5. **Ensure all automated checks (tests, linting, etc.) pass.**
6. **Request a review from @L-YLing/DevApotheosis / @L-YLing if applicable.**

### Code Review

* **One or more maintainers will review your PR.**

* **Please be responsive to feedback – we may ask for changes or clarifications.**

* **We aim to merge PRs once they meet our quality standards and pass all checks.**

* **If your PR becomes stale (no activity for [X] days), we may close it, but feel free to reopen when you’re ready.**

## 5. Code Standards & Quality

**To keep the codebase maintainable and consistent, please adhere to the following:**

* **Code style: None for now.**

* **Linting: None for now**

* **Testing: None for now**

* **Documentation: Update relevant docstrings, README, or user guides when changing functionality.**

**If you’re unsure, feel free to ask in the issue or PR.**

## 6. Community & Communication
**We value open and respectful communication. Here’s where you can reach out:**

* **GitHub Discussions: [LINK_TO_DISCUSSIONS] – for questions, ideas, and general chat.**

* **Chat / Slack / Discord: [LINK_TO_CHAT] – for real‑time conversations.**

* **Regular Meetings: [MEETING_SCHEDULE_AND_LINK] – open to all contributors.**

**Please be patient when waiting for replies – we are a distributed team with different time zones.**

## 7. Legal & Licensing
**By contributing to Thon Code, you agree that your contributions will be licensed under the project’s open‑source license (see LICENSE file). If your contribution includes third‑party code, ensure it is compatible with our license.**

**Thank you again for your interest in Thon Code! We look forward to your contributions.**
