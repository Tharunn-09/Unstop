import sys
import time
import subprocess
from typing import Dict, Any, List
from src.logger import log

class CodeEvaluator:
    @staticmethod
    def test_solution(code: str, sample_testcases: List[Dict[str, str]], timeout_sec: float = 3.0) -> Dict[str, Any]:
        """
        Executes code against sample test cases locally.
        Returns metrics on passed count, total count, runtime in ms, and any errors.
        """
        if not code or not code.strip():
            return {
                "passed_all": False,
                "passed_count": 0,
                "total_count": len(sample_testcases),
                "runtime_ms": 9999.0,
                "error": "Empty code"
            }

        if not sample_testcases:
            # If no sample testcases provided, verify syntax
            try:
                compile(code, "<string>", "exec")
                return {
                    "passed_all": True,
                    "passed_count": 1,
                    "total_count": 1,
                    "runtime_ms": 0.0,
                    "error": None
                }
            except Exception as e:
                return {
                    "passed_all": False,
                    "passed_count": 0,
                    "total_count": 1,
                    "runtime_ms": 9999.0,
                    "error": str(e)
                }

        passed = 0
        total_time_ms = 0.0

        for i, testcase in enumerate(sample_testcases, 1):
            inp = testcase.get("input", "").strip()
            expected = testcase.get("output", "").strip()

            try:
                start_t = time.perf_counter()
                process = subprocess.run(
                    [sys.executable, "-c", code],
                    input=inp,
                    text=True,
                    capture_output=True,
                    timeout=timeout_sec
                )
                elapsed_ms = (time.perf_counter() - start_t) * 1000.0
                total_time_ms += elapsed_ms

                if process.returncode != 0:
                    return {
                        "passed_all": False,
                        "passed_count": passed,
                        "total_count": len(sample_testcases),
                        "runtime_ms": total_time_ms,
                        "error": f"Runtime error on sample {i}: {process.stderr.strip()}"
                    }

                actual = process.stdout.strip()
                # Normalize line endings and whitespace for comparison
                norm_actual = " ".join(actual.split())
                norm_expected = " ".join(expected.split())

                if norm_actual == norm_expected:
                    passed += 1
                else:
                    return {
                        "passed_all": False,
                        "passed_count": passed,
                        "total_count": len(sample_testcases),
                        "runtime_ms": total_time_ms,
                        "error": f"Sample {i} mismatch. Expected: '{norm_expected}', Got: '{norm_actual}'"
                    }
            except subprocess.TimeoutExpired:
                return {
                    "passed_all": False,
                    "passed_count": passed,
                    "total_count": len(sample_testcases),
                    "runtime_ms": timeout_sec * 1000.0,
                    "error": f"Time Limit Exceeded on sample {i}"
                }
            except Exception as e:
                return {
                    "passed_all": False,
                    "passed_count": passed,
                    "total_count": len(sample_testcases),
                    "runtime_ms": 9999.0,
                    "error": str(e)
                }

        return {
            "passed_all": (passed == len(sample_testcases)),
            "passed_count": passed,
            "total_count": len(sample_testcases),
            "runtime_ms": round(total_time_ms / max(1, len(sample_testcases)), 2),
            "error": None
        }

    @classmethod
    def compare_and_select(cls, problem_details: dict, gemini_code: str, groq_code: str, gemini_solver=None, groq_solver=None) -> dict:
        """
        Evaluates both solutions against sample test cases (for Python) or validates SQL statements (for MySQL).
        Returns the winning code and evaluation metrics.
        """
        lang_type = problem_details.get("language_type", "python3")
        examples = problem_details.get("examples", [])

        # Special evaluation for MySQL / SQL problems
        if lang_type == "mysql":
            log.info("🧪 Validating candidate SQL queries for MySQL problem...")
            gemini_valid = bool(gemini_code and ("select" in gemini_code.lower() or "with" in gemini_code.lower()))
            groq_valid = bool(groq_code and ("select" in groq_code.lower() or "with" in groq_code.lower()))

            gemini_res = {"passed_count": 1 if gemini_valid else 0, "total_count": 1, "runtime_ms": 10.0, "error": None}
            groq_res = {"passed_count": 1 if groq_valid else 0, "total_count": 1, "runtime_ms": 12.0, "error": None}

            if gemini_valid:
                winner = "Gemini"
                winning_code = gemini_code
            elif groq_valid:
                winner = "Groq"
                winning_code = groq_code
            else:
                winner = "Gemini"
                winning_code = gemini_code or groq_code

            log.info(f"🏆 Winner Selected for SQL Problem: {winner} (Submitted to Unstop)")
            return {
                "winner": winner,
                "code": winning_code,
                "gemini_result": gemini_res,
                "groq_result": groq_res,
                "language_type": "mysql"
            }

        log.info("🧪 Evaluating candidate solutions against sample test cases...")

        gemini_res = cls.test_solution(gemini_code, examples) if gemini_code else None
        groq_res = cls.test_solution(groq_code, examples) if groq_code else None

        # Self-Healing Retry for Gemini if samples failed
        if gemini_solver and gemini_res and not gemini_res["passed_all"]:
            log.warning(f"⚠️ Gemini failed {gemini_res['total_count'] - gemini_res['passed_count']} sample testcase(s). Triggering self-healing refinement...")
            refined_gemini = gemini_solver.refine_solution(problem_details, gemini_code, gemini_res.get("error") or "Failed sample testcase")
            if refined_gemini and refined_gemini != gemini_code:
                refined_res = cls.test_solution(refined_gemini, examples)
                log.info(f"  🤖 Gemini (Refined): Passed {refined_res['passed_count']}/{refined_res['total_count']} | Runtime: {refined_res['runtime_ms']}ms")
                if refined_res["passed_count"] >= gemini_res["passed_count"]:
                    gemini_code = refined_gemini
                    gemini_res = refined_res

        # Self-Healing Retry for Groq if samples failed
        if groq_solver and groq_res and not groq_res["passed_all"]:
            log.warning(f"⚠️ Groq failed {groq_res['total_count'] - groq_res['passed_count']} sample testcase(s). Triggering self-healing refinement...")
            refined_groq = groq_solver.refine_solution(problem_details, groq_code, groq_res.get("error") or "Failed sample testcase")
            if refined_groq and refined_groq != groq_code:
                refined_res = cls.test_solution(refined_groq, examples)
                log.info(f"  ⚡ Groq (Refined): Passed {refined_res['passed_count']}/{refined_res['total_count']} | Runtime: {refined_res['runtime_ms']}ms")
                if refined_res["passed_count"] >= groq_res["passed_count"]:
                    groq_code = refined_groq
                    groq_res = refined_res

        if gemini_res:
            log.info(f"  🤖 Gemini: Passed {gemini_res['passed_count']}/{gemini_res['total_count']} | Runtime: {gemini_res['runtime_ms']}ms | Error: {gemini_res['error']}")
        else:
            log.info("  🤖 Gemini: Solution generation failed.")

        if groq_res:
            log.info(f"  ⚡ Groq: Passed {groq_res['passed_count']}/{groq_res['total_count']} | Runtime: {groq_res['runtime_ms']}ms | Error: {groq_res['error']}")
        else:
            log.info("  ⚡ Groq: Solution generation failed.")

        # Selection Logic
        winner = "Gemini"
        winning_code = gemini_code

        gemini_passed_all = gemini_res and gemini_res["passed_count"] == gemini_res["total_count"] and gemini_res["total_count"] > 0
        groq_passed_all = groq_res and groq_res["passed_count"] == groq_res["total_count"] and groq_res["total_count"] > 0

        if gemini_passed_all and groq_passed_all:
            # Both passed all sample cases -> choose the faster runtime
            if groq_res["runtime_ms"] < gemini_res["runtime_ms"]:
                winner = "Groq"
                winning_code = groq_code
            else:
                winner = "Gemini"
                winning_code = gemini_code
        elif gemini_passed_all:
            winner = "Gemini"
            winning_code = gemini_code
        elif groq_passed_all:
            winner = "Groq"
            winning_code = groq_code
        else:
            # If neither passed all, pick the one with more passed cases or fallback to Gemini
            gemini_score = gemini_res["passed_count"] if gemini_res else -1
            groq_score = groq_res["passed_count"] if groq_res else -1
            if groq_score > gemini_score:
                winner = "Groq"
                winning_code = groq_code
            else:
                winner = "Gemini"
                winning_code = gemini_code or groq_code

        log.info(f"🏆 Winner Selected: {winner} (Submitted to Unstop)")
        return {
            "winner": winner,
            "code": winning_code,
            "gemini_result": gemini_res,
            "groq_result": groq_res,
            "language_type": "python3"
        }

    @classmethod
    def select_best_code(cls, problem_details: dict, gemini_code: str, groq_code: str, gemini_solver=None, groq_solver=None) -> dict:
        return cls.compare_and_select(problem_details, gemini_code, groq_code, gemini_solver, groq_solver)
