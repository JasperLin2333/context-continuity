# Context Continuity · 上下文协作治理

**换一个 Agent，仍能接着当前决定与源文件继续工作。**

一个可安装、可迭代的通用 Skill，用于建立和修复跨 Agent、跨会话、跨工具的项目协作规范。适合代码仓库、产品文档和其他持续维护的工作区。

它帮助 Agent 找到当前信源、核对旧摘要、明确修改责任，把新决定与成果写回维护源。项目已有规范会被沿用，缺少的部分才补上。

**[使用 Skill](SKILL.md) · [下载发布包](https://github.com/JasperLin2333/context-continuity/releases/latest) · [迭代规范](CONTRIBUTING.md) · [反馈问题](https://github.com/JasperLin2333/context-continuity/issues)**

## 可以这样用

| 你的情况 | 发给 Agent 的请求 |
| --- | --- |
| 新项目准备使用多个 AI 工具 | 使用上下文协作治理，为这个项目建立最小协作规范，沿用已有目录和文件 |
| 换会话就忘记之前的决定 | 使用上下文协作治理，找出接续时缺了哪些必要读取与交接信息 |
| 明明写了规则，还是反复做错 | 使用上下文协作治理，用这次失败检查是理解、读取、信源还是执行出了问题 |
| 当前机制已用了一段时间 | 使用上下文协作治理，根据这次反馈修订已有机制，清除重复与冲突条款 |

例如：旧交接写着“继续方案 A”，而用户已决定转向 B，当前正文也已更新。接手的 Agent 应读取并核对 B 的源文件，保留仍有效的约束，再继续任务。它不应依据旧摘要恢复 A，也不应为这个问题再创建一份长期状态文件。

## 安装与开始

把这段话发给支持 Skill 安装的 AI 助手：

```text
请安装 https://github.com/JasperLin2333/context-continuity 中的 Skill。
按当前宿主支持的方式安装完整 Skill 及 references，不修改我的项目规则或全局配置。
然后使用上下文协作治理，先检查当前项目的信源、任务接续和成果回写机制。
```

也可使用 [Vercel skills CLI](https://github.com/vercel-labs/skills)，按提示选择宿主：

```sh
npx skills add JasperLin2333/context-continuity --skill context-continuity
```

Skill 执行本身不需要脚本、API Key 或额外运行依赖。它使用当前 AI 助手已有的文件或平台访问能力；修改仍遵守用户和宿主授权。

安装后对 Agent 说：

> 使用 context-continuity，检查这个项目为什么换会话后总会用到旧决定。在已授权的项目范围内优化，保留用户改动，说明实际验证结果。

普通业务修改不需要每次运行治理。Skill 建立或修复机制，日常任务通过项目规则与实际源文件继续工作。只要求分析时保持只读。

## 跨平台分发

维护同一份 Skill 正文，打包时生成不同的元数据与插件外壳。

| 发布包 | 用途 |
| --- | --- |
| `context-continuity.zip` | Agent Skills 标准目录包；供 Codex、Claude Code、Cursor、Copilot 等按各自规则安装 |
| `context-continuity-workbuddy.zip` | WorkBuddy 开放平台的字段适配包 |
| `context-continuity-skillhub.zip` | 腾讯 SkillHub 的字段适配包 |
| `context-continuity-claude.zip` | 含 Skill 和本地 marketplace 的 Claude 插件包 |
| `context-continuity-openai.zip` | 使用 Agent Plugins 根 manifest 的 OpenAI 插件包 |

安装目录、官方规范与能力边界见[平台接入](references/platforms.md)。GitHub Release 提供以上 ZIP 和 SHA256 清单；市场包准备完成与各市场审核上架分别确认。

本 Skill 不自动同步聊天或项目文件。多端需要访问同一维护源或按项目约定同步版本；无法访问的会话、目录或远端不会凭安装 Skill 自动出现。当前发布已验证包结构与引用，跨客户端实际调用仍需在对应宿主验证。

Claude 插件包解压后，可以在 Claude Code 中按官方本地市场流程安装：

```text
/plugin marketplace add /解压目录/context-continuity
/plugin install context-continuity@context-continuity-marketplace
```

OpenAI 插件包解压后，按[官方插件文档](https://developers.openai.com/plugins/build/plugins)从本地目录测试或准备提交。这里只分发包，不自动注册市场、改宿主配置或申请官方目录上架。

## 持续维护

仓库是 Skill 的维护源；项目业务事实继续保存在各自项目。版本号只维护在 `distribution.json`，平台字段和版本在打包时注入，避免多份正文分别演进。

维护者使用 Python 3.10+，无需第三方库：

```sh
python3 -m unittest discover -s tests -v
python3 scripts/distribute.py check
python3 scripts/distribute.py pack --target all
```

只构建一个通道：

```sh
python3 scripts/distribute.py pack --target workbuddy
```

输出位于 `dist/<通道>/`。包采用明确文件清单，排除维护脚本、测试、真实项目和 Git 数据；同一环境对相同输入重复构建得到相同 ZIP。`dist/SHA256SUMS` 记录本次构建的包。下载 Release 后，把 ZIP 与清单放在同一目录，可用 `sha256sum -c SHA256SUMS` 核对。

手动安装到指定的新目录，已有安装会停止并保留：

```sh
python3 scripts/distribute.py install --destination "/你的宿主/skills/context-continuity"
```

开发者可加 `--link` 指向维护仓库，避免本机维护两份正文；需先核对宿主是否支持目录符号链接。安装成功只证明文件已放置，实际发现、读取和执行分别核对。

后续修改先分清是项目特例、宿主差异还是通用机制，再更新对应层。验证格式之外，还要检查[行为场景](tests/behavior-cases.md)。仓库提供[GitHub Actions 模板](templates/github-actions.yml)，具有工作流写入权限后可启用标签发布；当前也可按[迭代规范](CONTRIBUTING.md)手动验证和发布。发布说明写清具体变化与实际取得的行为证据。

方法来自实际项目协作的抽象，并参考了 [Orbital](https://github.com/zqiren/Orbital) 的上下文接续与回写思路。本仓库独立编写，采用 [MIT](LICENSE) 许可证。
