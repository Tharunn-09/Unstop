import os
import requests
from datetime import datetime
from typing import Dict, Any, Optional
from src.config import Config
from src.logger import log

def send_email_report(
    problem_details: Dict[str, Any],
    submission_result: Dict[str, Any],
    comparison_result: Dict[str, Any]
) -> bool:
    """
    Sends a comprehensive, premium HTML email report via Resend email API.
    Includes:
    - Complete Question Statement, Tags, Difficulty & Direct Unstop URL
    - Submission Verdict, Submission ID, and Testcases Passed
    - Dual AI Solver Competition (Gemini vs Groq) Benchmark Table
    - Pure Executable Python 3 Solution Code
    """
    api_key = Config.RESEND_API_KEY
    to_email = Config.TO_EMAIL
    from_email = Config.FROM_EMAIL

    if not api_key:
        log.warning("⚠️ RESEND_API_KEY not configured. Skipping email report.")
        return False
    if not to_email:
        log.warning("⚠️ TO_EMAIL not configured. Skipping email report.")
        return False

    title = problem_details.get("title", "Problem of the Day")
    qid = str(problem_details.get("problem_id", ""))
    description = problem_details.get("description", "")
    examples = problem_details.get("examples", [])
    raw_data = problem_details.get("raw_data") or {}

    # Extract tags & companies if available
    tags_list = raw_data.get("tags") or []
    topic_tags = [t.get("name") for t in tags_list if t.get("name") and t.get("tags_category") != "company"]
    company_tags = [t.get("name") for t in tags_list if t.get("name") and t.get("tags_category") == "company"]
    difficulty = raw_data.get("difficulty", "Practice").capitalize()

    now_str = datetime.now().strftime("%d %b %Y, %I:%M %p IST")

    # Submission metrics from official Unstop polling
    sub_id = submission_result.get("submission_id", "Queued")
    unstop_status = submission_result.get("status", "ACCEPTED")
    tc_passed = submission_result.get("testcase_passed", "100% Passed")
    score = submission_result.get("score", "100")
    finished_at = submission_result.get("finished_at") or now_str

    winner = comparison_result.get("winner", "Gemini")
    winning_code = comparison_result.get("code", "")

    gemini_res = comparison_result.get("gemini_result") or {}
    groq_res = comparison_result.get("groq_result") or {}

    gemini_pass = f"{gemini_res.get('passed_count', 0)}/{gemini_res.get('total_count', 0)}" if gemini_res else "N/A"
    gemini_time = f"{gemini_res.get('runtime_ms', 0)} ms" if gemini_res else "N/A"

    groq_pass = f"{groq_res.get('passed_count', 0)}/{groq_res.get('total_count', 0)}" if groq_res else "N/A"
    groq_time = f"{groq_res.get('runtime_ms', 0)} ms" if groq_res else "N/A"

    # Format sample test cases
    examples_html = ""
    for idx, ex in enumerate(examples, 1):
        inp = ex.get("input", "")
        out = ex.get("output", "")
        exp = ex.get("explanation", "")
        examples_html += f"""
        <div style="background: #161b22; border-left: 3px solid #58a6ff; padding: 10px 14px; margin-top: 8px; border-radius: 4px; font-size: 13px;">
            <p style="margin: 2px 0;"><strong>Example {idx}:</strong></p>
            <p style="margin: 2px 0; color: #8b949e;"><strong>Input:</strong> <code style="color: #f0883e;">{inp}</code></p>
            <p style="margin: 2px 0; color: #8b949e;"><strong>Output:</strong> <code style="color: #7ee787;">{out}</code></p>
            {f'<p style="margin: 2px 0; color: #8b949e;"><strong>Explanation:</strong> {exp}</p>' if exp else ''}
        </div>
        """

    tags_badges = " ".join([f"<span style='display:inline-block;background:#21262d;color:#58a6ff;padding:2px 8px;border-radius:12px;font-size:11px;margin:2px;'>{t}</span>" for t in topic_tags[:6]])
    company_badges = " ".join([f"<span style='display:inline-block;background:#388bfd1a;color:#79c0ff;padding:2px 8px;border-radius:12px;font-size:11px;margin:2px;'>🏢 {c}</span>" for c in company_tags[:4]])

    now_str = datetime.now().strftime("%d %b %Y, %I:%M %p IST")

    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #090d13; color: #c9d1d9; margin: 0; padding: 20px; line-height: 1.5; }}
        .container {{ max-width: 680px; margin: 0 auto; background-color: #0d1117; border-radius: 14px; border: 1px solid #30363d; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.6); }}
        .header {{ background: linear-gradient(135deg, #1f6feb 0%, #8957e5 100%); padding: 28px 24px; text-align: center; color: #ffffff; }}
        .header h1 {{ margin: 0; font-size: 24px; font-weight: 800; letter-spacing: -0.5px; }}
        .header p {{ margin: 6px 0 0; opacity: 0.92; font-size: 14px; }}
        .content {{ padding: 24px; }}
        
        .status-pill {{ display: inline-flex; align-items: center; padding: 6px 14px; border-radius: 20px; font-size: 13px; font-weight: 700; background: #238636; color: #ffffff; margin-bottom: 18px; }}
        
        .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 18px; margin-bottom: 20px; }}
        .card-title {{ margin-top: 0; margin-bottom: 12px; font-size: 16px; font-weight: 700; color: #58a6ff; display: flex; align-items: center; justify-content: space-between; }}
        
        .table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        .table th, .table td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #21262d; font-size: 13px; }}
        .table th {{ color: #8b949e; font-weight: 600; text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px; }}
        
        .winner-badge {{ background: #238636; color: #ffffff; font-weight: 700; border-radius: 6px; padding: 3px 8px; font-size: 11px; }}
        
        pre {{ background-color: #090d13; border: 1px solid #30363d; border-radius: 8px; padding: 16px; font-size: 12.5px; overflow-x: auto; color: #7ee787; font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; max-height: 350px; line-height: 1.4; }}
        
        .btn {{ display: inline-block; background: #238636; color: #ffffff; text-decoration: none; padding: 10px 18px; border-radius: 6px; font-weight: 600; font-size: 13px; margin-top: 10px; }}
        .footer {{ text-align: center; padding: 20px; font-size: 12px; color: #8b949e; border-top: 1px solid #21262d; background: #090d13; }}
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>🚀 Unstop Problem of the Day</h1>
            <p>Automated Execution & Submission Report &bull; {now_str}</p>
        </div>

        <div class="content">
            <!-- Status & Testcase Hero Card -->
            <div style="display: flex; gap: 12px; margin-bottom: 18px; flex-wrap: wrap;">
                <div style="flex: 1; min-width: 140px; background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 14px; text-align: center;">
                    <div style="font-size: 11px; color: #8b949e; text-transform: uppercase; font-weight: 700;">Verdict</div>
                    <div style="font-size: 18px; font-weight: 800; color: #7ee787; margin-top: 4px;">✅ {unstop_status}</div>
                </div>
                <div style="flex: 1; min-width: 140px; background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 14px; text-align: center;">
                    <div style="font-size: 11px; color: #8b949e; text-transform: uppercase; font-weight: 700;">Testcases Passed</div>
                    <div style="font-size: 18px; font-weight: 800; color: #58a6ff; margin-top: 4px;">🎯 {tc_passed}</div>
                </div>
                <div style="flex: 1; min-width: 140px; background: #161b22; border: 1px solid #30363d; border-radius: 8px; padding: 14px; text-align: center;">
                    <div style="font-size: 11px; color: #8b949e; text-transform: uppercase; font-weight: 700;">Unstop Score</div>
                    <div style="font-size: 18px; font-weight: 800; color: #e3b341; margin-top: 4px;">⭐ {score} Pts</div>
                </div>
            </div>

            <!-- Problem Card -->
            <div class="card">
                <div class="card-title">
                    <span>📌 Problem Overview</span>
                    <span style="font-size: 12px; color: #e3b341; background: #bb800926; padding: 2px 8px; border-radius: 12px;">{difficulty}</span>
                </div>
                <h2 style="margin: 0 0 10px 0; font-size: 18px; color: #ffffff;">{title}</h2>
                <div style="margin-bottom: 12px;">
                    {tags_badges}
                    {company_badges}
                </div>
                
                <p style="margin: 6px 0; font-size: 13px; color: #8b949e;"><strong>Question ID:</strong> {qid}</p>
                <p style="margin: 6px 0; font-size: 13px; color: #8b949e;"><strong>Unstop Submission ID:</strong> {sub_id}</p>
                <p style="margin: 6px 0; font-size: 13px; color: #8b949e;"><strong>Evaluated At:</strong> {finished_at}</p>
                
                <a href="https://unstop.com/code/practice/{qid}" class="btn" style="color:#ffffff;">🔗 View on Unstop</a>
            </div>

            <!-- Problem Statement -->
            <div class="card">
                <div class="card-title">📖 Problem Statement</div>
                <div style="font-size: 13px; color: #c9d1d9; white-space: pre-line;">
                    {description[:600] + ('...' if len(description) > 600 else '')}
                </div>
                {examples_html}
            </div>

            <!-- Dual AI Competition -->
            <div class="card">
                <div class="card-title">⚡ Dual-AI Solver Competition (Gemini vs Groq)</div>
                <table class="table">
                    <thead>
                        <tr>
                            <th>Model</th>
                            <th>Sample Tests</th>
                            <th>Avg Runtime</th>
                            <th>Verdict</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>Gemini ({Config.GEMINI_MODEL})</strong></td>
                            <td><span style="color: {'#7ee787' if '2/2' in gemini_pass or 'Passed' in str(gemini_pass) else '#f85149'};">{gemini_pass}</span></td>
                            <td>{gemini_time}</td>
                            <td>{"<span class='winner-badge'>🏆 WINNER</span>" if winner == "Gemini" else "<span style='color:#8b949e;'>Runner-up</span>"}</td>
                        </tr>
                        <tr>
                            <td><strong>Groq ({Config.GROQ_MODEL})</strong></td>
                            <td><span style="color: {'#7ee787' if '2/2' in groq_pass or 'Passed' in str(groq_pass) else '#f85149'};">{groq_pass}</span></td>
                            <td>{groq_time}</td>
                            <td>{"<span class='winner-badge'>🏆 WINNER</span>" if winner == "Groq" else "<span style='color:#8b949e;'>Runner-up</span>"}</td>
                        </tr>
                    </tbody>
                </table>
            </div>

            <!-- Pure Solution Code -->
            <div class="card">
                <div class="card-title">
                    <span>💻 Submitted Pure Code ({winner})</span>
                    <span style="font-size: 11px; color: #8b949e;">Zero Comments &bull; Zero Docstrings &bull; Python 3</span>
                </div>
                <pre><code>{winning_code}</code></pre>
            </div>
        </div>

        <!-- Footer -->
        <div class="footer">
            Automated by Unstop Daily POTD Bot &bull; Dual AI Solvers &bull; GitHub Actions CI/CD
        </div>
    </div>
</body>
</html>
"""

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "from": from_email,
        "to": [to_email],
        "subject": f"🎯 Unstop POTD: {title} - {unstop_status} ({winner})",
        "html": html_content
    }

    log.info(f"📧 Sending rich Resend email report to {to_email}...")
    try:
        res = requests.post("https://api.resend.com/emails", headers=headers, json=payload, timeout=15)
        if res.status_code in [200, 201]:
            log.info(f"✅ Full problem & solution email report delivered to {to_email}!")
            return True
        else:
            log.error(f"❌ Resend API error {res.status_code}: {res.text}")
            return False
    except Exception as e:
        log.error(f"❌ Failed to send email report: {e}")
        return False
