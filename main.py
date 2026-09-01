import sys
from src.config import Config
from src.logger import log
from src.solver import CodingSolver
from src.groq_solver import GroqSolver
from src.evaluator import CodeEvaluator
from src.unstop_client import UnstopClient
from src.notifier import send_email_report

def main():
    log.info("=" * 60)
    log.info("🤖 Starting Unstop Problem of the Day (POTD) Automation Bot")
    log.info("=" * 60)

    # 1. Parse Command-Line Arguments
    import argparse
    parser = argparse.ArgumentParser(description="Unstop Problem of the Day Automation Bot")
    parser.add_argument("question", nargs="?", default=None, help="Optional Question ID, URL, or 'potd'")
    parser.add_argument("--dry-run", action="store_true", help="Run without submitting to Unstop")
    args = parser.parse_args()

    if args.dry_run:
        Config.RUN_MODE = "dry-run"
        log.info("🧪 CLI Flag: RUN_MODE set to 'dry-run'")

    target_q = args.question
    if target_q and target_q.lower() not in ["potd", "auto", "daily"]:
        log.info(f"🎯 Targeted Question from CLI: {target_q}")

    # 2. Check Configuration & Credentials
    if not Config.validate():
        if Config.RUN_MODE != "dry-run":
            log.error("⚠️ Credentials validation failed. Switch to RUN_MODE='dry-run' in .env or provide your keys.")
            sys.exit(1)

    # 3. Initialize Clients & Solvers
    client = UnstopClient()
    gemini_solver = CodingSolver()
    groq_solver = GroqSolver()

    # 4. Fetch Problem of the Day / Target Practice Question
    try:
        problem_details = client.fetch_potd_details(target_q)
    except Exception as e:
        log.error(f"❌ Failed to fetch problem: {e}")
        sys.exit(1)

    title = problem_details.get("title", "Unknown Problem")
    qid = problem_details.get("problem_id", "")
    log.info(f"📌 Problem Identified: '{title}' (ID: {qid})")

    # 4. Generate Solutions from Dual AI Solvers (Gemini & Groq)
    gemini_code = ""
    groq_code = ""

    try:
        gemini_code = gemini_solver.generate_solution(problem_details)
    except Exception as e:
        log.error(f"❌ Gemini solver error: {e}")

    try:
        if Config.GROQ_API_KEY:
            groq_code = groq_solver.generate_solution(problem_details)
    except Exception as e:
        log.error(f"❌ Groq solver error: {e}")

    if not gemini_code and not groq_code:
        log.error("❌ Both AI solvers failed to generate a solution. Aborting.")
        sys.exit(1)

    # 5. Evaluate & Compare Solutions (with automated sample testcase self-healing)
    comparison = CodeEvaluator.select_best_code(
        problem_details,
        gemini_code,
        groq_code,
        gemini_solver=gemini_solver,
        groq_solver=groq_solver
    )
    winning_code = comparison.get("code", "")
    winner_name = comparison.get("winner", "Gemini")
    lang_type = problem_details.get("language_type", "python3").upper()

    log.info("-" * 50)
    log.info(f"📝 Pure {lang_type} Solution ({winner_name}) - Zero Comments/Docstrings:")
    log.info("-" * 50)
    print(winning_code)
    log.info("-" * 50)

    # 6. Submit Best Solution to Unstop
    submission_result = client.submit_solution(problem_details, winning_code)

    # 7. Automated Self-Healing Resubmission if Unstop Testcases Failed
    max_retries = 2
    retry_count = 0
    while (
        Config.RUN_MODE != "dry-run"
        and retry_count < max_retries
        and submission_result.get("status") == "FAILED"
    ):
        retry_count += 1
        tc_info = submission_result.get("testcase_passed", "Partial/Failed")
        log.warning(f"⚠️ Unstop testcase verdict: {tc_info} (Attempt {retry_count}/{max_retries}). Initiating Dual-AI Self-Healing...")

        feedback = f"Unstop evaluation failed on hidden testcases. Verdict: {tc_info}. Re-examine constraints, edge cases, types, and logic."
        refined_gemini = gemini_solver.refine_solution(problem_details, winning_code, feedback)
        refined_groq = groq_solver.refine_solution(problem_details, winning_code, feedback) if Config.GROQ_API_KEY else ""

        comparison = CodeEvaluator.select_best_code(
            problem_details,
            refined_gemini,
            refined_groq,
            gemini_solver=gemini_solver,
            groq_solver=groq_solver
        )
        winning_code = comparison.get("code", "")
        winner_name = comparison.get("winner", "Gemini")

        log.info(f"🚀 Resubmitting refined {winner_name} solution to Unstop...")
        submission_result = client.submit_solution(problem_details, winning_code)
        if submission_result.get("status") == "ACCEPTED":
            log.info(f"🎉 Self-Healing Successful! All Unstop testcases passed on attempt {retry_count + 1}!")
            break

    # 8. Send Resend Email Report
    try:
        send_email_report(problem_details, submission_result, comparison)
    except Exception as email_err:
        log.error(f"❌ Email sending error: {email_err}")

    # 9. Final Summary
    log.info("=" * 60)
    if submission_result.get("success"):
        status = submission_result.get("status", "ACCEPTED")
        tc_passed = submission_result.get("testcase_passed", "Passed")
        log.info(f"🎉 Bot Execution Completed! Status: {status} | Testcases: {tc_passed} | Model: {winner_name}")
    else:
        log.warning(f"⚠️ Bot finished with status: {submission_result.get('status')}")
    log.info("=" * 60)

if __name__ == "__main__":
    main()
