import argparse
import base64
import json
import urllib.parse
import urllib.request
import urllib.error
import re
import sys


def create_parser():
    parser = argparse.ArgumentParser(description="Инструмент визуализации графа зависимостей для менеджера пакетов")

    parser.add_argument("--package", help="Имя анализируемого пакета")
    parser.add_argument("--repo_url", help="URL-адрес репозитория или путь к файлу тестового репозитория")
    parser.add_argument("--repo_mode", choices=["remote", "local"], help="Режим работы с тестовым репозиторием: 'remote' или 'local'")
    parser.add_argument("--version", default="latest", help="Версия пакета (по умолчанию: latest)")
    parser.add_argument("--ascii_tree", help="Режим вывода зависимостей в формате ASCII-дерева")
    parser.add_argument("--filter", help="Подстрока для фильтрации пакетов")

    return parser

def validate_args(args):
    errors = []

    if not args.package:
        errors.append("--package не может быть пустым")

    if not args.repo_url:
        errors.append("--repo_url не может быть пустым")

    if args.repo_mode not in ["remote", "local"]:
        errors.append("--repo_mode должен быть 'remote' или 'local'")

    if not args.version:
        errors.append("--version не может быть пустой")

    if errors:
        for error in errors:
            print(f"Ошибка: {error}", file=sys.stderr)
        sys.exit(1)

def get_pyproject_toml(repo_url, ref):
    parsed_url = urllib.parse.urlparse(repo_url) # парсим url
    path = parsed_url.path.strip('/').split('/') # получаем путь из url
    if len(path) < 2:
        print("Неверный формат url репозитория GitHub")
        return None
    owner = path[0]
    repo = path[1]
    api_url = f"https://api.github.com/repos/{owner}/{repo}/contents/pyproject.toml?ref={ref}" # url для запроса к GitHUb API для доступа к файлу
    try:
        req = urllib.request.Request(api_url) # объект для запроса
        req.add_header('User-Agent', 'Dependency-Visualizer-Tool') # требование GitHub API для запросов
        response = urllib.request.urlopen(req) # делаем HTTP запрос и ждем ответ
    except urllib.error.HTTPError as e: # нет такого файла или превышен лимит запросов
        if e.code == 404:
            print("Файл pyproject.toml не найден в репозитории на GitHub")
        else:
            print("Ошибка при запросе")
        return None
    except urllib.error.URLError as e: # неверный URL
        print("Ошибка соединения")

    data = json.loads(response.read().decode("utf-8")) # парсим строку как json, так как GitHub API возвращает в таком формате
    content_b64 = data["content"]
    content_decoded = base64.b64decode(content_b64).decode("utf-8") # декодируем наши данные
    return content_decoded

def get_package_name(dep_string):
    match = re.match(r'^([a-zA-Z0-9\-_.]+)', dep_string.strip())
    if match:
        return match.group(1)
    return dep_string.strip()

def get_dependencies(content):
    lines = toml_content.splitlines()
    all_deps = set()
    current_section = "" # Текущая TOML-секция
    in_multiline_list = False
    multiline_content = ""
    for line in lines:
        stripped_line = line.strip()
        section_match = re.match(r'^\[(.+)\]$', line) # строка - TOML секция?
        if section_match:
            current_section = section_match.group(1).strip()
            if 'dependencies' in current_section.lower():
                pass
            else:
                in_multiline_list = False
                multiline_content = ""
            continue
        if 'dependencies' not in current_section.lower():
            continue
        assignment_match = re.match(r'^\s*([^\s=]+[^\s=]*)\s*=\s*(\[.*?\]|".*?"|\'.*?\'|\{.*?\})\s*$', line, re.DOTALL) # нужна строка с зав-ми?

        if assignment_match:
            key = assignment_match.group(1)  # например, 'pytest'
            value_content = assignment_match.group(2) # например, '["greenlet>=1"]', '">=3.10,<4"', '{ version = ">=17.0.0", optional = true }'
            if value_content.startswith('[') and value_content.endswith(']'):
                # Это список
                list_content = value_content[1:-1]  # убираем скобки
                dep_strings = re.findall(r'"([^"]*)"|\'([^\']*)\'', list_content)
                deps_raw = [item[0] if item[0] else item[1] for item in dep_strings] # если "" то добавить текст в "" иначе текст в ''
                deps_names = [get_package_name(dep) for dep in deps_raw]
                all_deps.update(deps_names)

            elif (value_content.startswith('"') and value_content.endswith('"')) or (value_content.startswith("'") and value_content.endswith("'")): # например pytest = "7.4.4"
                all_deps.add(key)

            elif value_content.startswith('{') and value_content.endswith('}'):
                all_deps.add(key)

            in_multiline_list = False
            multiline_content = ""
            continue

        multiline_list_match = re.match(r'^\s*([^\s=]+[^\s=]*)\s*=\s*\[\s*(.*)', line, re.DOTALL) # многострочный список
        if multiline_list_match:
            key = multiline_list_match.group(1)  # имя зависимости
            in_multiline_list = True
            remaining_on_first_line = multiline_list_match.group(2).strip()  # остаток строки после "["

            if remaining_on_first_line:  # если после [ есть содержимое
                first_line_deps = re.findall(r'"([^"]*)"|\'([^\']*)\'', remaining_on_first_line)
                first_line_deps_raw = [item[0] if item[0] else item[1] for item in first_line_deps]
                first_line_deps_names = [get_package_name(dep) for dep in first_line_deps_raw]
                all_deps.update(first_line_deps_names)

                multiline_content = remaining_on_first_line + "\n"

            else:
                # если после '[' идут только пробелы, начинаем накапливать с новой строки
                multiline_content = ""
            continue


        if in_multiline_list: # внутри многострочного списка
            if stripped_line.endswith(']'):
                multiline_content += line[:line.rfind(']')] # добавляем текущую строку
                dep_strings = re.findall(r'"([^"]*)"|\'([^\']*)\'', multiline_content)
                deps_raw = [item[0] if item[0] else item[1] for item in dep_strings]
                deps_names = [get_package_name(dep) for dep in deps_raw]
                all_deps.update(deps_names)
                in_multiline_list = False # Сбрасываем флаги
                multiline_content = ""
            else:
                multiline_content += line + "\n"  # собираем строку
    if not all_deps:
        print("Зависимости не найдены")
        return None

    return list(all_deps)


parser = create_parser()
args = parser.parse_args()

validate_args(args)

branch = "main"
if args.version != "latest":
    branch = args.version()

toml_content = get_pyproject_toml(args.repo_url, branch)
dependencies = get_dependencies(toml_content)
for dep in sorted(dependencies):
    print(dep)
