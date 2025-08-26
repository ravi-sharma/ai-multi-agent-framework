"""Comprehensive test runner for the AI agent framework."""

import os
import sys
import subprocess
import argparse
import json
from datetime import datetime
from pathlib import Path


class ComprehensiveTestRunner:
    """Runner for comprehensive testing including coverage and reporting."""
    
    def __init__(self, project_root: str = None):
        """Initialize test runner.
        
        Args:
            project_root: Path to project root directory
        """
        self.project_root = Path(project_root) if project_root else Path(__file__).parent.parent
        self.test_results = {}
        self.coverage_threshold = 80
    
    def run_unit_tests(self, verbose: bool = True) -> dict:
        """Run unit tests with coverage.
        
        Args:
            verbose: Whether to run in verbose mode
            
        Returns:
            Test results dictionary
        """
        print("🧪 Running unit tests...")
        
        cmd = [
            "python", "-m", "pytest",
            "tests/",
            "--cov=ai_agent_framework",
            "--cov-report=html:htmlcov",
            "--cov-report=term-missing",
            "--cov-report=xml",
            f"--cov-fail-under={self.coverage_threshold}",
            "-m", "unit",
            "--tb=short"
        ]
        
        if verbose:
            cmd.append("-v")
        
        result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
        
        self.test_results["unit_tests"] = {
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0
        }
        
        if result.returncode == 0:
            print("✅ Unit tests passed")
        else:
            print("❌ Unit tests failed")
            print(result.stdout)
            print(result.stderr)
        
        return self.test_results["unit_tests"]
    
    def run_integration_tests(self, verbose: bool = True) -> dict:
        """Run integration tests.
        
        Args:
            verbose: Whether to run in verbose mode
            
        Returns:
            Test results dictionary
        """
        print("🔗 Running integration tests...")
        
        cmd = [
            "python", "-m", "pytest",
            "tests/integration/",
            "-m", "integration",
            "--tb=short"
        ]
        
        if verbose:
            cmd.append("-v")
        
        result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
        
        self.test_results["integration_tests"] = {
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0
        }
        
        if result.returncode == 0:
            print("✅ Integration tests passed")
        else:
            print("❌ Integration tests failed")
            print(result.stdout)
            print(result.stderr)
        
        return self.test_results["integration_tests"]
    
    def run_performance_tests(self, verbose: bool = True) -> dict:
        """Run performance tests.
        
        Args:
            verbose: Whether to run in verbose mode
            
        Returns:
            Test results dictionary
        """
        print("⚡ Running performance tests...")
        
        cmd = [
            "python", "-m", "pytest",
            "tests/performance/",
            "-m", "performance",
            "--run-performance",
            "--tb=short"
        ]
        
        if verbose:
            cmd.append("-v")
        
        result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
        
        self.test_results["performance_tests"] = {
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0
        }
        
        if result.returncode == 0:
            print("✅ Performance tests passed")
        else:
            print("⚠️ Performance tests completed with issues")
            print(result.stdout)
            print(result.stderr)
        
        return self.test_results["performance_tests"]
    
    def check_coverage(self) -> dict:
        """Check test coverage and generate reports.
        
        Returns:
            Coverage results dictionary
        """
        print("📊 Checking test coverage...")
        
        coverage_file = self.project_root / "coverage.xml"
        if not coverage_file.exists():
            print("⚠️ Coverage file not found. Run unit tests first.")
            return {"success": False, "message": "Coverage file not found"}
        
        # Parse coverage from XML file
        try:
            import xml.etree.ElementTree as ET
            tree = ET.parse(coverage_file)
            root = tree.getroot()
            
            coverage_percent = float(root.attrib.get('line-rate', 0)) * 100
            
            coverage_result = {
                "success": coverage_percent >= self.coverage_threshold,
                "coverage_percent": coverage_percent,
                "threshold": self.coverage_threshold,
                "html_report": str(self.project_root / "htmlcov" / "index.html")
            }
            
            if coverage_result["success"]:
                print(f"✅ Coverage: {coverage_percent:.1f}% (threshold: {self.coverage_threshold}%)")
            else:
                print(f"❌ Coverage: {coverage_percent:.1f}% (below threshold: {self.coverage_threshold}%)")
            
            self.test_results["coverage"] = coverage_result
            return coverage_result
            
        except Exception as e:
            print(f"⚠️ Error parsing coverage: {e}")
            return {"success": False, "error": str(e)}
    
    def run_linting(self) -> dict:
        """Run code linting checks.
        
        Returns:
            Linting results dictionary
        """
        print("🔍 Running code linting...")
        
        linting_results = {}
        
        # Run flake8
        print("  Running flake8...")
        flake8_result = subprocess.run(
            ["python", "-m", "flake8", "ai_agent_framework/", "--max-line-length=100"],
            cwd=self.project_root,
            capture_output=True,
            text=True
        )
        
        linting_results["flake8"] = {
            "return_code": flake8_result.returncode,
            "stdout": flake8_result.stdout,
            "stderr": flake8_result.stderr,
            "success": flake8_result.returncode == 0
        }
        
        # Run black check
        print("  Running black check...")
        black_result = subprocess.run(
            ["python", "-m", "black", "--check", "ai_agent_framework/"],
            cwd=self.project_root,
            capture_output=True,
            text=True
        )
        
        linting_results["black"] = {
            "return_code": black_result.returncode,
            "stdout": black_result.stdout,
            "stderr": black_result.stderr,
            "success": black_result.returncode == 0
        }
        
        # Run isort check
        print("  Running isort check...")
        isort_result = subprocess.run(
            ["python", "-m", "isort", "--check-only", "ai_agent_framework/"],
            cwd=self.project_root,
            capture_output=True,
            text=True
        )
        
        linting_results["isort"] = {
            "return_code": isort_result.returncode,
            "stdout": isort_result.stdout,
            "stderr": isort_result.stderr,
            "success": isort_result.returncode == 0
        }
        
        all_passed = all(result["success"] for result in linting_results.values())
        
        if all_passed:
            print("✅ All linting checks passed")
        else:
            print("❌ Some linting checks failed")
            for tool, result in linting_results.items():
                if not result["success"]:
                    print(f"  {tool}: {result['stdout']}")
        
        self.test_results["linting"] = linting_results
        return linting_results
    
    def run_type_checking(self) -> dict:
        """Run type checking with mypy.
        
        Returns:
            Type checking results dictionary
        """
        print("🔎 Running type checking...")
        
        cmd = [
            "python", "-m", "mypy",
            "ai_agent_framework/",
            "--ignore-missing-imports",
            "--no-strict-optional"
        ]
        
        result = subprocess.run(cmd, cwd=self.project_root, capture_output=True, text=True)
        
        type_check_result = {
            "return_code": result.returncode,
            "stdout": result.stdout,
            "stderr": result.stderr,
            "success": result.returncode == 0
        }
        
        if type_check_result["success"]:
            print("✅ Type checking passed")
        else:
            print("⚠️ Type checking found issues")
            print(result.stdout)
        
        self.test_results["type_checking"] = type_check_result
        return type_check_result
    
    def generate_test_report(self) -> str:
        """Generate comprehensive test report.
        
        Returns:
            Path to generated report file
        """
        print("📋 Generating test report...")
        
        report_data = {
            "timestamp": datetime.now().isoformat(),
            "project": "AI Agent Framework",
            "test_results": self.test_results,
            "summary": self._generate_summary()
        }
        
        report_file = self.project_root / "test_report.json"
        with open(report_file, 'w') as f:
            json.dump(report_data, f, indent=2)
        
        # Generate HTML report
        html_report = self._generate_html_report(report_data)
        html_file = self.project_root / "test_report.html"
        with open(html_file, 'w') as f:
            f.write(html_report)
        
        print(f"📄 Test report generated: {html_file}")
        return str(html_file)
    
    def _generate_summary(self) -> dict:
        """Generate test summary.
        
        Returns:
            Summary dictionary
        """
        summary = {
            "total_test_suites": len(self.test_results),
            "passed_suites": 0,
            "failed_suites": 0,
            "overall_success": True
        }
        
        for suite_name, suite_result in self.test_results.items():
            if isinstance(suite_result, dict) and suite_result.get("success", False):
                summary["passed_suites"] += 1
            else:
                summary["failed_suites"] += 1
                summary["overall_success"] = False
        
        return summary
    
    def _generate_html_report(self, report_data: dict) -> str:
        """Generate HTML test report.
        
        Args:
            report_data: Report data dictionary
            
        Returns:
            HTML report string
        """
        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>AI Agent Framework - Test Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
        .summary {{ margin: 20px 0; }}
        .test-suite {{ margin: 20px 0; border: 1px solid #ddd; border-radius: 5px; }}
        .suite-header {{ background-color: #f8f9fa; padding: 10px; font-weight: bold; }}
        .suite-content {{ padding: 10px; }}
        .success {{ color: green; }}
        .failure {{ color: red; }}
        .warning {{ color: orange; }}
        pre {{ background-color: #f5f5f5; padding: 10px; border-radius: 3px; overflow-x: auto; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>AI Agent Framework - Test Report</h1>
        <p>Generated: {report_data['timestamp']}</p>
    </div>
    
    <div class="summary">
        <h2>Summary</h2>
        <p>Total Test Suites: {report_data['summary']['total_test_suites']}</p>
        <p>Passed: <span class="success">{report_data['summary']['passed_suites']}</span></p>
        <p>Failed: <span class="failure">{report_data['summary']['failed_suites']}</span></p>
        <p>Overall Status: <span class="{'success' if report_data['summary']['overall_success'] else 'failure'}">
            {'PASSED' if report_data['summary']['overall_success'] else 'FAILED'}
        </span></p>
    </div>
    
    <div class="test-results">
        <h2>Test Results</h2>
"""
        
        for suite_name, suite_result in report_data['test_results'].items():
            status_class = "success" if suite_result.get("success", False) else "failure"
            status_text = "PASSED" if suite_result.get("success", False) else "FAILED"
            
            html += f"""
        <div class="test-suite">
            <div class="suite-header">
                {suite_name.replace('_', ' ').title()} - <span class="{status_class}">{status_text}</span>
            </div>
            <div class="suite-content">
"""
            
            if isinstance(suite_result, dict):
                if "stdout" in suite_result and suite_result["stdout"]:
                    html += f"<h4>Output:</h4><pre>{suite_result['stdout']}</pre>"
                if "stderr" in suite_result and suite_result["stderr"]:
                    html += f"<h4>Errors:</h4><pre>{suite_result['stderr']}</pre>"
            
            html += """
            </div>
        </div>
"""
        
        html += """
    </div>
</body>
</html>
"""
        return html
    
    def run_all_tests(self, include_performance: bool = False, verbose: bool = True) -> dict:
        """Run all test suites.
        
        Args:
            include_performance: Whether to include performance tests
            verbose: Whether to run in verbose mode
            
        Returns:
            Complete test results dictionary
        """
        print("🚀 Running comprehensive test suite...")
        print("=" * 60)
        
        # Run linting first
        self.run_linting()
        
        # Run type checking
        self.run_type_checking()
        
        # Run unit tests with coverage
        self.run_unit_tests(verbose)
        
        # Check coverage
        self.check_coverage()
        
        # Run integration tests
        self.run_integration_tests(verbose)
        
        # Run performance tests if requested
        if include_performance:
            self.run_performance_tests(verbose)
        
        # Generate report
        report_file = self.generate_test_report()
        
        # Print summary
        self._print_final_summary()
        
        return self.test_results
    
    def _print_final_summary(self):
        """Print final test summary."""
        print("\n" + "=" * 60)
        print("📊 FINAL TEST SUMMARY")
        print("=" * 60)
        
        summary = self._generate_summary()
        
        print(f"Total Test Suites: {summary['total_test_suites']}")
        print(f"Passed: {summary['passed_suites']}")
        print(f"Failed: {summary['failed_suites']}")
        
        if summary['overall_success']:
            print("\n🎉 ALL TESTS PASSED!")
        else:
            print("\n❌ SOME TESTS FAILED")
            print("\nFailed suites:")
            for suite_name, suite_result in self.test_results.items():
                if not suite_result.get("success", False):
                    print(f"  - {suite_name}")
        
        print("=" * 60)


def main():
    """Main entry point for test runner."""
    parser = argparse.ArgumentParser(description="Comprehensive test runner for AI Agent Framework")
    parser.add_argument("--performance", action="store_true", help="Include performance tests")
    parser.add_argument("--unit-only", action="store_true", help="Run only unit tests")
    parser.add_argument("--integration-only", action="store_true", help="Run only integration tests")
    parser.add_argument("--performance-only", action="store_true", help="Run only performance tests")
    parser.add_argument("--no-coverage", action="store_true", help="Skip coverage checking")
    parser.add_argument("--quiet", action="store_true", help="Run in quiet mode")
    parser.add_argument("--coverage-threshold", type=int, default=80, help="Coverage threshold percentage")
    
    args = parser.parse_args()
    
    runner = ComprehensiveTestRunner()
    runner.coverage_threshold = args.coverage_threshold
    
    verbose = not args.quiet
    
    try:
        if args.unit_only:
            runner.run_unit_tests(verbose)
            if not args.no_coverage:
                runner.check_coverage()
        elif args.integration_only:
            runner.run_integration_tests(verbose)
        elif args.performance_only:
            runner.run_performance_tests(verbose)
        else:
            runner.run_all_tests(include_performance=args.performance, verbose=verbose)
        
        # Generate report
        runner.generate_test_report()
        
    except KeyboardInterrupt:
        print("\n⚠️ Test run interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test run failed with error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()