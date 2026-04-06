"""Internationalization support for MAD — Korean, English, Chinese status messages."""

from __future__ import annotations

from mad.config import load_settings

# Supported languages
SUPPORTED_LANGUAGES = ("en", "ko", "zh")

# Translation dictionaries keyed by message ID.
_TRANSLATIONS: dict[str, dict[str, str]] = {
    # Phase names
    "phase.brainstorm": {
        "en": "Brainstorm",
        "ko": "브레인스토밍",
        "zh": "头脑风暴",
    },
    "phase.plan": {
        "en": "Planning",
        "ko": "계획 수립",
        "zh": "规划",
    },
    "phase.code": {
        "en": "Coding",
        "ko": "코딩",
        "zh": "编码",
    },
    "phase.review": {
        "en": "Review",
        "ko": "리뷰",
        "zh": "审查",
    },
    "phase.fix": {
        "en": "Fix",
        "ko": "수정",
        "zh": "修复",
    },
    "phase.finalize": {
        "en": "Finalization",
        "ko": "마무리",
        "zh": "完成",
    },
    "phase.evolution": {
        "en": "Evolution",
        "ko": "진화 학습",
        "zh": "进化学习",
    },

    # Status messages
    "status.running": {
        "en": "Running",
        "ko": "실행 중",
        "zh": "运行中",
    },
    "status.completed": {
        "en": "Completed",
        "ko": "완료",
        "zh": "已完成",
    },
    "status.failed": {
        "en": "Failed",
        "ko": "실패",
        "zh": "失败",
    },
    "status.approved": {
        "en": "Approved",
        "ko": "승인됨",
        "zh": "已批准",
    },
    "status.needs_work": {
        "en": "Needs Work",
        "ko": "수정 필요",
        "zh": "需要修改",
    },

    # Bot responses
    "bot.started": {
        "en": "MAD pipeline started for project: {project}",
        "ko": "MAD 파이프라인이 프로젝트에 대해 시작되었습니다: {project}",
        "zh": "MAD 管道已为项目启动: {project}",
    },
    "bot.resumed": {
        "en": "Resuming project: {project}",
        "ko": "프로젝트를 재개합니다: {project}",
        "zh": "恢复项目: {project}",
    },
    "bot.stopped": {
        "en": "Pipeline stopped.",
        "ko": "파이프라인이 중지되었습니다.",
        "zh": "管道已停止。",
    },
    "bot.status": {
        "en": "Project: {project}\nPhase: {phase}\nIteration: {iteration}",
        "ko": "프로젝트: {project}\n단계: {phase}\n반복: {iteration}",
        "zh": "项目: {project}\n阶段: {phase}\n迭代: {iteration}",
    },
    "bot.no_active": {
        "en": "No active project. Use `!mad run <dir> \"<idea>\"` to start one.",
        "ko": "활성 프로젝트가 없습니다. `!mad run <dir> \"<idea>\"`로 시작하세요.",
        "zh": "没有活动项目。使用 `!mad run <dir> \"<idea>\"` 开始一个。",
    },
    "bot.language_set": {
        "en": "Language set to: {lang}",
        "ko": "언어가 설정되었습니다: {lang}",
        "zh": "语言已设置为: {lang}",
    },
    "bot.unknown_command": {
        "en": "Unknown command. Type `!mad help` to see all commands.",
        "ko": "알 수 없는 명령입니다. `!mad help`를 입력하여 모든 명령을 확인하세요.",
        "zh": "未知命令。输入 `!mad help` 查看所有命令。",
    },
    "bot.already_running": {
        "en": "A pipeline is already running. Use `!mad stop` first.",
        "ko": "파이프라인이 이미 실행 중입니다. 먼저 `!mad stop`을 사용하세요.",
        "zh": "管道已在运行中。请先使用 `!mad stop`。",
    },

    # Summary labels
    "summary.score": {
        "en": "Score",
        "ko": "점수",
        "zh": "分数",
    },
    "summary.duration": {
        "en": "Duration",
        "ko": "소요 시간",
        "zh": "持续时间",
    },
    "summary.cost": {
        "en": "Cost",
        "ko": "비용",
        "zh": "费用",
    },
    "summary.tickets": {
        "en": "Tickets",
        "ko": "티켓",
        "zh": "工单",
    },
    "summary.issues": {
        "en": "Issues",
        "ko": "이슈",
        "zh": "问题",
    },
}


def get_language() -> str:
    """Get the current language from settings.json, defaulting to 'en'."""
    settings = load_settings()
    lang = settings.get("language", "en")
    return lang if lang in SUPPORTED_LANGUAGES else "en"


def t(key: str, lang: str | None = None, **kwargs: str) -> str:
    """Translate a message key to the specified (or configured) language.

    Args:
        key: Message key (e.g., 'phase.plan', 'bot.started').
        lang: Language code ('en', 'ko', 'zh'). Reads from settings if None.
        **kwargs: Format variables (e.g., project="my-app").

    Returns:
        Translated string, or the key itself if not found.
    """
    if lang is None:
        lang = get_language()
    if lang not in SUPPORTED_LANGUAGES:
        lang = "en"

    translations = _TRANSLATIONS.get(key, {})
    text = translations.get(lang, translations.get("en", key))

    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, IndexError):
            pass  # return unformatted if variables don't match

    return text
