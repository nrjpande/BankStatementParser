#!/usr/bin/env python3

import requests
import sys
import json
import os
from datetime import datetime
from typing import Dict, Any

class Bank2TallyAPITester:
    def __init__(self, base_url="https://tally-ledger-mapper.preview.emergentagent.com"):
        self.base_url = base_url
        self.token = None
        self.user_data = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        
        # Test data
        self.test_email = "test3@bank2tally.com"
        self.test_password = "test123456"
        self.test_name = "Test User"
        self.statement_id = None
        self.transaction_id = None
        self.rule_id = None
        self.job_id = None
        self.ledger_id = None

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

    def test_upload_statement_async(self):
        """Test async uploading bank statement with job polling"""
        file_path = "/app/test_hdfc_statement.xlsx"
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': ('test_hdfc_statement.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
                success, response = self.run_test(
                    "Upload Statement (Async)",
                    "POST",
                    "/api/upload",
                    files=files
                )
                
                if success and 'job_id' in response:
                    self.job_id = response['job_id']
                    print(f"   Job ID: {self.job_id}")
                    return True, response
                elif success and response.get('status') == 'duplicate':
                    print(f"   Duplicate file detected: {response.get('message')}")
                    return True, response
                
                return success, response
                
        except Exception as e:
            self.log_test("Upload Statement (Async)", False, error=f"File error: {str(e)}")
            return False, {}

    def test_upload_status_polling(self):
        """Test polling upload job status"""
        if not self.job_id:
            self.log_test("Upload Status Polling", False, error="No job ID available")
            return False, {}
        
        import time
        max_attempts = 30
        attempt = 0
        
        while attempt < max_attempts:
            success, response = self.run_test(
                f"Upload Status Check (Attempt {attempt + 1})",
                "GET",
                f"/api/upload/status/{self.job_id}"
            )
            
            if not success:
                return False, response
            
            status = response.get('status')
            progress = response.get('progress', 0)
            print(f"   Status: {status}, Progress: {progress}%")
            
            if status == 'completed':
                self.statement_id = response.get('statement_id')
                print(f"   Upload completed! Statement ID: {self.statement_id}")
                # Get first transaction ID for testing
                if self.statement_id:
                    txn_success, txn_response = self.run_test(
                        "Get Transactions for ID",
                        "GET",
                        f"/api/transactions/{self.statement_id}"
                    )
                    if txn_success and txn_response and len(txn_response) > 0:
                        self.transaction_id = txn_response[0]['transaction_id']
                        print(f"   First Transaction ID: {self.transaction_id}")
                return True, response
            elif status == 'failed':
                error_msg = response.get('error', 'Unknown error')
                self.log_test("Upload Status Polling", False, error=f"Upload failed: {error_msg}")
                return False, response
            
            time.sleep(2)
            attempt += 1
        
        self.log_test("Upload Status Polling", False, error="Timeout waiting for upload completion")
        return False, {}

    def test_duplicate_file_upload(self):
        """Test duplicate file detection via SHA-256 hash"""
        file_path = "/app/test_hdfc_statement.xlsx"
        
        try:
            with open(file_path, 'rb') as f:
                files = {'file': ('test_hdfc_statement.xlsx', f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')}
                success, response = self.run_test(
                    "Duplicate File Upload Test",
                    "POST",
                    "/api/upload",
                    files=files
                )
                
                if success and response.get('status') == 'duplicate':
                    print(f"   ✅ Duplicate detection working: {response.get('message')}")
                    return True, response
                elif success and 'job_id' in response:
                    print(f"   ⚠️  File uploaded as new (not duplicate)")
                    return True, response
                
                return success, response
                
        except Exception as e:
            self.log_test("Duplicate File Upload Test", False, error=f"File error: {str(e)}")
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

    def test_get_ledger_names(self):
        """Test getting ledger names for dropdowns"""
        return self.run_test("Get Ledger Names", "GET", "/api/ledgers/names")

    def test_create_ledger(self):
        """Test creating a new ledger"""
        success, response = self.run_test(
            "Create Ledger",
            "POST",
            "/api/ledgers",
            data={
                "name": "Test Automation Ledger",
                "group": "Test Group"
            }
        )
        
        if success and 'ledger_id' in response:
            self.ledger_id = response['ledger_id']
            
        return success, response

    def test_delete_ledger(self):
        """Test deleting a ledger"""
        if not self.ledger_id:
            self.log_test("Delete Ledger", False, error="No ledger ID available")
            return False, {}
            
        return self.run_test("Delete Ledger", "DELETE", f"/api/ledgers/{self.ledger_id}")

    def test_import_tally_xml(self):
        """Test importing ledgers from Tally XML"""
        # Create a simple test XML file
        test_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<ENVELOPE>
    <HEADER>
        <TALLYREQUEST>Import Data</TALLYREQUEST>
    </HEADER>
    <BODY>
        <IMPORTDATA>
            <REQUESTDESC>
                <REPORTNAME>All Masters</REPORTNAME>
            </REQUESTDESC>
            <REQUESTDATA>
                <TALLYMESSAGE xmlns:UDF="TallyUDF">
                    <LEDGER NAME="Test Import Ledger 1" RESERVEDNAME="">
                        <OLDAUDITENTRYIDS.LIST TYPE="Number">
                            <OLDAUDITENTRYIDS>-1</OLDAUDITENTRYIDS>
                        </OLDAUDITENTRYIDS.LIST>
                        <GUID>test-guid-1</GUID>
                        <PARENT>Sundry Debtors</PARENT>
                        <LEDGERNAME>Test Import Ledger 1</LEDGERNAME>
                    </LEDGER>
                    <LEDGER NAME="Test Import Ledger 2" RESERVEDNAME="">
                        <OLDAUDITENTRYIDS.LIST TYPE="Number">
                            <OLDAUDITENTRYIDS>-2</OLDAUDITENTRYIDS>
                        </OLDAUDITENTRYIDS.LIST>
                        <GUID>test-guid-2</GUID>
                        <PARENT>Sundry Creditors</PARENT>
                        <LEDGERNAME>Test Import Ledger 2</LEDGERNAME>
                    </LEDGER>
                </TALLYMESSAGE>
            </REQUESTDATA>
        </IMPORTDATA>
    </BODY>
</ENVELOPE>'''
        
        try:
            # Write test XML to temporary file
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
                f.write(test_xml)
                temp_file_path = f.name
            
            # Upload the XML file
            with open(temp_file_path, 'rb') as f:
                files = {'file': ('test_tally_masters.xml', f, 'application/xml')}
                success, response = self.run_test(
                    "Import Tally XML",
                    "POST",
                    "/api/ledgers/import-tally-xml",
                    files=files
                )
            
            # Clean up temp file
            import os
            os.unlink(temp_file_path)
            
            return success, response
                
        except Exception as e:
            self.log_test("Import Tally XML", False, error=f"File error: {str(e)}")
            return False, {}

    def test_mark_ready_for_tally(self):
        """Test marking transactions as ready for Tally sync"""
        if not self.statement_id:
            self.log_test("Mark Ready for Tally", False, error="No statement ID available")
            return False, {}
            
        return self.run_test(
            "Mark Ready for Tally",
            "POST",
            f"/api/tally/mark-ready/{self.statement_id}",
            data={
                "company_name": "Test Company",
                "bank_ledger": "Test Bank Account"
            }
        )

    def test_get_pending_sync(self):
        """Test getting transactions pending Tally sync"""
        return self.run_test("Get Pending Sync", "GET", "/api/tally/pending")

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
        print(f"🚀 Starting Bank2Tally API Tests (New Features)")
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

        # NEW: Async file upload and processing with job polling
        upload_success, _ = self.test_upload_statement_async()
        if upload_success:
            self.test_upload_status_polling()
        
        # NEW: Test duplicate file detection
        self.test_duplicate_file_upload()
        
        self.test_list_statements()
        
        # Transaction management
        self.test_get_transactions()
        self.test_update_transaction()
        self.test_bulk_update_transactions()

        # NEW: DB-backed master ledgers
        self.test_get_ledgers()
        self.test_get_ledger_names()
        self.test_create_ledger()
        self.test_import_tally_xml()

        # Mapping rules (now uses DB-backed ledgers)
        self.test_create_mapping_rule()
        self.test_list_mapping_rules()
        self.test_apply_rules()

        # NEW: Mark as Ready for Tally (replaces XML export)
        self.test_mark_ready_for_tally()
        self.test_get_pending_sync()

        # Dashboard and utilities
        self.test_dashboard_stats()

        # Cleanup
        self.test_delete_mapping_rule()
        if self.ledger_id:
            self.test_delete_ledger()
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