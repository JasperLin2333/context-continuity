# 迭代规范

每次修改都应解决一个明确问题，并保护已有有效行为。不以规则数量或文件数量作为成熟度指标。

## 选择修改位置

| 变化 | 维护位置 |
| --- | --- |
| 通用判断、触发边界和共同流程 | `SKILL.md` |
| 接入、交接或诊断的条件性细节 | `references/` 对应正文 |
| 平台字段、插件格式、文件清单 | `scripts/distribute.py`、`distribution.json` 与包测试 |
| 发布版本与身份信息 | `distribution.json` |
| 具体项目的规则和业务决定 | 项目本身；不要放进公开 Skill |
| 真实失败及预期行为 | 去敏后提炼到 `tests/behavior-cases.md`，避免堆积完整聊天或项目快照 |

先确认问题是理解、读取、信源、执行还是能力缺口。已有规则正确却未被执行时，修执行路径；不要再增加一条同义规则。优先修订原内容和清除冲突。

## 验证修改

```sh
python3 -m unittest discover -s tests -v
python3 scripts/distribute.py check
python3 scripts/distribute.py pack --target all
```

检查与本次变化相关的行为场景，至少覆盖原问题和可能受影响的正常任务。场景推演、模型实际执行、包结构验证与平台接收是不同证据，说明取得了哪一种。不要把场景文档的存在或格式测试通过写成行为回归通过。

有实际执行条件时，用去敏的最小项目验证修改；不要为测试使用生产材料、真实凭据或未经授权的外部写入。独立评估按当前工具与授权条件选择，不默认启动子 Agent。

## 版本与发布

采用 SemVer：修复不改变使用方式时递增补丁号；新增兼容能力时递增次版本；破坏已有用法时递增主版本。早期 `0.x` 版本仍在发布说明中明确变化与迁移影响。

1. 更新 `distribution.json` 中唯一维护的版本号，完成相应正文和测试修改。
2. 运行上述检查，审阅 Git diff，确认包只含公开清单中的材料。
3. 按用户授权提交并推送代码，再创建匹配的版本标签。用 `python3 scripts/distribute.py check --tag vX.Y.Z` 核对版本一致性。
4. 用 GitHub CLI 创建 Release，明确列出五种包与清单，不把未知 ZIP 一起上传。已有同名 Release 时停止，不静默覆盖。
5. 在 Release 中填写具体变化与验证边界。向其他市场提交前核对最新规范与用户授权，分别记录实际返回的版本和 URL。

例如，将下面的版本替换为 `distribution.json` 中的版本；先准备本轮发布说明文件，再执行：

```sh
gh release create vX.Y.Z --verify-tag --title "上下文协作治理 vX.Y.Z" \
  --notes-file /本轮发布说明的路径 \
  dist/generic/context-continuity.zip \
  dist/workbuddy/context-continuity-workbuddy.zip \
  dist/skillhub/context-continuity-skillhub.zip \
  dist/claude/context-continuity-claude.zip \
  dist/openai/context-continuity-openai.zip \
  dist/SHA256SUMS
```

## 可选的自动发布

仓库中的 `templates/github-actions.yml` 提供验证与标签发布工作流。当前 GitHub 登录的 OAuth 权限不包含 `workflow`，因此首版保留模板并手动发布，不声称 CI 已启用。

需要启用时，在具备工作流写入权限的环境中，将模板移动到 `.github/workflows/verify-and-release.yml`，审阅并推送。之后普通推送和 PR 执行验证；匹配版本的标签在验证成功后构建并创建 Release。发布 job 仅申请仓库内容写权限，不使用个人令牌。首次启用后仍需观察实际运行结果。

新增平台只增加必要适配，不分叉通用正文。平台规范不能确认时提供通用包并说明缺口，不猜测字段或宣称兼容。
