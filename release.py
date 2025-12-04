#!/usr/bin/env python3
"""
本地自动发布脚本
功能：自动更新版本号、同步依赖、提交更改、推送并触发GitHub工作流
"""

import argparse
import re
import subprocess
import sys
from typing import Optional, Tuple


def run_command(cmd: str, cwd: Optional[str] = None) -> Tuple[bool, str]:
    """运行命令并返回结果"""
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
        return result.returncode == 0, result.stdout.strip()
    except Exception as e:
        return False, str(e)


def get_current_version() -> Optional[str]:
    """从pyproject.toml获取当前版本号"""
    try:
        with open("pyproject.toml", "r", encoding="utf-8") as f:
            content = f.read()
            match = re.search(r'^version\s*=\s*"([^"]+)"', content, re.MULTILINE)
            return match.group(1) if match else None
    except FileNotFoundError:
        print("❌ 错误：pyproject.toml文件不存在")
        return None


def update_version(version_type: str) -> Optional[str]:
    """更新版本号"""
    current_version = get_current_version()
    if not current_version:
        return None

    print(f"当前版本: {current_version}")

    # 解析版本号
    match = re.match(
        r"^(\d+)\.(\d+)\.(\d+)(-[a-zA-Z0-9\.]+)?(\+[a-zA-Z0-9\.]+)?$", current_version
    )
    if not match:
        print(f"❌ 错误：版本号格式不正确: {current_version}")
        return None

    major, minor, patch = int(match.group(1)), int(match.group(2)), int(match.group(3))
    prerelease = match.group(4) or ""
    build = match.group(5) or ""

    # 根据版本类型更新
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

    # 更新pyproject.toml
    try:
        with open("pyproject.toml", "r", encoding="utf-8") as f:
            content = f.read()

        # 替换版本号
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
    """同步依赖（uv sync）"""
    print("\n🔄 同步依赖...")
    success, output = run_command("uv sync")
    if success:
        print("✅ 依赖同步完成")
        return True
    else:
        print(f"❌ 依赖同步失败: {output}")
        return False


def push_changes() -> bool:
    """推送更改到远程仓库"""
    print("\n🚀 推送到GitHub...")
    success, output = run_command("git push origin main")
    if success:
        print("✅ 推送完成")
        print("📦 GitHub Actions工作流已触发")
        print("   请查看: https://github.com/CooperZhuang/hyperate-overlay/actions")
        return True
    else:
        print(f"❌ 推送失败: {output}")
        return False


def create_tag(version: str) -> bool:
    """创建本地标签（可选）"""
    print(f"\n🏷️  创建标签 v{version}...")
    success, output = run_command(
        f'git tag -a "v{version}" -m "Release version {version}"'
    )
    if success:
        print(f"✅ 标签 v{version} 已创建")
        return True
    else:
        print(f"⚠️  标签创建失败: {output}")
        return False


def get_multiline_input(prompt: str, default: str = "") -> str:
    """获取多行输入，以空行结束"""
    print(prompt)
    print("请输入多行文本（输入空行结束）:")
    lines = []
    while True:
        try:
            line = input()
            if line == "":
                break
            lines.append(line)
        except EOFError:
            break
    return "\n".join(lines) if lines else default


def _get_commit_message(current_version: str, new_version: str):
    """获取提交信息（内部辅助函数）"""
    # 直接输入提交信息
    print()
    default_msg = f"chore: bump version to {new_version}"
    print(f"默认提交信息: '{default_msg}'")

    # 询问用户是否要输入多行提交信息
    print("\n请选择提交信息输入方式:")
    print("1) 单行输入 (默认)")
    print("2) 多行输入 (适合详细说明)")

    input_choice = input("请选择 (1 或 2，默认 1): ").strip()
    if input_choice == "2":
        print("\n⚠️  注意：在Windows PowerShell中粘贴多行文本可能会出现问题")
        print("   建议使用以下方法之一：")
        print("   a) 逐行输入，最后输入一个空行结束")
        print("   b) 使用单行输入，用 '\\n' 表示换行")
        print("   c) 使用命令行模式的 --commit-message 参数")
        print()
        print("请输入多行提交信息（逐行输入，输入空行结束）:")
        lines = []
        while True:
            try:
                line = input()
                if line == "":
                    break
                lines.append(line)
            except EOFError:
                break

        # 如果用户直接按 Enter 而没有输入任何内容，使用默认值
        if not lines:
            commit_msg = default_msg
        else:
            commit_msg = "\n".join(lines)
    else:
        custom_msg = input("请输入提交信息 (直接回车使用默认值): ").strip()
        commit_msg = custom_msg if custom_msg else default_msg

    # 确认步骤
    print()
    print("请确认以下设置:")
    print(f"当前版本: {current_version}")
    print(f"新版本: {new_version}")
    print(f"提交信息: {commit_msg}")
    print()

    confirm = input("确认提交更改? (y/N): ").strip().lower()
    if confirm != "y":
        print("❌ 用户取消")
        sys.exit(0)

    return new_version, commit_msg


def interactive_mode():
    """交互式发布模式"""
    print("=" * 60)
    print("🚀 交互式发布模式")
    print("=" * 60)

    # 显示当前版本
    current_version = get_current_version()
    if not current_version:
        sys.exit(1)

    print(f"当前版本: {current_version}")
    print()

    # 选择版本更新类型
    print("请选择版本更新类型:")
    print("1) patch (修订号) - bug修复，向后兼容")
    print("2) minor (次版本号) - 新功能，向后兼容")
    print("3) major (主版本号) - 不兼容的API修改")
    print("4) 手动输入版本号")

    while True:
        choice = input("请输入选择 (1-4): ").strip()
        if choice in ["1", "2", "3", "4"]:
            break
        print("❌ 无效选择，请重新输入")

    version_type = ""
    if choice == "1":
        version_type = "patch"
    elif choice == "2":
        version_type = "minor"
    elif choice == "3":
        version_type = "major"
    elif choice == "4":
        while True:
            manual_version = input("请输入新版本号 (格式: X.Y.Z): ").strip()
            if re.match(
                r"^[0-9]+\.[0-9]+\.[0-9]+(-[a-zA-Z0-9\.]+)?(\+[a-zA-Z0-9\.]+)?$",
                manual_version,
            ):
                # 对于手动输入版本，我们需要特殊处理
                print(f"新版本: {manual_version}")
                confirm = (
                    input(f"确认更新到版本 {manual_version}? (y/N): ").strip().lower()
                )
                if confirm == "y":
                    # 直接更新版本号
                    try:
                        with open("pyproject.toml", "r", encoding="utf-8") as f:
                            content = f.read()
                        new_content = re.sub(
                            r'^(version\s*=\s*)"([^"]+)"',
                            f'\\1"{manual_version}"',
                            content,
                            flags=re.MULTILINE,
                        )
                        with open("pyproject.toml", "w", encoding="utf-8") as f:
                            f.write(new_content)
                        print(f"✅ 已更新pyproject.toml版本为: {manual_version}")
                        new_version = manual_version
                        break
                    except Exception as e:
                        print(f"❌ 更新pyproject.toml失败: {e}")
                        sys.exit(1)
                else:
                    print("❌ 用户取消")
                    sys.exit(0)
            else:
                print("❌ 版本号格式不正确，请重新输入")

        # 手动输入版本号后也需要同步依赖
        print("\n🔄 同步依赖...")
        success, output = run_command("uv sync")
        if not success:
            print(f"❌ 依赖同步失败: {output}")
            sys.exit(1)
        print("✅ 依赖同步完成")

        # 跳过自动版本更新的部分，直接进入提交信息输入
        return _get_commit_message(current_version, new_version)

    # 对于自动版本更新
    new_version = update_version(version_type)
    if not new_version:
        sys.exit(1)

    # 同步依赖
    print("\n🔄 同步依赖...")
    success, output = run_command("uv sync")
    if not success:
        print(f"❌ 依赖同步失败: {output}")
        sys.exit(1)
    print("✅ 依赖同步完成")

    return _get_commit_message(current_version, new_version)


def commit_changes(version: str, commit_type: str = "chore") -> bool:
    """提交更改"""
    print("\n📝 提交更改...")

    # 添加文件
    success, output = run_command("git add pyproject.toml uv.lock")
    if not success:
        print(f"❌ 添加文件失败: {output}")
        return False

    # 提交
    commit_msg = f"{commit_type}: bump version to {version}"
    success, output = run_command(f'git commit -m "{commit_msg}"')
    if success:
        print(f"✅ 提交完成: {commit_msg}")
        return True
    else:
        print(f"❌ 提交失败: {output}")
        return False


def commit_with_message(commit_msg: str) -> bool:
    """使用自定义提交信息提交更改"""
    print("\n📝 提交更改...")

    # 添加文件
    success, output = run_command("git add pyproject.toml uv.lock")
    if not success:
        print(f"❌ 添加文件失败: {output}")
        return False

    # 提交
    success, output = run_command(f'git commit -m "{commit_msg}"')
    if success:
        print(f"✅ 提交完成: {commit_msg}")
        return True
    else:
        print(f"❌ 提交失败: {output}")
        return False


def main():
    parser = argparse.ArgumentParser(description="本地自动发布脚本")
    parser.add_argument(
        "type",
        nargs="?",  # 改为可选参数
        choices=["patch", "minor", "major"],
        help="版本更新类型: patch(修订号), minor(次版本号), major(主版本号)",
    )
    parser.add_argument(
        "--commit-type",
        default="chore",
        choices=["chore", "feat", "fix", "docs", "style", "refactor", "test", "build"],
        help="提交类型，仅在命令行模式使用 (默认: chore)",
    )
    parser.add_argument(
        "--commit-message",
        help="自定义提交信息，覆盖默认提交信息 (命令行模式使用)",
    )
    parser.add_argument(
        "--no-sync",
        action="store_true",
        help="跳过uv sync步骤",
    )
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="跳过推送步骤（仅本地操作）",
    )
    parser.add_argument(
        "--create-tag",
        action="store_true",
        help="创建本地Git标签",
    )
    parser.add_argument(
        "--interactive",
        "-i",
        action="store_true",
        help="进入交互式模式",
    )

    args = parser.parse_args()

    # 交互式模式
    if args.interactive or not args.type:
        new_version, commit_msg = interactive_mode()
        # 注意：在交互式模式中，commit_type已包含在commit_msg中
        # 交互式模式中已经执行了uv sync，所以这里跳过
        args.no_sync = True
    else:
        # 命令行模式
        print("=" * 60)
        print("🚀 本地自动发布脚本")
        print("=" * 60)

        new_version = update_version(args.type)
        if not new_version:
            sys.exit(1)

        # 确定提交信息
        if args.commit_message:
            commit_msg = args.commit_message
        else:
            commit_msg = f"{args.commit_type}: bump version to {new_version}"

    # 2. 同步依赖（除非指定跳过）
    if not args.no_sync:
        if not sync_dependencies():
            sys.exit(1)

    # 3. 提交更改
    if args.interactive or not args.type:
        # 交互式模式使用自定义提交信息
        if not commit_with_message(commit_msg):
            sys.exit(1)
    else:
        # 命令行模式使用原有逻辑
        if not commit_changes(new_version, args.commit_type):
            sys.exit(1)

    # 4. 创建标签（可选）
    if args.create_tag or (
        args.interactive and input("\n创建Git标签? (y/N): ").strip().lower() == "y"
    ):
        create_tag(new_version)

    # 5. 推送更改（除非指定跳过）
    push_confirm = True
    if args.interactive and not args.no_push:
        push_confirm = input("\n推送到GitHub? (Y/n): ").strip().lower() != "n"

    if (not args.no_push and push_confirm) and (not args.interactive or push_confirm):
        if not push_changes():
            sys.exit(1)
    elif args.interactive and not push_confirm:
        print("⏸️  跳过推送步骤")

    print("\n" + "=" * 60)
    print("🎉 发布流程完成！")
    print("=" * 60)
    print(f"版本: {new_version}")
    print(f"标签: v{new_version}")
    if (not args.no_push and push_confirm) and (not args.interactive or push_confirm):
        print("GitHub Actions工作流已触发")
        print("请等待工作流完成并创建Release")
    else:
        print("（本地操作完成，未推送到远程）")
    print("\n下一步:")
    print(
        "1. 查看GitHub Actions: https://github.com/CooperZhuang/hyperate-overlay/actions"
    )
    print("2. 查看Releases: https://github.com/CooperZhuang/hyperate-overlay/releases")
    print("=" * 60)


if __name__ == "__main__":
    main()
