"""
案件スコアリングツール (job_scorer)
====================================
クラウドソーシングの案件リストを、受注戦略に沿って自動でスコアリング・ランク付けするデモ。

Agentic（現役エンジニア × AI × 業務自動化）が実際に毎朝の案件選別で使っている
ロジックを、単体で動く形に切り出したサンプルです。

特長:
- 標準ライブラリのみ（追加インストール不要）
- AI/自動化・Python・API などの「狙い目キーワード」で加点
- 受託常駐・PM など本業と競合しうる案件にフラグ（競業避止チェック）
- 予算・稼働規模でフィルタ

使い方:
    python job_scorer.py            # 同梱のサンプル案件で実行
    python job_scorer.py jobs.json  # 自前のJSON（list[dict]）で実行

入力JSONの各案件フォーマット:
    {"title": "...", "budget": 80000, "site": "CrowdWorks"}
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field

# --- スコアリング設定 ---------------------------------------------------------

# 狙い目キーワード（出現で加点）
POSITIVE_KEYWORDS: dict[str, int] = {
    "ai": 3, "claude": 3, "chatgpt": 3, "llm": 3, "エージェント": 3,
    "自動化": 3, "スクレイピング": 2, "api": 2, "python": 2,
    "n8n": 2, "gas": 2, "zapier": 2, "bot": 2, "line": 1,
}

# 避けたい/減点キーワード（単純作業・対象外領域）
NEGATIVE_KEYWORDS: dict[str, int] = {
    "ライティング": 3, "記事作成": 3, "データ入力": 3,
    "動画編集": 2, "アンケート": 2, "fx": 2, "投資": 2,
}

# 競業避止フラグ（本業＝システム開発会社と被りやすい受託常駐・PM系）
COMPETITION_FLAGS: tuple[str, ...] = ("常駐", "pm", "pmo", "ses", "プロジェクトマネージャー")

MIN_BUDGET = 30_000  # これ未満は減点（低単価タスク回避）


@dataclass
class ScoredJob:
    title: str
    budget: int
    site: str
    score: int = 0
    reasons: list[str] = field(default_factory=list)
    competition_risk: bool = False

    @property
    def flag(self) -> str:
        return "⚠️" if self.competition_risk else "○"


def score_job(title: str, budget: int, site: str) -> ScoredJob:
    """1案件をスコアリングする。"""
    job = ScoredJob(title=title, budget=budget, site=site)
    low = title.lower()

    for kw, pts in POSITIVE_KEYWORDS.items():
        if kw in low:
            job.score += pts
            job.reasons.append(f"+{pts} {kw}")

    for kw, pts in NEGATIVE_KEYWORDS.items():
        if kw in low:
            job.score -= pts
            job.reasons.append(f"-{pts} {kw}")

    if budget and budget >= 100_000:
        job.score += 2
        job.reasons.append("+2 高単価")
    elif budget and budget < MIN_BUDGET:
        job.score -= 2
        job.reasons.append("-2 低単価")

    if any(flag in low for flag in COMPETITION_FLAGS):
        job.competition_risk = True
        job.reasons.append("⚠️ 競業避止チェック要")

    return job


def rank(jobs: list[dict]) -> list[ScoredJob]:
    scored = [score_job(j["title"], j.get("budget", 0), j.get("site", "-")) for j in jobs]
    return sorted(scored, key=lambda x: x.score, reverse=True)


def render(ranked: list[ScoredJob]) -> str:
    lines = ["順位  点  競業  サイト         案件", "-" * 72]
    for i, j in enumerate(ranked, 1):
        lines.append(f"{i:>2}   {j.score:>3}   {j.flag}   {j.site:<12} {j.title[:34]}")
    return "\n".join(lines)


SAMPLE_JOBS: list[dict] = [
    {"title": "AI自動化・エージェント開発（Claude活用）", "budget": 200000, "site": "Lancers"},
    {"title": "EC業務改善・自動化パートナー（n8n・API連携）", "budget": 120000, "site": "CrowdWorks"},
    {"title": "【Python】Amazon書籍の自動抽出システム開発", "budget": 150000, "site": "Lancers"},
    {"title": "Webシステム開発 PM・常駐（フルタイム）", "budget": 500000, "site": "CrowdWorks"},
    {"title": "AIを使った記事作成・ライティング（未経験OK）", "budget": 5000, "site": "CrowdWorks"},
    {"title": "Slack Bot開発・AI機能連携の実装", "budget": 80000, "site": "Lancers"},
]


def main(argv: list[str]) -> int:
    if len(argv) > 1:
        with open(argv[1], encoding="utf-8") as f:
            jobs = json.load(f)
    else:
        jobs = SAMPLE_JOBS
        print("(サンプル案件で実行中。`python job_scorer.py jobs.json` で自前データも可)\n")

    ranked = rank(jobs)
    print(render(ranked))
    print("\n★ おすすめTOP3")
    for j in [r for r in ranked if not r.competition_risk][:3]:
        print(f"  - {j.title}  （{j.score}点 / {j.site}）  {'  '.join(j.reasons)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
