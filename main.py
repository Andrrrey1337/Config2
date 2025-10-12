import argparse
import sys


def create_parser():
    parser = argparse.ArgumentParser(description="Инструмент визуализации графа зависимостей для менеджера пакетов")

    parser.add_argument("--package", help="Имя анализируемого пакета")
    parser.add_argument("--repo-url", help="URL-адрес репозитория или путь к файлу тестового репозитория")
    parser.add_argument("--repo-mode", help="Режим работы с тестовым репозиторием: 'remote' или 'local'")
    parser.add_argument("--version", help="Версия пакета (по умолчанию: latest)")
    parser.add_argument("--ascii-tree", help="Режим вывода зависимостей в формате ASCII-дерева")
    parser.add_argument("--filter", help="Подстрока для фильтрации пакетов")

    return parser


def validate_args(args):
    errors = []

    if not args.package:
        errors.append("--package не может быть пустым")

    if not args.repo_url:
        errors.append("--repo-url не может быть пустым")

    if args.repo_mode not in ["remote", "local"]:
        errors.append("--repo-mode должен быть 'remote' или 'local'")

    if not args.version:
        errors.append("--version не может быть пустой")

    if errors:
        for error in errors:
            print(f"Ошибка: {error}", file=sys.stderr)
        sys.exit(1)


parser = create_parser()
args = parser.parse_args()

validate_args(args)

# выводим все параметры в формате ключ-значение
print("Параметры командной строки:")
print(f"package: {args.package}")
print(f"repo-url: {args.repo_url}")
print(f"repo-mode: {args.repo_mode}")
print(f"version: {args.version}")
print(f"ascii-tree: {args.ascii_tree}")
print(f"filter: {args.filter}")
