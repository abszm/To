# 用户指令记忆

本文件记录了用户的指令、偏好和教导，用于在未来的交互中提供参考。

## 格式

### 用户指令条目
用户指令条目应遵循以下格式：

[用户指令摘要]
- Date: [YYYY-MM-DD]
- Context: [提及的场景或时间]
- Instructions:
  - [用户教导或指示的内容，逐行描述]

### 项目知识条目
Agent 在任务执行过程中发现的条目应遵循以下格式：

[项目知识摘要]
- Date: [YYYY-MM-DD]
- Context: Agent 在执行 [具体任务描述] 时发现
- Category: [代码结构|代码模式|代码生成|构建方法|测试方法|依赖关系|环境配置]
- Instructions:
  - [具体的知识点，逐行描述]

## 去重策略
- 添加新条目前，检查是否存在相似或相同的指令
- 若发现重复，跳过新条目或与已有条目合并
- 合并时，更新上下文或日期信息
- 这有助于避免冗余条目，保持记忆文件整洁

## 条目

[按上述格式记录的记忆条目]

[音频转码项目结构与测试方式]
- Date: 2026-04-27
- Context: Agent 在执行“根据技术方案进行开发”任务时发现
- Category: 代码结构
- Instructions:
  - 当前功能规格位于 `.monkeycode/specs/2026-04-27-audio-transcoder/`，实现代码采用 `src/` 与 `tests/` 分层

[音频转码项目测试命令]
- Date: 2026-04-27
- Context: Agent 在执行“根据技术方案进行开发”任务时发现
- Category: 测试方法
- Instructions:
  - 项目使用 `pytest` 作为测试框架，根目录执行 `pytest` 运行全部单元测试

[音频转码集成测试入口]
- Date: 2026-04-27
- Context: Agent 在执行“补一组真实音频样本集成测试脚本”任务时发现
- Category: 测试方法
- Instructions:
  - 集成测试命令为 `./scripts/run_integration_tests.sh`，用 `pytest -m integration` 运行
  - 可通过环境变量 `REAL_AUDIO_SAMPLE` 指向真实音频文件以启用真实样本测试

[音频转码项目 Web 运行方式]
- Date: 2026-04-27
- Context: Agent 在执行“增加上传入口与下载按钮”任务时发现
- Category: 构建方法
- Instructions:
  - 默认运行模式为 `APP_MODE=web`，入口命令为 `python3 -m src.web`
  - 容器中可通过 `PORT` 指定 Web 端口，默认 `8080`
