import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests
import yaml

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "audit.yml"
REPORTS_DIR = ROOT / "reports" / "audit"

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


def load_config():
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def fetch_page(url, timeout):
    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru,en;q=0.9",
    }
    started = datetime.now(timezone.utc)
    try:
        response = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        elapsed_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        return {
            "ok": True,
            "status_code": response.status_code,
            "text": response.text,
            "size": len(response.content),
            "elapsed_ms": elapsed_ms,
            "error": None,
        }
    except requests.RequestException as e:
        elapsed_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)
        return {
            "ok": False,
            "status_code": None,
            "text": "",
            "size": 0,
            "elapsed_ms": elapsed_ms,
            "error": str(e),
        }


def run_checks(page, checks):
    text_lower = page["text"].lower()
    results = []
    for check in checks or []:
        name = check.get("name", "без имени")
        ctype = check.get("type", "text")
        value = str(check.get("value", ""))
        severity = check.get("severity", "warning")
        passed = False
        detail = ""

        if ctype == "text":
            passed = value.lower() in text_lower
            detail = f"искали '{value}' в тексте"
        elif ctype == "link":
            passed = value.lower() in text_lower
            detail = f"искали '{value}' в html и тексте"
        elif ctype == "absent_text":
            passed = value.lower() not in text_lower
            detail = f"проверяли отсутствие '{value}'"
        elif ctype == "status":
            try:
                expected = int(value)
            except ValueError:
                expected = 200
            passed = page["status_code"] == expected
            detail = f"ожидали код {expected}, получили {page['status_code']}"
        else:
            detail = f"неизвестный тип проверки '{ctype}'"
            passed = False

        results.append({
            "name": name,
            "type": ctype,
            "severity": severity,
            "passed": passed,
            "detail": detail,
        })
    return results


def compute_overall(page, results):
    if not page["ok"]:
        return "problems"
    if page["status_code"] != 200:
        return "problems"
    has_critical_fail = any(
        (not r["passed"]) and r["severity"] == "critical" for r in results
    )
    if has_critical_fail:
        return "problems"
    has_warning_fail = any(
        (not r["passed"]) and r["severity"] == "warning" for r in results
    )
    if has_warning_fail:
        return "warnings"
    return "ok"


def format_text_report(report):
    lines = []
    lines.append(f"Дата: {report['checked_at']}")
    lines.append(f"URL: {report['url']}")
    lines.append(f"Код ответа: {report['status_code']}")
    lines.append(f"Размер страницы: {report['page_size']} байт")
    lines.append(f"Время ответа: {report['elapsed_ms']} мс")
    lines.append(f"Общий статус: {report['overall_status']}")
    if report.get("error"):
        lines.append(f"Ошибка запроса: {report['error']}")
    lines.append("")
    lines.append("Проверки:")
    for c in report["checks"]:
        mark = "OK" if c["passed"] else "FAIL"
        lines.append(
            f"[{mark}] {c['name']} ({c['severity']}) — {c['detail']}"
        )
    lines.append("")
    return "\n".join(lines)


def main():
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    config = load_config()
    url = config.get("url")
    timeout = int(config.get("timeout", 20))
    checks = config.get("checks", [])

    if not url:
        print("В audit.yml не задан url", file=sys.stderr)
        return 1

    page = fetch_page(url, timeout)
    results = run_checks(page, checks)
    overall = compute_overall(page, results)

    now = datetime.now(timezone.utc)
    date_str = now.strftime("%Y-%m-%d")
    iso_str = now.isoformat(timespec="seconds")

    report = {
        "url": url,
        "checked_at": iso_str,
        "status_code": page["status_code"],
        "elapsed_ms": page["elapsed_ms"],
        "page_size": page["size"],
        "overall_status": overall,
        "error": page["error"],
        "checks": results,
    }

    json_path = REPORTS_DIR / f"audit_{date_str}.json"
    txt_path = REPORTS_DIR / f"audit_{date_str}.txt"
    last_path = REPORTS_DIR / "last_status.json"

    with json_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    with txt_path.open("w", encoding="utf-8") as f:
        f.write(format_text_report(report))

    with last_path.open("w", encoding="utf-8") as f:
        json.dump(
            {
                "checked_at": iso_str,
                "overall_status": overall,
                "status_code": page["status_code"],
                "url": url,
            },
            f,
            ensure_ascii=False,
            indent=2,
        )

    print(f"Отчёт сохранён: {txt_path.name}, статус: {overall}")
    return 0


if __name__ == "__main__":
    sys.exit(main())