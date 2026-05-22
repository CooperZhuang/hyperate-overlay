#!/usr/bin/env python3
"""本地自动发布脚本 - 自动更新版本号、同步依赖、提交更改、推送并触发 GitHub 工作流"""

import argparse
import re
import subprocess
import sys


def run_command(cmd: list[str], cwd: str | None = None) -> tuple[bool, str]:
    """运行命令并返回 (成功, 输出)"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)


def get_current_version() -> str | None:
    """从 pyproject.toml 获取当前版本号"""
    try:
        with open("pyproject.toml", encoding="utf-8") as f:
            content = f.read()
            match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
            return match.group(1) if match else None
    except FileNotFoundError:
        print("❌ 错误：pyproject.toml文件不存在")
        return None


def has_changes() -> bool:
    """检查是否有待提交的更改"""
    success, output = run_command(["git", "status", "--porcelain"])
    return success and bool(output.strip())


def update_version(version_type: str) -> str | None:
    """更新版本号"""
    current = get_current_version()
    if not current:
        return None

    print(f"当前版本: {current}")

    match = re.match(
        r"^(\d+)\.(\d+)\.(\d+)(-[a-zA-Z0-9.]+)?(\+[a-zA-Z0-9.]+)?$", current
    )
    if not match:
        print(f"❌ 错误：版本号格式不正确: {current}")
        return None

    major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
    prerelease = match.group(4) or ""
    build = match.group(5) or ""

    if version_type == "major":
        major += 1
        minor = 0
        patch = 0
    elif version_type == "minor":
        minor += 1
        patch = 0
    elif version_type == "patch":
        patch += 1
    else:
        print(f"❌ 错误：不支持的版本类型: {version_type}")
        return None

    new_version = f"{major}.{minor}.{patch}{prerelease}{build}"
    print(f"新版本: {new_version}")

    try:
        with open("pyproject.toml", encoding="utf-8") as f:
            content = f.read()

        new_content = re.sub(
            r'^(version\s*=\s*)"([^"]+)"',
            f'\\1"{new_version}"',
            content,
            flags=re.MULTILINE,
        )

        with open("pyproject.toml", "w", encoding="utf-8") as f:
            f.write(new_content)

        print(f"✅ 已更新pyproject.toml版本为: {new_version}")
        return new_version
    except Exception as e:
        print(f"❌ 更新pyproject.toml失败: {e}")
        return None


def sync_dependencies() -> bool:
    """同步依赖 (uv sync)"""
    print("\n\U0001f504 同步依赖...")
    success, output = run_command(["uv", "sync"])
    if success:
        print("✅ 依赖同步完成")
        return True
    print(f"❌ 依赖同步失败: {output}")
    return False


def push_changes() -> bool:
    """推送更改到远程仓库"""
    print("\n\U0001f680 推送到GitHub...")
    success, output = run_command(["git", "push", "origin", "main"])
    if success:
        print("✅ 推送完成")
        print("\U0001f4e6 GitHub Actions工作流已触发")
        print("   请查看: https://github.com/CooperZhuang/hyperate-overlay/actions")
        return True
    print(f"❌ 推送失败: {output}")
    return False


def create_tag(version: str) -> bool:
    """创建本地标签"""
    print(f"\n\U0001f3f7️  创建标签 v{version}...")
    success, output = run_command(
        ["git", "tag", "-a", f"v{version}", "-m", f"Release version {version}"]
    )
    if success:
        print(f"✅ 标签 v{version} 已创建")
        return True
    print(f"⚠️  标签创建失败: {output}")
    return False


def commit_changes(version: str, commit_type: str = "chore") -> bool:
    """提交更改 (命令行模式)"""
    if not has_changes():
        print("⚠️  没有需要提交的更改")
        return True

    print("\n\U0001f4dd 提交更改...")
    print("添加所有更改的文件...")
    success, output = run_command(["git", "add", "."])
    if not success:
        print(f"❌ 添加文件失败: {output}")
        return False

    commit_msg = f"{commit_type}: bump version to {version}"
    success, output = run_command(["git", "commit", "-m", commit_msg])
    if success:
        print(f"✅ 提交完成: {commit_msg}")
        return True
    print(f"❌ 提交失败: {output}")
    return False


def commit_with_message(commit_msg: str | None) -> bool:
    """使用自定义提交信息提交，commit_msg 为 None 时使用编辑器"""
    if not has_changes() and commit_msg is not None:
        print("⚠️  没有需要提交的更改")
        return True

    print("\n\U0001f4dd 提交更改...")
    print("添加所有更改的文件...")
    success, output = run_command(["git", "add", "."])
    if not success:
        print(f"❌ 添加文件失败: {output}")
        return False

    if commit_msg is None:
        print("正在打开编辑器输入提交信息...")
        success, output = run_command(["git", "commit"])
    else:
        success, output = run_command(["git", "commit", "-m", commit_msg])

    if success:
        if commit_msg is None:
            print("✅ 提交完成（使用编辑器输入）")
        else:
            print(f"✅ 提交完成: {commit_msg}")
        return True
    print(f"❌ 提交失败: {output}")
    return False


def _get_commit_message(current_version: str, new_version: str) -> tuple[str, str | None]:
    """获取提交信息 (交互式模式)"""
    print()
    default_msg = f"chore: bump version to {new_version}"
    print(f"默认提交信息: '{default_msg}'")
    print("\n✅ 将使用编辑器输入提交信息")
    print("   提交时将打开编辑器，保存并关闭后继续")
    return new_version, None


def interactive_mode() -> tuple[str, str | None]:
    """交互式发布模式"""
    print("=" * 60)
    print("\U0001f680 交互式发布模式")
    print("=" * 60)

    current_version = get_current_version()
    if not current_version:
        sys.exit(1)

    print(f"当前版本: {current_version}")
    print()

    print("请选择版本更新类型:")
    print("1) patch (修订号) - bug修复，向后兼容")
    print("2) minor (次版本号) - 新功能，向后兼容")
    print("3) major (主版本号) - 不兼容的API修改")
    print("4) 手动输入版本号")

    while True:
        choice = input("请输入选择 (1-4): ").strip()
        if choice in ("1", "2", "3", "4"):
            break
        print("❌ 无效选择，请重新输入")

    if choice == "4":
        while True:
            manual = input("请输入新版本号 (格式: X.Y.Z): ").strip()
            if re.match(
                r"^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9.]+)?(\+[a-zA-Z0-9.]+)?$",
                manual,
            ):
                print(f"新版本: {manual}")
                confirm = input(f"确认更新到版本 {manual}? (y/N): ").strip().lower()
                if confirm == "y":
                    try:
                        with open("pyproject.toml", encoding="utf-8") as f:
                            content = f.read()
                        new_content = re.sub(
                            r'^(version\s*=\s*)"([^"]+)"',
                            f'\\1"{manual}"',
                            content,
                            flags=re.MULTILINE,
                        )
                        with open("pyproject.toml", "w", encoding="utf-8") as f:
                            f.write(new_content)
                        print(f"✅ 已更新pyproject.toml版本为: {manual}")
                        new_version = manual
                        break
                    except Exception as e:
                        print(f"❌ 更新pyproject.toml失败: {e}")
                        sys.exit(1)
                else:
                    print("❌ 用户取消")
                    sys.exit(0)
            else:
                print("❌ 版本号格式不正确，请重新输入")

        print("\n\U0001f504 同步依赖...")
        success, output = run_command(["uv", "sync"])
        if not success:
            print(f"❌ 依赖同步失败: {output}")
            sys.exit(1)
        print("✅ 依赖同步完成")

        return _get_commit_message(current_version, new_version)

    version_type = {"1": "patch", "2": "minor", "3": "major"}[choice]
    new_version = update_version(version_type)
    if not new_version:
        sys.exit(1)

    print("\n\U0001f504 同步依赖...")
    success, output = run_command(["uv", "sync"])
    if not success:
        print(f"❌ 依赖同步失败: {output}")
        sys.exit(1)
    print("✅ 依赖同步完成")

    return _get_commit_message(current_version, new_version)


def main() -> None:
    parser = argparse.ArgumentParser(description="本地自动发布脚本")
    parser.add_argument(
        "type",
        nargs="?",
        choices=["patch", "minor", "major"],
        help="版本更新类型",
    )
    parser.add_argument(
        "--commit-type",
        default="chore",
        choices=["chore", "feat", "fix", "docs", "style", "refactor", "test", "build"],
        help="提交类型 (命令行模式)",
    )
    parser.add_argument(
        "--commit-message",
        help="自定义提交信息 (命令行模式)",
    )
    parser.add_argument("--no-sync", action="store_true", help="跳过 uv sync")
    parser.add_argument("--no-push", action="store_true", help="跳过推送")
    parser.add_argument("--create-tag", action="store_true", help="创建本地Git标签")
    parser.add_argument("-i", "--interactive", action="store_true", help="交互式模式")

    args = parser.parse_args()

    if args.interactive or not args.type:
        new_version, commit_msg = interactive_mode()
        args.no_sync = True
    else:
        print("=" * 60)
        print("\U0001f680 本地自动发布脚本")
        print("=" * 60)

        new_version = update_version(args.type)
        if not new_version:
            sys.exit(1)

        commit_msg = args.commit_message or f"{args.commit_type}: bump version to {new_version}"

    if not args.no_sync:
        if not sync_dependencies():
            sys.exit(1)

    if args.interactive or not args.type:
        if not commit_with_message(commit_msg):
            sys.exit(1)
    else:
        if not commit_changes(new_version, args.commit_type):
            sys.exit(1)

    if args.create_tag or (
        args.interactive
        and input("\n创建Git标签? (y/N): ").strip().lower() == "y"
    ):
        create_tag(new_version)

    push_confirm = True
    if args.interactive and not args.no_push:
        push_confirm = input("\n推送到GitHub? (Y/n): ").strip().lower() != "n"

    if not args.no_push and push_confirm:
        if not push_changes():
            sys.exit(1)
    elif args.interactive and not push_confirm:
        print("⏸️  跳过推送步骤")

    print("\n" + "=" * 60)
    print("\U0001f389 发布流程完成！")
    print("=" * 60)
    print(f"版本: {new_version}")
    print(f"标签: v{new_version}")
    if not args.no_push and push_confirm:
        print("GitHub Actions工作流已触发")
        print("请等待工作流完成并创建Release")
    else:
        print("（本地操作完成，未推送到远程）")
    print("\n下一步:")
    print(
        "1. 查看GitHub Actions: "
        "https://github.com/CooperZhuang/hyperate-overlay/actions"
    )
    print(
        "2. 查看Releases: "
        "https://github.com/CooperZhuang/hyperate-overlay/releases"
    )
    print("=" * 60)


if __name__ == "__main__":
    main()
