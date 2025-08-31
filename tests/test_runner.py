"""
Automated test runner and reporting utilities for the banking platform.
Provides comprehensive test execution, coverage reporting, and performance metrics.
"""

import os
import sys
import time
import json
import subprocess
from datetime import datetime
from django.test.runner import DiscoverRunner
from django.test import TestCase
from django.conf import settings
from django.core.management import call_command
from django.db import connection
from io import StringIO


class BankingPlatformTestRunner(DiscoverRunner):
    """Custom test runner with enhanced reporting and metrics."""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.start_time = None
        self.test_results = {}
        self.performance_metrics = {}
        self.coverage_data = {}
    
    def setup_test_environment(self, **kwargs):
        """Set up test environment with performance monitoring."""
        self.start_time = time.time()
        super().setup_test_environment(**kwargs)
        
        # Clear any existing test data
        self._clear_test_cache()
        
        print("Banking Platform Test Suite Starting...")
        print(f"Django Version: {settings.DJANGO_VERSION if hasattr(settings, 'DJANGO_VERSION') else 'Unknown'}")
        print(f"Database: {settings.DATABASES['default']['ENGINE']}")
        print("-" * 60)
    
    def teardown_test_environment(self, **kwargs):
        """Clean up test environment and generate reports."""
        super().teardown_test_environment(**kwargs)
        
        end_time = time.time()
        total_time = end_time - self.start_time
        
        # Generate comprehensive test report
        self._generate_test_report(total_time)
        
        # Clean up
        self._clear_test_cache()
    
    def _clear_test_cache(self):
        """Clear test-related cache and temporary data."""
        from django.core.cache import cache
        cache.clear()
    
    def _generate_test_report(self, total_time):
        """Generate comprehensive test report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_execution_time': total_time,
            'database_queries': len(connection.queries),
            'test_results': self.test_results,
            'performance_metrics': self.performance_metrics,
            'coverage_data': self.coverage_data
        }
        
        # Save report to file
        report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        # Print summary
        print("\n" + "=" * 60)
        print("BANKING PLATFORM TEST REPORT")
        print("=" * 60)
        print(f"Total Execution Time: {total_time:.2f} seconds")
        print(f"Database Queries: {len(connection.queries)}")
        print(f"Report saved to: {report_file}")
        print("=" * 60)


class TestSuiteManager:
    """Manages test suite execution and reporting."""
    
    def __init__(self):
        self.test_categories = {
            'unit': [
                'accounts.tests',
                'transactions.tests',
                'admin_panel.tests',
                'core.tests'
            ],
            'integration': [
                'tests.test_integration_workflows'
            ],
            'performance': [
                'tests.test_performance'
            ],
            'security': [
                'core.tests.test_security',
                'tests.test_security_comprehensive'
            ]
        }
    
    def run_all_tests(self):
        """Run all test categories."""
        print("Running complete test suite...")
        
        results = {}
        total_start_time = time.time()
        
        for category, test_modules in self.test_categories.items():
            print(f"\n{'='*20} {category.upper()} TESTS {'='*20}")
            category_start_time = time.time()
            
            category_results = self._run_test_category(category, test_modules)
            category_end_time = time.time()
            
            results[category] = {
                'results': category_results,
                'execution_time': category_end_time - category_start_time
            }
        
        total_end_time = time.time()
        
        # Generate summary report
        self._generate_summary_report(results, total_end_time - total_start_time)
        
        return results
    
    def run_category(self, category):
        """Run tests for a specific category."""
        if category not in self.test_categories:
            raise ValueError(f"Unknown test category: {category}")
        
        print(f"Running {category} tests...")
        return self._run_test_category(category, self.test_categories[category])
    
    def _run_test_category(self, category, test_modules):
        """Run tests for a specific category."""
        results = {}
        
        for module in test_modules:
            print(f"  Running {module}...")
            module_start_time = time.time()
            
            try:
                # Capture test output
                output = StringIO()
                call_command('test', module, verbosity=2, stdout=output)
                
                module_end_time = time.time()
                
                results[module] = {
                    'status': 'passed',
                    'execution_time': module_end_time - module_start_time,
                    'output': output.getvalue()
                }
                
                print(f"    ✓ {module} passed ({module_end_time - module_start_time:.2f}s)")
                
            except Exception as e:
                module_end_time = time.time()
                
                results[module] = {
                    'status': 'failed',
                    'execution_time': module_end_time - module_start_time,
                    'error': str(e)
                }
                
                print(f"    ✗ {module} failed ({module_end_time - module_start_time:.2f}s)")
                print(f"      Error: {str(e)}")
        
        return results
    
    def _generate_summary_report(self, results, total_time):
        """Generate summary report for all test categories."""
        print("\n" + "="*60)
        print("TEST SUITE SUMMARY REPORT")
        print("="*60)
        
        total_tests = 0
        passed_tests = 0
        failed_tests = 0
        
        for category, category_data in results.items():
            category_results = category_data['results']
            category_time = category_data['execution_time']
            
            category_passed = sum(1 for r in category_results.values() if r['status'] == 'passed')
            category_failed = sum(1 for r in category_results.values() if r['status'] == 'failed')
            category_total = len(category_results)
            
            total_tests += category_total
            passed_tests += category_passed
            failed_tests += category_failed
            
            print(f"\n{category.upper()} TESTS:")
            print(f"  Total: {category_total}")
            print(f"  Passed: {category_passed}")
            print(f"  Failed: {category_failed}")
            print(f"  Time: {category_time:.2f}s")
            
            if category_failed > 0:
                print("  Failed modules:")
                for module, result in category_results.items():
                    if result['status'] == 'failed':
                        print(f"    - {module}: {result.get('error', 'Unknown error')}")
        
        print(f"\nOVERALL RESULTS:")
        print(f"  Total Tests: {total_tests}")
        print(f"  Passed: {passed_tests}")
        print(f"  Failed: {failed_tests}")
        print(f"  Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        print(f"  Total Time: {total_time:.2f}s")
        
        # Save detailed report
        report_file = f"test_summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'total_time': total_time,
                'summary': {
                    'total_tests': total_tests,
                    'passed_tests': passed_tests,
                    'failed_tests': failed_tests,
                    'success_rate': (passed_tests/total_tests)*100
                },
                'detailed_results': results
            }, f, indent=2)
        
        print(f"\nDetailed report saved to: {report_file}")
        print("="*60)


class CoverageReporter:
    """Generates test coverage reports."""
    
    def __init__(self):
        self.coverage_available = self._check_coverage_availability()
    
    def _check_coverage_availability(self):
        """Check if coverage.py is available."""
        try:
            import coverage
            return True
        except ImportError:
            return False
    
    def run_with_coverage(self, test_modules=None):
        """Run tests with coverage reporting."""
        if not self.coverage_available:
            print("Coverage.py not available. Install with: pip install coverage")
            return None
        
        import coverage
        
        # Start coverage
        cov = coverage.Coverage()
        cov.start()
        
        try:
            # Run tests
            if test_modules:
                for module in test_modules:
                    call_command('test', module, verbosity=1)
            else:
                call_command('test', verbosity=1)
        finally:
            # Stop coverage
            cov.stop()
            cov.save()
        
        # Generate reports
        self._generate_coverage_reports(cov)
        
        return cov
    
    def _generate_coverage_reports(self, cov):
        """Generate coverage reports in multiple formats."""
        print("\nGenerating coverage reports...")
        
        # Console report
        print("\nCoverage Summary:")
        cov.report()
        
        # HTML report
        try:
            cov.html_report(directory='htmlcov')
            print("HTML coverage report generated in 'htmlcov' directory")
        except Exception as e:
            print(f"Could not generate HTML report: {e}")
        
        # XML report (for CI/CD)
        try:
            cov.xml_report(outfile='coverage.xml')
            print("XML coverage report generated: coverage.xml")
        except Exception as e:
            print(f"Could not generate XML report: {e}")


class PerformanceProfiler:
    """Profiles test performance and identifies bottlenecks."""
    
    def __init__(self):
        self.query_counts = {}
        self.execution_times = {}
    
    def profile_test_method(self, test_method):
        """Profile a specific test method."""
        # Reset query count
        connection.queries_log.clear()
        
        start_time = time.time()
        
        try:
            result = test_method()
            status = 'passed'
            error = None
        except Exception as e:
            result = None
            status = 'failed'
            error = str(e)
        
        end_time = time.time()
        execution_time = end_time - start_time
        query_count = len(connection.queries)
        
        profile_data = {
            'execution_time': execution_time,
            'query_count': query_count,
            'status': status,
            'error': error,
            'queries': connection.queries.copy() if query_count > 0 else []
        }
        
        return profile_data
    
    def generate_performance_report(self, profile_data):
        """Generate performance analysis report."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'performance_analysis': profile_data,
            'recommendations': self._generate_recommendations(profile_data)
        }
        
        # Save report
        report_file = f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Performance report saved to: {report_file}")
        
        return report
    
    def _generate_recommendations(self, profile_data):
        """Generate performance optimization recommendations."""
        recommendations = []
        
        for test_name, data in profile_data.items():
            if data['execution_time'] > 5.0:
                recommendations.append(f"{test_name}: Slow execution time ({data['execution_time']:.2f}s)")
            
            if data['query_count'] > 10:
                recommendations.append(f"{test_name}: High query count ({data['query_count']} queries)")
        
        return recommendations


# Utility functions for running specific test scenarios
def run_smoke_tests():
    """Run basic smoke tests to verify system functionality."""
    smoke_tests = [
        'accounts.tests.UserModelTest.test_create_user',
        'accounts.tests.BankAccountModelTest.test_create_bank_account',
        'transactions.tests.TransactionModelTest.test_create_deposit_transaction',
        'admin_panel.tests.AdminDashboardViewTests.test_admin_dashboard_requires_login'
    ]
    
    print("Running smoke tests...")
    manager = TestSuiteManager()
    
    for test in smoke_tests:
        try:
            call_command('test', test, verbosity=1)
            print(f"✓ {test}")
        except Exception as e:
            print(f"✗ {test}: {e}")
            return False
    
    print("All smoke tests passed!")
    return True


def run_regression_tests():
    """Run regression tests to ensure no functionality is broken."""
    print("Running regression test suite...")
    
    manager = TestSuiteManager()
    results = manager.run_all_tests()
    
    # Check for any failures
    total_failed = 0
    for category_data in results.values():
        for module_result in category_data['results'].values():
            if module_result['status'] == 'failed':
                total_failed += 1
    
    if total_failed == 0:
        print("✓ All regression tests passed!")
        return True
    else:
        print(f"✗ {total_failed} test modules failed regression testing")
        return False


def run_performance_benchmark():
    """Run performance benchmark tests."""
    print("Running performance benchmarks...")
    
    manager = TestSuiteManager()
    profiler = PerformanceProfiler()
    
    # Run performance tests with profiling
    performance_results = manager.run_category('performance')
    
    # Generate performance report
    profiler.generate_performance_report(performance_results)
    
    return performance_results


def run_security_audit():
    """Run security audit tests."""
    print("Running security audit...")
    
    manager = TestSuiteManager()
    security_results = manager.run_category('security')
    
    # Check for security test failures
    failed_security_tests = []
    for module, result in security_results.items():
        if result['status'] == 'failed':
            failed_security_tests.append(module)
    
    if failed_security_tests:
        print(f"⚠️  Security issues detected in: {', '.join(failed_security_tests)}")
        return False
    else:
        print("✓ Security audit passed!")
        return True


if __name__ == '__main__':
    """Command-line interface for test runner."""
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == 'smoke':
            run_smoke_tests()
        elif command == 'regression':
            run_regression_tests()
        elif command == 'performance':
            run_performance_benchmark()
        elif command == 'security':
            run_security_audit()
        elif command == 'all':
            manager = TestSuiteManager()
            manager.run_all_tests()
        elif command == 'coverage':
            reporter = CoverageReporter()
            reporter.run_with_coverage()
        else:
            print(f"Unknown command: {command}")
            print("Available commands: smoke, regression, performance, security, all, coverage")
    else:
        print("Banking Platform Test Runner")
        print("Usage: python test_runner.py <command>")
        print("Commands:")
        print("  smoke      - Run basic smoke tests")
        print("  regression - Run full regression test suite")
        print("  performance- Run performance benchmarks")
        print("  security   - Run security audit")
        print("  all        - Run all test categories")
        print("  coverage   - Run tests with coverage reporting")