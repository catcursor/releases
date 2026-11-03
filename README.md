# 公共发布仓库

`catcursor/releases` 用于集中发布多个项目的安装包、压缩包和更新说明。源码继续保存在各自的仓库中；下载请前往 [Releases](https://github.com/catcursor/releases/releases)。

## 命名约定

每个项目的每个版本单独创建一个 Release。同一版本的不同系统、架构附件放在同一个 Release 中。

| 项目 | Release 标签 | 标题 | 附件示例 |
| --- | --- | --- | --- |
| aimd | `aimd-v1.0.0` | `aimd v1.0.0` | `aimd-1.0.0-windows-x64.zip` |
| 其他项目（示例） | `toolbox-v2.1.0` | `toolbox v2.1.0` | `toolbox-2.1.0-linux-x64.tar.gz` |

标签统一采用 `<项目名>-v<版本号>`，预发布可用 `aimd-v1.1.0-beta.1`。附件名包含项目、版本、系统和架构，避免混淆。

## 本地发布

下面以 aimd 1.0.0 为例。路径、版本和更新说明均为示例，执行前替换为实际值。命令可在源码仓库或构建产物目录执行，不需要克隆本仓库。

### 1. 准备

安装 [GitHub CLI](https://cli.github.com/)，并登录有本仓库写权限的账号：

```powershell
gh auth login
gh auth status
```

在源码仓库完成构建，准备明确要公开的安装包，以及 UTF-8 编码的 `release-notes.md`。说明文件应包含版本、改动和安装方法。建议附带 SHA-256 校验文件。所有上传附件和发布说明都会公开，请在上传前检查内容。

### 2. 直接发布

```powershell
gh release create aimd-v1.0.0 ./dist/aimd-1.0.0-windows-x64.zip --repo catcursor/releases --title "aimd v1.0.0" --notes-file ./release-notes.md --latest=false
```

多个附件可依次列在标签后面。始终显式指定 `--repo catcursor/releases`，避免发布到源码仓库。

### 3. 先创建草稿，再发布

如需先检查附件和说明，使用这一流程代替上一步：

```powershell
gh release create aimd-v1.0.0 ./dist/aimd-1.0.0-windows-x64.zip --repo catcursor/releases --title "aimd v1.0.0" --notes-file ./release-notes.md --latest=false --draft
```

登录后在 [Releases 页面](https://github.com/catcursor/releases/releases) 检查草稿；确认完成后执行：

```powershell
gh release edit aimd-v1.0.0 --repo catcursor/releases --draft=false --latest=false
```

预发布版本在创建时增加 `--prerelease`，并使用对应的预发布标签和附件名。

### 4. 验证与补传

```powershell
gh release view aimd-v1.0.0 --repo catcursor/releases
gh release upload aimd-v1.0.0 ./dist/aimd-1.0.0-linux-x64.tar.gz --repo catcursor/releases
```

补传通常应在草稿阶段完成。已存在的 Release 不要重复执行 `create`。同一 Release 中附件名必须唯一；不要默认使用 `--clobber`，它会先删除同名旧附件。正式发布后的修正建议发布新版本；如启用不可变 Release，发布后的附件不能修改或补传。

## 标签、源码与更新说明

- Release 标签属于本发布仓库。标签不存在时，CLI 默认从本仓库默认分支创建标签，不会自动同步源码仓库的标签或提交。
- `--target` 指向的是本发布仓库中的分支或提交，不能直接填写仅存在于私有源码仓库中的提交。
- 构建来源和源码版本在原仓库维护；需要追溯时，在原仓库保留对应标签或构建记录。
- GitHub 自动附带的 “Source code” 压缩包是本发布仓库的内容。安装包应从手动上传的附件下载。
- 更新说明使用源码项目编写的 `release-notes.md`；`--generate-notes` 只依据本发布仓库，不能自动生成私有源码项目的改动说明。

## 下载与自动更新

发布后，版本页面和附件链接遵循以下格式（下方为格式示例，发布后才有效）：

```text
https://github.com/catcursor/releases/releases/tag/aimd-v1.0.0
https://github.com/catcursor/releases/releases/download/aimd-v1.0.0/aimd-1.0.0-windows-x64.zip
```

本仓库由多个项目共享，`/releases/latest` 及 `/releases/latest/download/...` 不能分别代表每个项目的最新版。示例命令统一使用 `--latest=false`；应用应使用明确版本链接，或另行维护每个项目的更新清单（如 `updates/aimd.json`）。本仓库目前仅提供发布说明，尚未配置更新清单或自动更新服务。

## 从 GitHub Actions 跨仓库发布

源码仓库工作流自带的 `GITHUB_TOKEN` 仅限当前仓库，不能直接写入本发布仓库。可使用仅授权 `catcursor/releases`、具有 **Contents: Read and write** 权限的 fine-grained PAT，或具有对应权限的 GitHub App token。

将令牌保存到源码仓库的 Actions Secret `RELEASES_TOKEN`，不要写入代码。构建完成后可添加以下步骤；此示例采用 Bash，假定 runner 已有 `gh`，当前目录中已生成指定附件和更新说明。它是发布步骤片段，不是完整构建工作流：

```yaml
- name: Publish aimd release
  shell: bash
  env:
    GH_TOKEN: ${{ secrets.RELEASES_TOKEN }}
    RELEASE_TAG: aimd-v1.0.0
    RELEASE_TITLE: aimd v1.0.0
  run: |
    gh release create "$RELEASE_TAG" \
      ./dist/aimd-1.0.0-windows-x64.zip \
      --repo catcursor/releases \
      --title "$RELEASE_TITLE" \
      --notes-file ./release-notes.md \
      --latest=false
```

实际工作流应让标签、标题和附件版本保持一致。若创建或上传失败，先检查目标 Release 是否已留下草稿及部分附件，再决定补传或继续发布，避免直接重复创建。

## 官方参考

- [创建 Release](https://cli.github.com/manual/gh_release_create)
- [编辑 Release](https://cli.github.com/manual/gh_release_edit)
- [上传附件](https://cli.github.com/manual/gh_release_upload)
- [GitHub Release 说明](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)
- [Release 下载链接](https://docs.github.com/en/repositories/releasing-projects-on-github/linking-to-releases)
- [GITHUB_TOKEN 权限范围](https://docs.github.com/en/actions/concepts/security/github_token)
- [Release API 权限](https://docs.github.com/en/rest/releases/releases#create-a-release)
