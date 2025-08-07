# Task Master AI - Agents Integration Guide

## 🚀 Essential Commands

### Core Workflow Commands

```bash
# Project Setup
task-master init                                    # Initialize Task Master in current project
task-master parse-prd .taskmaster/docs/prd.txt      # Generate tasks from PRD document
task-master models --setup                        # Configure AI models interactively

# Daily Development Workflow
task-master list                                   # Show all tasks with status
task-master next                                   # Get next available task to work on
task-master show <id>                             # View detailed task information (e.g., task-master show 1.2)
task-master set-status --id=<id> --status=done    # Mark task complete

# Task Management
task-master add-task --prompt="description" --research        # Add new task with AI assistance
task-master expand --id=<id> --research --force              # Break task into subtasks
task-master update-task --id=<id> --prompt="changes"         # Update specific task
task-master update --from=<id> --prompt="changes"            # Update multiple tasks from ID onwards
task-master update-subtask --id=<id> --prompt="notes"        # Add implementation notes to subtask

# Analysis & Planning
task-master analyze-complexity --research          # Analyze task complexity
task-master complexity-report                      # View complexity analysis
task-master expand --all --research               # Expand all eligible tasks

# Dependencies & Organization
task-master add-dependency --id=<id> --depends-on=<id>       # Add task dependency
task-master move --from=<id> --to=<id>                       # Reorganize task hierarchy
task-master validate-dependencies                            # Check for dependency issues
task-master generate                                         # Update task markdown files (usually auto-called)
```

## 📁 Key Files & Project Structure

### Core Files

- `.taskmaster/tasks/tasks.json` - Main task data file (auto-managed)
- `.taskmaster/config.json` - AI model configuration (use `task-master models` to modify)
- `.taskmaster/docs/prd.txt` - Product Requirements Document for parsing
- `.taskmaster/tasks/*.txt` - Individual task files (auto-generated from tasks.json)
- `.env` - API keys for CLI usage

### Agents Integration Files

- `AGENTS.md` - Auto-loaded context for AI Agents (this file)
- `.claude/settings.json` - Claude Code tool allowlist and preferences
- `.claude/commands/` - Custom slash commands for repeated workflows
- `.mcp.json` - MCP server configuration (project-specific)

### Directory Structure

```
weekly-deploy-reporter/
├── .taskmaster/
│   ├── tasks/              # Task files directory
│   │   ├── tasks.json      # Main task database
│   │   ├── task-1.md      # Individual task files
│   │   └── task-2.md
│   ├── docs/              # Documentation directory
│   │   ├── prd.txt        # Product requirements
│   ├── reports/           # Analysis reports directory
│   │   └── task-complexity-report.json
│   ├── templates/         # Template files
│   │   └── example_prd.txt  # Example PRD template
│   └── config.json        # AI models & settings
├── .claude/
│   ├── settings.json      # Claude Code configuration
│   └── commands/         # Custom slash commands
├── .env                  # API keys
├── .mcp.json            # MCP configuration
├── create_weekly_report.py  # Main script (optimized)
├── log_manager.py        # Log management utility
├── create_daily_log.py   # Daily log creation script
├── DAILY_LOG_SETUP.md    # Daily log system guide
├── create_weekly_report_process_diagram.md  # Process diagrams
├── code_cleanup_summary.md  # Code optimization report
├── unused_functions_analysis.md  # Unused functions analysis
└── AGENTS.md            # This file - auto-loaded by AI Agents
```

## 🔧 MCP Integration

Task Master provides an MCP server that AI Agents can connect to. Configure in `.mcp.json`:

```json
{
  "mcpServers": {
    "task-master-ai": {
      "command": "npx",
      "args": ["-y", "--package=task-master-ai", "task-master-ai"],
      "env": {
        "ANTHROPIC_API_KEY": "your_key_here",
        "PERPLEXITY_API_KEY": "your_key_here",
        "OPENAI_API_KEY": "OPENAI_API_KEY_HERE",
        "GOOGLE_API_KEY": "GOOGLE_API_KEY_HERE",
        "XAI_API_KEY": "XAI_API_KEY_HERE",
        "OPENROUTER_API_KEY": "OPENROUTER_API_KEY_HERE",
        "MISTRAL_API_KEY": "MISTRAL_API_KEY_HERE",
        "AZURE_OPENAI_API_KEY": "AZURE_OPENAI_API_KEY_HERE",
        "OLLAMA_API_KEY": "OLLAMA_API_KEY_HERE"
      }
    }
  }
}
```

## 🎯 Weekly Deploy Reporter Integration

### Project Overview

This project integrates TaskMaster AI with the Weekly Deploy Reporter system, providing AI-powered task management for automated deployment reporting.

### Key Integration Points

#### 1. Automated Task Generation
```bash
# Generate tasks from PRD document
task-master parse-prd .taskmaster/docs/weekly-reporter-prd.txt

# View generated tasks
task-master list
```

#### 2. Development Workflow
```bash
# Get next task to work on
task-master next

# Mark task as complete
task-master set-status --id=1.2 --status=done

# Expand complex tasks
task-master expand --id=2.1 --research
```

#### 3. Task Analysis
```bash
# Analyze task complexity
task-master analyze-complexity --research

# View complexity report
task-master complexity-report
```

### Current Task Status

Based on the project analysis, the following tasks are currently managed:

#### Completed Tasks ✅
- **Task 1**: 프로젝트 저장소 및 환경 초기화
- **Task 2**: API 인증 및 연동 구현
- **Task 3**: Jira 이슈 조회 및 필터링 모듈
- **Task 4**: Confluence 페이지 생성/업데이트 모듈
- **Task 5**: Slack 알림 시스템 구현
- **Task 6**: 스냅샷 관리 및 변경 감지
- **Task 7**: 코드 최적화 및 정리

#### Active Tasks 🔄
- **Task 8**: 로그 시스템 고도화
- **Task 9**: TaskMaster AI 통합 완료
- **Task 10**: 문서화 및 가이드 업데이트

#### Planned Tasks 📋
- **Task 11**: 성능 모니터링 대시보드
- **Task 12**: 자동화 스크립트 개선
- **Task 13**: 테스트 커버리지 확대

## 🔍 Task Management Workflow

### 1. Daily Development Process

```bash
# Start your day
task-master next                    # Get next task to work on
task-master show <id>              # Review task details

# Work on task
# ... development work ...

# Complete task
task-master set-status --id=<id> --status=done

# Move to next task
task-master next
```

### 2. Task Expansion Process

```bash
# For complex tasks, expand into subtasks
task-master expand --id=<id> --research --force

# Review expanded subtasks
task-master show <id>

# Work on subtasks
task-master update-subtask --id=<id> --prompt="implementation notes"
```

### 3. Dependency Management

```bash
# Add dependencies between tasks
task-master add-dependency --id=3.1 --depends-on=2.3

# Validate dependencies
task-master validate-dependencies

# Reorganize task hierarchy
task-master move --from=3.2 --to=2.4
```

## 📊 Project Metrics

### Code Optimization Results
- **44% code reduction**: ~1,600 lines → ~900 lines
- **39% function reduction**: 38 functions → 23 functions
- **100% unused function removal**: 15 functions completely removed
- **100% duplicate function removal**: 1 duplicate function removed

### Task Completion Status
- **Completed**: 7 tasks (70%)
- **In Progress**: 3 tasks (30%)
- **Planned**: 3 tasks (pending)

### Performance Improvements
- **Execution time**: 1-2 minutes (without pagination)
- **Memory usage**: 50-200MB (depending on pagination)
- **API calls**: 1-5 Jira calls, 1-2 Confluence calls (default)

## 🛠️ Development Guidelines

### Code Quality Standards
- **Readability first**: Prioritize code readability over performance
- **Single responsibility**: Each function should have a single purpose
- **Descriptive naming**: Use clear, meaningful variable and function names
- **Documentation**: Add comprehensive comments for complex logic
- **Error handling**: Implement proper exception handling

### Testing Strategy
```bash
# Run all tests
python -m pytest tests/

# Run specific test
python -m pytest tests/test_create_weekly_report.py -v

# Debug specific functionality
python create_weekly_report.py --debug-links IT-5332
```

### Logging Best Practices
```bash
# Debug level for development
LOG_LEVEL=DEBUG python create_weekly_report.py current

# Info level for production
LOG_LEVEL=INFO python create_weekly_report.py current

# Verbose logging for detailed debugging
VERBOSE_LOGGING=true python create_weekly_report.py current
```

## 🔧 Configuration Management

### Environment Variables
```bash
# Required variables
ATLASSIAN_URL=https://your-domain.atlassian.net
ATLASSIAN_USERNAME=your-email@domain.com
ATLASSIAN_API_TOKEN=your-api-token
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Optional variables
LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
VERBOSE_LOGGING=false            # true/false
DEPLOY_MESSAGE=off               # on/off
JIRA_PROJECT_KEY=IT
CONFLUENCE_SPACE_KEY=DEV
```

### TaskMaster Configuration
```json
{
  "models": {
    "main": {
      "provider": "anthropic",
      "modelId": "claude-3-7-sonnet-20250219",
      "maxTokens": 120000,
      "temperature": 0.2
    },
    "research": {
      "provider": "perplexity",
      "modelId": "sonar-pro",
      "maxTokens": 8700,
      "temperature": 0.1
    }
  },
  "global": {
    "logLevel": "info",
    "debug": false,
    "defaultNumTasks": 10,
    "defaultSubtasks": 5,
    "defaultPriority": "medium",
    "projectName": "weekly-reporter",
    "defaultLanguage": "ko"
  }
}
```

## 📈 Monitoring & Analytics

### Log Management
```bash
# View log summary
python3 log_manager.py summary

# Monitor real-time logs
python3 log_manager.py tail

# Check today's logs
python3 log_manager.py today

# Clean up old logs
python3 log_manager.py cleanup --keep-days 30
```

### Performance Monitoring
- **Execution time tracking**: Automatic timing in logs
- **Error rate monitoring**: Failed execution detection
- **API call tracking**: Request/response logging
- **Resource usage**: Memory and CPU monitoring

## 🚀 Deployment & Automation

### Crontab Configuration
```bash
# Weekly report generation (Fridays at 9:30 AM)
30 9 * * 5 /path/to/venv/bin/python /path/to/create_weekly_report.py create

# Daily updates (Mon-Fri, 8 AM-9 PM, every 15 minutes)
15,30,45,0 8-21 * * 1-5 /path/to/venv/bin/python /path/to/create_weekly_report.py update

# Log management (Sundays at 2 AM)
0 2 * * 0 /path/to/venv/bin/python /path/to/log_manager.py cleanup --keep-days 30
```

### Automated Testing
```bash
# Run all tests
python -m pytest tests/ -v

# Test specific functionality
python test_pagination_options.py
python test_emoji_notification.py
python test_it_5332_links.py
```

## 🔍 Troubleshooting Guide

### Common Issues

#### 1. TaskMaster Connection Issues
```bash
# Check TaskMaster configuration
cat .taskmaster/config.json

# Test TaskMaster connection
task-master list

# Reinitialize if needed
task-master init
```

#### 2. Log System Problems
```bash
# Check log directory permissions
ls -la logs/runtime/

# Test log creation
python3 create_daily_log.py

# Verify log manager
python3 log_manager.py summary
```

#### 3. API Connection Issues
```bash
# Test environment variables
python -c "import os; from dotenv import load_dotenv; load_dotenv(); print('ATLASSIAN_URL:', os.getenv('ATLASSIAN_URL'))"

# Test Jira connection
python check_jira_fields.py

# Debug specific ticket
python create_weekly_report.py --debug-links IT-5332
```

### Debug Commands
```bash
# Enable debug logging
LOG_LEVEL=DEBUG python create_weekly_report.py current

# Verbose output
VERBOSE_LOGGING=true python create_weekly_report.py current

# Force update (ignore change detection)
python create_weekly_report.py --force-update

# Check page content
python create_weekly_report.py --check-page
```

## 📚 Related Documentation

- [README.md](README.md) - Project overview and setup guide
- [DAILY_LOG_SETUP.md](DAILY_LOG_SETUP.md) - Log system configuration
- [create_weekly_report_process_diagram.md](create_weekly_report_process_diagram.md) - Process flow diagrams
- [code_cleanup_summary.md](code_cleanup_summary.md) - Code optimization report
- [CLAUDE.md](CLAUDE.md) - Claude Code integration guide

## 🎯 Best Practices

### Development Workflow
1. **Start with TaskMaster**: Always check `task-master next` before starting work
2. **Document changes**: Update task notes with implementation details
3. **Test thoroughly**: Run tests after each significant change
4. **Monitor logs**: Check log files for any issues
5. **Update documentation**: Keep README and guides current

### Code Quality
1. **Follow PEP 8**: Maintain consistent Python code style
2. **Add comments**: Document complex logic and business rules
3. **Handle exceptions**: Implement proper error handling
4. **Use type hints**: Add type annotations where helpful
5. **Keep functions small**: Single responsibility principle

### Performance Optimization
1. **Use pagination selectively**: Only when needed for large datasets
2. **Implement caching**: Cache frequently accessed data
3. **Optimize API calls**: Minimize redundant requests
4. **Monitor resource usage**: Track memory and CPU usage
5. **Profile code**: Identify bottlenecks and optimize

## 🤖 AI Agent Integration

### Agent-Specific Commands

#### For Claude Code
```bash
# Get next task with context
task-master next

# Show task details
task-master show <id>

# Update task with implementation notes
task-master update-subtask --id=<id> --prompt="implementation details"

# Mark task complete
task-master set-status --id=<id> --status=done
```

#### For Other AI Agents
```bash
# List all tasks
task-master list

# Analyze project complexity
task-master analyze-complexity --research

# Expand complex tasks
task-master expand --id=<id> --research --force

# Generate complexity report
task-master complexity-report
```

### Agent Workflow Integration

#### 1. Task Discovery
```bash
# Find available tasks
task-master list

# Get next task to work on
task-master next

# View task details
task-master show <id>
```

#### 2. Task Execution
```bash
# Start working on task
task-master set-status --id=<id> --status=in-progress

# Update progress
task-master update-subtask --id=<id> --prompt="progress update"

# Complete task
task-master set-status --id=<id> --status=done
```

#### 3. Task Analysis
```bash
# Analyze task complexity
task-master analyze-complexity --research

# Expand into subtasks
task-master expand --id=<id> --research --force

# View complexity report
task-master complexity-report
```

## 📊 Agent Performance Metrics

### Task Completion Tracking
- **Tasks completed**: 7/10 (70%)
- **Tasks in progress**: 3/10 (30%)
- **Tasks planned**: 3 (pending)

### Code Quality Metrics
- **Functions optimized**: 23/38 (60% reduction)
- **Code lines reduced**: 900/1600 (44% reduction)
- **Unused functions removed**: 15/15 (100%)

### Performance Metrics
- **Execution time**: 1-2 minutes (optimized)
- **Memory usage**: 50-200MB (efficient)
- **API calls**: 1-5 Jira, 1-2 Confluence (minimized)

## 🔧 Agent Configuration

### Environment Setup
```bash
# Required environment variables
export ANTHROPIC_API_KEY="your_claude_key"
export PERPLEXITY_API_KEY="your_perplexity_key"
export ATLASSIAN_URL="https://your-domain.atlassian.net"
export ATLASSIAN_USERNAME="your-email@domain.com"
export ATLASSIAN_API_TOKEN="your-api-token"
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
```

### Model Configuration
```json
{
  "models": {
    "main": {
      "provider": "anthropic",
      "modelId": "claude-3-7-sonnet-20250219",
      "maxTokens": 120000,
      "temperature": 0.2
    },
    "research": {
      "provider": "perplexity",
      "modelId": "sonar-pro",
      "maxTokens": 8700,
      "temperature": 0.1
    }
  }
}
```

## 🎯 Agent Best Practices

### Task Management
1. **Always check next task**: Use `task-master next` before starting work
2. **Update progress regularly**: Use `task-master update-subtask` to log progress
3. **Mark tasks complete**: Use `task-master set-status --status=done` when finished
4. **Expand complex tasks**: Use `task-master expand` for large tasks
5. **Analyze complexity**: Use `task-master analyze-complexity` for planning

### Code Quality
1. **Follow project standards**: Maintain consistent code style
2. **Add comprehensive comments**: Document complex logic
3. **Handle exceptions properly**: Implement robust error handling
4. **Test thoroughly**: Run tests after changes
5. **Monitor performance**: Check logs and metrics

### Communication
1. **Update task notes**: Keep task documentation current
2. **Log implementation details**: Record what worked and what didn't
3. **Report issues**: Document problems and solutions
4. **Share progress**: Update task status regularly
5. **Collaborate effectively**: Use task dependencies for coordination

---

**Last Updated**: January 2025
**Version**: TaskMaster AI integration, code optimization, advanced logging system, agent-specific workflows
