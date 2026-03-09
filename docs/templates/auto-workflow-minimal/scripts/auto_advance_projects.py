#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from pathlib import Path
from datetime import datetime
import json
import re

WORKSPACE = Path('/Users/you/.openclaw/workspace')
BASE = WORKSPACE / 'projects'
PROJECT = BASE / 'example-project'
DOCS = PROJECT / 'docs'
RUNTIME = WORKSPACE / 'runtime' / 'auto-advance'
AUTO = BASE / 'AUTO_ADVANCE.md'
DASH = BASE / 'DASHBOARD.md'
STATE = RUNTIME / 'example-project-state.json'
TRACE = RUNTIME / 'example-project-trace.log'
LAST = RUNTIME / 'example-project-last-run.txt'
TODO = PROJECT / 'TODO.md'
PROJECT_MD = PROJECT / 'PROJECT.md'
PROGRESS = DOCS / 'progress-log.md'

NOW = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
TODAY = datetime.now().strftime('%Y-%m-%d')

STEPS = [
    {
        'id': 'step-01',
        'name': '输出第一版 example-output.md',
        'checkpoint': 'docs/example-output.md 已生成',
        'action': 'write_output',
    },
    {
        'id': 'step-02',
        'name': '更新 TODO / PROJECT 状态',
        'checkpoint': 'TODO / PROJECT 已同步',
        'action': 'update_project_files',
    },
    {
        'id': 'step-03',
        'name': '写入结论摘要',
        'checkpoint': 'docs/summary.md 已生成',
        'action': 'write_summary',
    },
]


def trace(msg):
    with TRACE.open('a', encoding='utf-8') as f:
        f.write(f'[{NOW}] {msg}\n')


def progress(msg):
    with PROGRESS.open('a', encoding='utf-8') as f:
        f.write(f'- {NOW}：{msg}\n')


def load_state():
    return json.loads(STATE.read_text(encoding='utf-8'))


def save_state(state):
    STATE.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')


def write_output():
    p = DOCS / 'example-output.md'
    p.write_text('# Example Output\n\n这是自动推进系统生成的第一版样例产物。\n', encoding='utf-8')
    progress('已生成 example-output.md')
    trace('write_output: wrote docs/example-output.md')


def update_project_files():
    todo = TODO.read_text(encoding='utf-8')
    todo = todo.replace('- [ ] 输出 example-output.md', '- [x] 输出 example-output.md')
    todo = todo.replace('- [ ] 更新项目状态', '- [x] 更新项目状态')
    TODO.write_text(todo, encoding='utf-8')

    text = PROJECT_MD.read_text(encoding='utf-8')
    text = re.sub(r'## Next Action\n- .*\n', '## Next Action\n- 输出结论摘要\n', text)
    text = re.sub(r'## Auto-Advance Checkpoint\n- 当前 checkpoint：.*\n- 完成后进入：.*\n', '## Auto-Advance Checkpoint\n- 当前 checkpoint：docs/summary.md 已生成\n- 完成后进入：等待下一批 step\n', text)
    PROJECT_MD.write_text(text, encoding='utf-8')
    progress('已更新 TODO / PROJECT 状态')
    trace('update_project_files: synced TODO.md and PROJECT.md')


def write_summary():
    p = DOCS / 'summary.md'
    p.write_text('# Summary\n\n最小自动推进模板已完成一批 3 步任务。\n', encoding='utf-8')
    progress('已生成 summary.md')
    trace('write_summary: wrote docs/summary.md')


def update_auto(next_step_index):
    if next_step_index < len(STEPS):
        step = STEPS[next_step_index]
        next_action = step['name']
        checkpoint = step['checkpoint']
    else:
        next_action = '等待定义下一批自动推进动作'
        checkpoint = '当前预设小步任务已完成'

    AUTO.write_text(f'''# Auto Advance Queue\n\n## Ready\n- project: example-project\n  level: L4\n  next_action: {next_action}\n  checkpoint: {checkpoint}\n  notify: on_blocked,on_decision,on_complete\n  last_update: {TODAY}\n\n## Running\n- 暂无\n\n## Waiting\n- 暂无\n\n## Blocked\n- 暂无\n''', encoding='utf-8')

    dash = DASH.read_text(encoding='utf-8')
    dash = re.sub(r'## Auto-Advance Queue\n(?:- .*\n)+', f'## Auto-Advance Queue\n- **example-project** — ready · next: {next_action}\n', dash)
    DASH.write_text(dash, encoding='utf-8')
    trace(f'update_auto: next_action={next_action}')


def main():
    state = load_state()
    idx = state.get('next_step_index', 0)
    trace(f'start run: next_step_index={idx}')

    if idx >= len(STEPS):
        progress('自动推进检查：当前配置步骤已全部完成，无新动作执行')
        trace('no-op: all configured steps completed')
        LAST.write_text(f'{NOW} no-op\n', encoding='utf-8')
        return

    step = STEPS[idx]
    trace(f'executing {step["id"]}: {step["name"]}')

    if step['action'] == 'write_output':
        write_output()
    elif step['action'] == 'update_project_files':
        update_project_files()
    elif step['action'] == 'write_summary':
        write_summary()
    else:
        raise RuntimeError(f'unknown action: {step["action"]}')

    state['next_step_index'] = idx + 1
    state['last_run'] = NOW
    save_state(state)
    update_auto(state['next_step_index'])
    LAST.write_text(f'{NOW} completed {step["id"]}\n', encoding='utf-8')
    trace(f'completed {step["id"]}')


if __name__ == '__main__':
    main()
