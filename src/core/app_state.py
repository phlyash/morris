import json
from pathlib import Path
from typing import List

from src.config import RECENT_PROJECTS_FILE
from src.core.project import Project


class AppState:
    @staticmethod
    def get_recent_projects() -> List[Project]:
        """
        Возвращает список объектов Project.
        Они НЕ загружены (is_loaded=False), но имеют path и name.
        """
        if not RECENT_PROJECTS_FILE.exists():
            return []

        try:
            with open(RECENT_PROJECTS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return []

        project_objects = []
        needs_save = False

        for item in data:
            path_str = item.get('path')
            name_cached = item.get('name')

            if path_str and Path(path_str).exists():
                # Создаем ЛЕГКИЙ объект (без сканирования видео)
                # Мы используем name из кэша, чтобы сразу показать его в меню
                proj = Project(path_str, cached_name=name_cached)
                project_objects.append(proj)
            else:
                # Если путь больше не существует, помечаем, что файл надо обновить
                needs_save = True

        if needs_save:
            # Пересохраняем только валидные
            AppState._save_list(project_objects)

        return project_objects

    @staticmethod
    def add_recent(project: Project):
        """
        Принимает объект Project (даже только что созданный)
        и добавляет его в начало списка.
        """
        # 1. Получаем текущие (уже как объекты)
        current_projects = AppState.get_recent_projects()

        # 2. Удаляем этот проект из списка, если он там уже есть (сравнение по пути)
        # Приводим пути к resolve(), чтобы исключить разницу слэшей
        new_path = project.path.resolve()
        current_projects = [p for p in current_projects if p.path.resolve() != new_path]

        # 3. Вставляем в начало
        current_projects.insert(0, project)

        # 4. Обрезаем до 10
        current_projects = current_projects[:10]

        # 5. Сохраняем JSON
        AppState._save_list(current_projects)

    @staticmethod
    def _save_list(projects: List[Project]):
        """Сериализует список объектов в JSON"""
        data_to_save = []
        for p in projects:
            data_to_save.append({
                'path': str(p.path),
                'name': p.name  # Сохраняем текущее имя в кэш
            })

        try:
            with open(RECENT_PROJECTS_FILE, 'w', encoding='utf-8') as f:
                json.dump(data_to_save, f, ensure_ascii=False, indent=4)
        except OSError as e:
            pass
