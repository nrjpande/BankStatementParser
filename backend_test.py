#!/usr/bin/env python3

import requests
import sys
import json
import os
from datetime import datetime
from typing import Dict, Any

class Bank2TallyAPITester:
    def __init__(self, base_url="https://f7af87bc-7a46-4ab8-823d-b7157ecf0a8b.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.user_data = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
        # Test data
        self.test_email = "test@bank2tally.com"
        self.test_password = "test123456"
        self.test_name = "Test User"
        self.statement_id = None
        self.transaction_id = None
        self.rule_id = None

    def log_test(self, name: str, success: bool, response_data: Any = None, error: str = None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
        
        result = {
            "test_name": name,
            "success": success,
            "timestamp": datetime.now().isoformat(),
        }
        if error:
            result["error"] = error
        if response_data:
            result["response_sample"] = str(response_data)[:200] + "..." if len(str(response_data)) > 200 else str(response_data)
        
        self.test_results.append(result)
        
        status = "✅" if success else "❌"
        print(f"{status} {name}")
        if error:
            print(f"   Error: {error}")

    def run_test(self, name: str, method: str, endpoint: str, expected_status: int = 200, data: Dict = None, files: Dict = None, headers: Dict = None) -> tuple:
        """Run a single API test"""
        url = f"{self.base_url}{endpoint}"
        
        # Default headers
        default_headers = {'Content-Type': 'application/json'}
        if self.token:
            default_headers['Authorization'] = f'Bearer {self.token}'
        
        # Merge with custom headers
        if headers:
            default_headers.update(headers)
        
        # Remove Content-Type for file uploads
        if files:
            default_headers.pop('Content-Type', None)

        try:
            if method == 'GET':
                response = requests.get(url, headers=default_headers)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files, headers=default_headers)
                else:
                    response = requests.post(url, json=data, headers=default_headers)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=default_headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=default_headers)
            else:
                self.log_test(name, False, error=f"Unsupported method: {method}")
                return False, {}

            success = response.status_code == expected_status
            response_data = {}
            
            try:
                if response.content:
                    response_data = response.json()
            except:
                response_data = {"raw_content": response.text[:200]}

            if success:
                self.log_test(name, True, response_data)
            else:
                error_msg = f"Expected {expected_status}, got {response.status_code}"
                if response_data:
                    error_msg += f" - {response_data.get('detail', response_data)}"
                self.log_test(name, False, response_data, error_msg)

            return success, response_data

        except Exception as e:
            self.log_test(name, False, error=str(e))
            return False, {}

    def test_health_check(self):
        """Test health endpoint"""
        return self.run_test("Health Check", "GET", "/api/health")

    def test_register(self):
        """Test user registration"""
        success, response = self.run_test(
            "Register User",
            "POST",
            "/api/auth/register",
            data={
                "email": self.test_email,
                "password": self.test_password,
                "name": self.test_name
            }
        )
        
        if success and 'token' in response:
            self.token = response['token']
            self.user_data = response.get('user', {})
            
        return success, response

    def test_login(self):
        """Test user login"""
        success, response = self.run_test(
            "Login User",
            "POST",
            "/api/auth/login",
            data={
                "email": self.test_email,
                "password": self.test_password
            }
        )
        
        if success and 'token' in response:
            self.token = response['token']
            self.user_data = response.get('user', {})
            
        return success, response

    def test_get_current_user(self):
        """Test getting current user info"""
        return self.run_test("Get Current User", "GET", "/api/auth/me")

    def test_upload_statement(self):
        """Test uploading bank statement"""
        file_path = "/app/test_hdfc_statement.xlsx"
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': ('test_hdfc_statement.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
                success, response = self.run_test(
                    "Upload Statement",
                    "POST",
                    "/api/upload",
                    files=files
                )
                
                if success and 'statement' in response:
                    self.statement_id = response['statement']['statement_id']
                    if response.get('transactions') and len(response['transactions']) > 0:
                        self.transaction_id = response['transactions'][0]['transaction_id']
                
                return success, response
                
        except Exception as e:
            self.log_test("Upload Statement", False, error=f"File error: {str(e)}")
            return False, {}

    def test_list_statements(self):
        """Test listing statements"""
        return self.run_test("List Statements", "GET", "/api/statements")

    def test_get_transactions(self):
        """Test getting transactions for a statement"""
        if not self.statement_id:
            self.log_test("Get Transactions", False, error="No statement ID available")
            return False, {}
            
        return self.run_test("Get Transactions", "GET", f"/api/transactions/{self.statement_id}")

    def test_update_transaction(self):
        """Test updating a transaction's ledger"""
        if not self.transaction_id:
            self.log_test("Update Transaction", False, error="No transaction ID available")
            return False, {}
            
        return self.run_test(
            "Update Transaction",
            "PUT",
            f"/api/transactions/{self.transaction_id}",
            data={
                "ledger": "Bank Charges",
                "voucher_type": "Payment"
            }
        )

    def test_bulk_update_transactions(self):
        """Test bulk updating transactions"""
        if not self.transaction_id:
            self.log_test("Bulk Update Transactions", False, error="No transaction ID available")
            return False, {}
            
        return self.run_test(
            "Bulk Update Transactions",
            "PUT",
            "/api/transactions/bulk/update",
            data={
                "transaction_ids": [self.transaction_id],
                "ledger": "Office Supplies",
                "voucher_type": "Payment"
            }
        )

    def test_create_mapping_rule(self):
        """Test creating a mapping rule"""
        success, response = self.run_test(
            "Create Mapping Rule",
            "POST",
            "/api/mapping-rules",
            data={
                "keyword": "testmerchant",
                "ledger": "Meals & Entertainment"
            }
        )
        
        if success and 'rule_id' in response:
            self.rule_id = response['rule_id']
            
        return success, response

    def test_list_mapping_rules(self):
        """Test listing mapping rules"""
        return self.run_test("List Mapping Rules", "GET", "/api/mapping-rules")

    def test_apply_rules(self):
        """Test applying rules to a statement"""
        if not self.statement_id:
            self.log_test("Apply Rules", False, error="No statement ID available")
            return False, {}
            
        return self.run_test("Apply Rules", "POST", f"/api/apply-rules/{self.statement_id}")

    def test_export_tally(self):
        """Test exporting Tally XML"""
        if not self.statement_id:
            self.log_test("Export Tally XML", False, error="No statement ID available")
            return False, {}
            
        # For XML export, we expect different content type
        url = f"{self.base_url}/api/export/tally/{self.statement_id}"
        headers = {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}
        
        try:
            response = requests.post(url, 
                json={
                    "company_name": "Test Company",
                    "bank_ledger": "Test Bank Account"
                }, 
                headers=headers
            )
            
            success = response.status_code == 200
            if success:
                # Check if it's XML content
                is_xml = response.headers.get('content-type', '').startswith('application/xml')
                self.log_test("Export Tally XML", success, f"XML content: {is_xml}, Length: {len(response.content)}")
            else:
                error_msg = f"Expected 200, got {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg += f" - {error_data.get('detail', error_data)}"
                except:
                    error_msg += f" - {response.text[:100]}"
                self.log_test("Export Tally XML", False, error=error_msg)
            
            return success, {"content_length": len(response.content), "content_type": response.headers.get('content-type')}
            
        except Exception as e:
            self.log_test("Export Tally XML", False, error=str(e))
            return False, {}

    def test_dashboard_stats(self):
        """Test getting dashboard statistics"""
        return self.run_test("Dashboard Stats", "GET", "/api/dashboard/stats")

    def test_get_ledgers(self):
        """Test getting ledger list"""
        return self.run_test("Get Ledgers", "GET", "/api/ledgers")

    def test_delete_mapping_rule(self):
        """Test deleting a mapping rule"""
        if not self.rule_id:
            self.log_test("Delete Mapping Rule", False, error="No rule ID available")
            return False, {}
            
        return self.run_test("Delete Mapping Rule", "DELETE", f"/api/mapping-rules/{self.rule_id}")

    def test_delete_statement(self):
        """Test deleting a statement"""
        if not self.statement_id:
            self.log_test("Delete Statement", False, error="No statement ID available")
            return False, {}
            
        return self.run_test("Delete Statement", "DELETE", f"/api/statements/{self.statement_id}")

    def run_all_tests(self):
        """Run comprehensive test suite"""
        print(f"🚀 Starting Bank2Tally API Tests")
        print(f"📍 Base URL: {self.base_url}")
        print("=" * 50)

        # Health check
        self.test_health_check()

        # Authentication flow
        register_success, _ = self.test_register()
        if not register_success:
            # Try login if register fails (user might already exist)
            login_success, _ = self.test_login()
            if not login_success:
                print("❌ Authentication failed. Cannot continue with other tests.")
                return self.get_summary()

        self.test_get_current_user()

        # File upload and processing
        self.test_upload_statement()
        self.test_list_statements()
        
        # Transaction management
        self.test_get_transactions()
        self.test_update_transaction()
        self.test_bulk_update_transactions()

        # Mapping rules
        self.test_create_mapping_rule()
        self.test_list_mapping_rules()
        self.test_apply_rules()

        # Export functionality
        self.test_export_tally()

        # Dashboard and utilities
        self.test_dashboard_stats()
        self.test_get_ledgers()

        # Cleanup
        self.test_delete_mapping_rule()
        self.test_delete_statement()

        return self.get_summary()

    def get_summary(self):
        """Get test summary"""
        success_rate = (self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0
        
        summary = {
            "total_tests": self.tests_run,
            "passed_tests": self.tests_passed,
            "failed_tests": self.tests_run - self.tests_passed,
            "success_rate": round(success_rate, 1),
            "test_results": self.test_results
        }
        
        print("\n" + "=" * 50)
        print(f"📊 Test Summary:")
        print(f"   Total Tests: {self.tests_run}")
        print(f"   Passed: {self.tests_passed}")
        print(f"   Failed: {self.tests_run - self.tests_passed}")
        print(f"   Success Rate: {success_rate:.1f}%")
        
        if self.tests_run - self.tests_passed > 0:
            print(f"\n❌ Failed Tests:")
            for result in self.test_results:
                if not result['success']:
                    print(f"   - {result['test_name']}: {result.get('error', 'Unknown error')}")
        
        return summary

def main():
    tester = Bank2TallyAPITester()
    summary = tester.run_all_tests()
    
    # Exit with appropriate code
    if summary['failed_tests'] > 0:
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())